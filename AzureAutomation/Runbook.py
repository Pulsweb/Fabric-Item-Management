#!/usr/bin/env python3
"""
Azure Automation Runbook (Python 3.10)
Goal: Create a Fabric Data Agent inside a Fabric workspace.

Prerequisites:
  1. System-assigned Managed Identity enabled on the Automation Account.
  2. The Managed Identity must have the "Contributor" (or "Member") role on the target Fabric workspace.
  3. In the Fabric Admin Portal: enable "Service principals can use Fabric APIs" (tenant settings).

Runbook Parameters:
  --workspace_name      : Name of the Fabric workspace (created if it does not exist)
  --agent_name          : Name of the Data Agent to create
  --agent_description   : (Optional) Description of the Data Agent
  --capacity_name       : (Optional) Name of the Fabric capacity to assign the workspace to
  --admin_user_object_id: (Optional) Entra Object ID (or UPN) of the user to promote as Admin
"""

import sys
import os
import json
import base64
import time
import urllib.request
import urllib.error
import urllib.parse
import automationassets

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_fabric_token() -> str:
    """Acquire a Fabric access token via the Managed Identity."""
    endpoint = os.getenv("IDENTITY_ENDPOINT")
    header   = os.getenv("IDENTITY_HEADER")

    if not endpoint or not header:
        raise EnvironmentError(
            "IDENTITY_ENDPOINT / IDENTITY_HEADER environment variables not found. "
            "Ensure the Managed Identity is enabled on the Automation Account."
        )

    url = f"{endpoint}?resource=https://api.fabric.microsoft.com&api-version=2019-08-01"
    req = urllib.request.Request(
        url,
        headers={"X-IDENTITY-HEADER": header, "Metadata": "True"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())["access_token"]


def get_graph_token() -> str:
    """Acquire a Microsoft Graph access token via the Managed Identity."""
    endpoint = os.getenv("IDENTITY_ENDPOINT")
    header   = os.getenv("IDENTITY_HEADER")

    if not endpoint or not header:
        raise EnvironmentError(
            "IDENTITY_ENDPOINT / IDENTITY_HEADER environment variables not found. "
            "Ensure the Managed Identity is enabled on the Automation Account."
        )

    url = f"{endpoint}?resource=https://graph.microsoft.com&api-version=2019-08-01"
    req = urllib.request.Request(
        url,
        headers={"X-IDENTITY-HEADER": header, "Metadata": "True"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())["access_token"]


def resolve_user_object_id(upn_or_id: str) -> str:
    """If upn_or_id is a UPN (email), resolve the Entra Object ID via Microsoft Graph."""
    import re
    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', upn_or_id, re.IGNORECASE):
        return upn_or_id  # already a GUID

    graph_token = get_graph_token()
    encoded_upn = urllib.parse.quote(upn_or_id)
    url = f"https://graph.microsoft.com/v1.0/users/{encoded_upn}?$select=id"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {graph_token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            object_id = result["id"]
            print(f"  [INFO] UPN '{upn_or_id}' resolved to Object ID: {object_id}")
            return object_id
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode()
        raise RuntimeError(
            f"Unable to resolve UPN '{upn_or_id}' via Microsoft Graph.\n"
            f"HTTP {exc.code}: {error_body}\n"
            f"Tip: verify that the Managed Identity has the 'User.Read.All' role on Microsoft Graph."
        )


def get_object_id_from_token(token: str) -> str:
    """Extract the Managed Identity's Object ID (oid claim) from the JWT token."""
    payload_b64 = token.split(".")[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    payload = json.loads(base64.b64decode(payload_b64).decode())
    return payload["oid"]


def poll_operation(operation_url: str, token: str, max_wait: int = 120) -> dict:
    """Poll a Fabric async operation until completion or timeout (max_wait seconds)."""
    headers = {"Authorization": f"Bearer {token}"}
    elapsed = 0
    retry_after = 5

    while elapsed < max_wait:
        time.sleep(retry_after)
        elapsed += retry_after

        req = urllib.request.Request(operation_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            status = data.get("status", "").lower()

            print(f"  [poll {elapsed}s] status: {status}")

            if status == "succeeded":
                return data
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"Async operation failed: {json.dumps(data, indent=2)}")

            retry_after = int(resp.getheader("Retry-After", 5))

    raise TimeoutError(f"Timeout ({max_wait}s) waiting for Data Agent creation to complete.")


def find_capacity_by_name(capacity_name: str, token: str):
    """Search for a capacity by display name (GET /capacities, paginated). Returns the ID or None."""
    url = "https://api.fabric.microsoft.com/v1/capacities"
    headers = {"Authorization": f"Bearer {token}"}
    found_names = []

    while url:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode()
            raise RuntimeError(
                f"Failed to list capacities.\n"
                f"HTTP {exc.code}: {error_body}"
            )

        for cap in data.get("value", []):
            name = cap.get("displayName", "")
            found_names.append(name)
            if name.lower() == capacity_name.lower():
                return cap["id"]

        url = data.get("continuationUri")

    if found_names:
        print(f"  [DEBUG] Accessible capacities: {found_names}")
    else:
        print(f"  [DEBUG] No capacities returned — the Managed Identity may not be Admin/Contributor on any capacity.")

    return None


def create_fabric_workspace(workspace_name: str, token: str, capacity_id: str = None) -> str:
    """Create a Fabric workspace and return its ID (POST /workspaces)."""
    url = "https://api.fabric.microsoft.com/v1/workspaces"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"displayName": workspace_name}
    if capacity_id:
        payload["capacityId"] = capacity_id
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            print(f"  [SUCCESS] Workspace '{result.get('displayName')}' created: {result.get('id')}")
            return result["id"]
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode()
        if exc.code == 409:
            error_json = json.loads(error_body)
            if error_json.get("errorCode") == "WorkspaceNameAlreadyExists":
                raise RuntimeError(
                    f"Workspace '{workspace_name}' already exists but the Managed Identity "
                    f"is not a member and cannot detect it.\n"
                    f"Solution: add the Managed Identity (Object ID visible in the runbook output) "
                    f"as a member of workspace '{workspace_name}' in Fabric, then re-run."
                )
        raise RuntimeError(
            f"Failed to create workspace.\n"
            f"HTTP {exc.code}: {error_body}"
        )


def find_workspace_by_name(workspace_name: str, token: str):
    """Search for a workspace by display name (GET /workspaces, paginated). Returns the ID or None."""
    url = "https://api.fabric.microsoft.com/v1/workspaces"
    headers = {"Authorization": f"Bearer {token}"}

    while url:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode()
            raise RuntimeError(
                f"Failed to list workspaces.\n"
                f"HTTP {exc.code}: {error_body}"
            )

        for ws in data.get("value", []):
            if ws.get("displayName", "").lower() == workspace_name.lower():
                return ws["id"]

        url = data.get("continuationUri")  # None on the last page

    return None


def assign_workspace_role(
    workspace_id: str,
    principal_id: str,
    principal_type: str,
    role: str,
    token: str,
) -> None:
    """Assign a role to a principal on a Fabric workspace (POST /roleAssignments)."""
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/roleAssignments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "principal": {"id": principal_id, "type": principal_type},
        "role": role,
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"  [SUCCESS] Role '{role}' assigned to principal {principal_id} ({principal_type}).")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode()
        if exc.code == 409:
            error_json = json.loads(error_body)
            if error_json.get("errorCode") == "PrincipalAlreadyHasWorkspaceRolePermissions":
                print(f"  [INFO] Principal {principal_id} already has a role on this workspace — no action needed.")
                return
        raise RuntimeError(
            f"Failed to assign role '{role}' to principal {principal_id}.\n"
            f"HTTP {exc.code}: {error_body}"
        )


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def create_fabric_data_agent(
    workspace_id: str,
    agent_name: str,
    agent_description: str = "",
    token: str = None,
) -> dict:
    """Create a Data Agent item in the specified Fabric workspace (POST /dataAgents)."""

    if token is None:
        print(f"Acquiring Fabric token via Managed Identity...")
        token = get_fabric_token()

    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/dataAgents"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "displayName": agent_name,
        "description": agent_description,
    }

    print(f"Sending creation request to: {url}")
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status_code = resp.status
            response_body = resp.read().decode()
            location = resp.getheader("Location") or resp.getheader("location")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode()
        raise RuntimeError(
            f"Failed to create Data Agent.\n"
            f"HTTP {exc.code}: {error_body}"
        )

    # Synchronous success
    if status_code in (200, 201):
        result = json.loads(response_body)
        print(f"\n[SUCCESS] Data Agent created:")
        print(f"  Name        : {result.get('displayName')}")
        print(f"  ID          : {result.get('id')}")
        print(f"  Workspace   : {result.get('workspaceId')}")
        print(f"  Type        : {result.get('type')}")
        return result

    # Asynchronous operation (202 Accepted)
    if status_code == 202:
        print(f"[INFO] Async creation in progress. Polling: {location}")
        result = poll_operation(location, token)
        print(f"\n[SUCCESS] Data Agent created (async):")
        print(json.dumps(result, indent=2))
        return result

    raise RuntimeError(
        f"Failed to create Data Agent.\n"
        f"HTTP {status_code}: {response_body}"
    )


# ---------------------------------------------------------------------------
# Entry point — parameters are passed via Runbook arguments (webhook or direct)
# ---------------------------------------------------------------------------

def _extract_request_body(raw: str) -> dict:
    """
    Azure Automation (Python) passes the entire webhook payload as a raw string
    in sys.argv[1:], space-split.  The format is:
      {WebhookName:...,RequestBody:{<valid JSON>},RequestHeader:{...}}
    This function locates RequestBody:{ and extracts the balanced JSON object.
    """
    marker = "RequestBody:"
    idx = raw.find(marker)
    if idx == -1:
        return {}
    start = raw.index("{", idx + len(marker))
    depth = 0
    in_string = False
    escape = False
    for i, c in enumerate(raw[start:], start):
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    json_str = raw[start : i + 1]
                    # Azure Automation passes newlines as literal \r\n escape sequences
                    # (backslash + letter), not real CR/LF — decode them before parsing.
                    json_str = json_str.replace('\\r\\n', '\r\n').replace('\\r', '\r').replace('\\n', '\n')
                    return json.loads(json_str)
    return {}


def main():
    # Azure Automation passes the webhook payload as a raw string split by spaces
    # across sys.argv[1:] — NOT as --key value pairs.  Re-join and parse.
    raw_argv = " ".join(sys.argv[1:])

    # --- Parse the webhook payload sent by the Static Web App (HTTP POST body) ---
    workspace_name       = ""
    agent_name           = ""
    agent_description    = ""
    capacity_name        = ""
    admin_user_object_id = ""

    if "RequestBody:" in raw_argv:
        try:
            request_body         = _extract_request_body(raw_argv)
            workspace_name       = request_body.get("workspace_name", "")
            agent_name           = request_body.get("agent_name", "")
            agent_description    = request_body.get("agent_description", "")
            capacity_name        = request_body.get("capacity_name", "")
            admin_user_object_id = request_body.get("admin_user_object_id", "")
            print("[INFO] Parameters read from webhook payload.")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            print(f"[WARN] Unable to parse RequestBody from webhook data: {exc}")

    # --- Fallback: Automation Account Variables (for direct / scheduled runs) ---
    def _get_var(name: str, current_value: str) -> str:
        if current_value:
            return current_value
        try:
            return automationassets.get_automation_variable(name) or ""
        except Exception:
            return ""

    workspace_name       = _get_var("workspace_name",       workspace_name)
    agent_name           = _get_var("agent_name",           agent_name)
    agent_description    = _get_var("agent_description",    agent_description)
    capacity_name        = _get_var("capacity_name",        capacity_name)
    admin_user_object_id = _get_var("admin_user_object_id", admin_user_object_id)

    if not workspace_name:
        print("[ERROR] 'workspace_name' is required.")
        sys.exit(1)

    if not agent_name:
        print("[ERROR] 'agent_name' is required.")
        sys.exit(1)

    print("=" * 60)
    print("Creating a Fabric Data Agent via Azure Automation")
    print(f"  Workspace      : {workspace_name}")
    print(f"  Agent Name     : {agent_name}")
    print("=" * 60)

    try:
        print("Acquiring Fabric token via Managed Identity...")
        token = get_fabric_token()

        print(f"\nLooking up workspace '{workspace_name}'...")
        workspace_id = find_workspace_by_name(workspace_name, token)

        if workspace_id:
            print(f"  [FOUND] Existing workspace: {workspace_id}")
        else:
            capacity_id = None
            if capacity_name:
                print(f"\nLooking up capacity '{capacity_name}'...")
                capacity_id = find_capacity_by_name(capacity_name, token)
                if capacity_id:
                    print(f"  [FOUND] Capacity: {capacity_id}")
                else:
                    raise RuntimeError(f"Capacity '{capacity_name}' not found.")

            print(f"  [NOT FOUND] Creating workspace '{workspace_name}'...")
            workspace_id = create_fabric_workspace(workspace_name, token, capacity_id)

            mi_object_id = get_object_id_from_token(token)
            print(f"\nAssigning Admin role to Managed Identity ({mi_object_id})...")
            assign_workspace_role(workspace_id, mi_object_id, "ServicePrincipal", "Admin", token)

            if admin_user_object_id:
                print(f"Assigning Admin role to user ({admin_user_object_id})...")
                resolved_id = resolve_user_object_id(admin_user_object_id)
                assign_workspace_role(workspace_id, resolved_id, "User", "Admin", token)

        create_fabric_data_agent(workspace_id, agent_name, agent_description, token)
    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()