# Extending the Solution

[← Back to README](../README.md)

---

## Add New Fabric Item Types

The solution is designed around a single item type (Data Agent) to keep it simple and focused. Adding support for a new item type (Lakehouse, Warehouse, Notebook, etc.) follows the same pattern:

1. **Add a new wizard flow** in `AzureWebApp/index.html` — duplicate the existing Data Agent wizard cards and update the item type label.
2. **Add the item-type field** to the JSON payload in `AzureWebApp/app.js`.
3. **Add a new creation function** in `AzureAutomation/Runbook.py`:

   ```python
   def create_fabric_lakehouse(workspace_id: str, name: str, token: str) -> dict:
       url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
       # ... same pattern as create_fabric_data_agent()
   ```

4. Route to the correct function in `main()` based on the `item_type` field in the webhook payload.

---

## Enforce Naming Conventions

Add regex validation in the wizard (`validateStep()` in `app.js`) before the payload is sent:

```javascript
const namingPattern = /^[A-Z][a-zA-Z0-9_-]{2,49}$/;
if (!namingPattern.test(workspaceName)) {
    showError("Workspace name must start with a capital letter and be 3–50 characters.");
    return false;
}
```

This catches naming violations client-side before the Runbook ever runs.

---

## Add Audit Logging

Write the runbook output to Azure Storage or Log Analytics for traceability and chargeback reporting:

```python
import urllib.request, json

def log_to_storage(event: dict, connection_string: str):
    # Write a JSON event to an Azure Storage Table or Blob
    ...
```

Or use Azure Monitor custom logs via the Data Collection API.

---

## Add the Approval Workflow

See [Approval Workflow](approval-workflow.md) for a full guide on inserting a human-in-the-loop gate between the SWA and the webhook.

---

## Entra Group Support

Instead of assigning individual users, accept an Entra Group Object ID and assign workspace roles to the group:

```python
assign_workspace_role(workspace_id, group_object_id, "Group", "Member", token)
```

No Graph API call is needed — group Object IDs can be passed directly to the Fabric role assignment API.

---

## Multi-Tenant Support

Parameterize the Fabric API base URL and the Graph tenant in the runbook to support deployments that span multiple Entra tenants or sovereign clouds:

```python
FABRIC_API_BASE = os.getenv("FABRIC_API_BASE", "https://api.fabric.microsoft.com")
GRAPH_API_BASE  = os.getenv("GRAPH_API_BASE",  "https://graph.microsoft.com")
```

Store these as Automation Account variables for easy configuration.

---

## Intelligent Item Recommendation (Roadmap)

The most promising evolution of this solution is to turn the wizard into an **intelligent questionnaire**. Instead of asking the user *what* they want to create, ask about their use case, data, and goals — and automatically recommend the most appropriate Fabric item(s).

This doubles as a **lightweight knowledge assessment**: analysing the answers can surface targeted governance recommendations and best practices at exactly the moment the user is most receptive — when they are configuring something for their own stated goal.

| Enhancement | Description |
|---|---|
| **Multi-item questionnaire flow** | Branching wizard that recommends Lakehouse, Warehouse, Notebook, or Data Agent based on user answers |
| **Knowledge-level detection** | Score answers to estimate Fabric familiarity and tailor recommendations |
| **Contextual best-practice prompts** | Surface governance and naming guidelines inline, framed around the user's current input |
| **Approval workflow** | Human-in-the-loop approval before provisioning (Logic App / Power Automate) |
| **Audit trail** | Persist runbook output to Azure Storage or Log Analytics |
| **Entra Group support** | Assign workspace roles to groups rather than individuals |
| **Naming convention enforcement** | Regex-based validation at wizard level before submission |
