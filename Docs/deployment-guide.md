# Deployment Guide

[← Back to README](../README.md)

---

## Prerequisites

### Azure Resources

| Resource | Purpose | Notes |
|---|---|---|
| Azure Automation Account | Hosts the runbook and webhook | Python 3.10 runtime required |
| Azure Static Web App | Hosts the wizard UI | Free tier is sufficient |
| Microsoft Fabric Capacity | Assigns workspaces to a capacity | Optional — Trial/Shared capacity can be used |

### Required Permissions

| Permission | Granted to | Purpose | How |
|---|---|---|---|
| `Service principals can use Fabric APIs` | Entire tenant | Allows the Managed Identity to call Fabric REST APIs | Fabric Admin Portal → Tenant Settings |
| `User.Read.All` (Graph Application) | Managed Identity | Resolves UPN email addresses to Entra Object IDs | `Resources/Grant-GraphPermission.ps1` |
| Fabric workspace member | Managed Identity | Required only when reusing an **existing** workspace | Manually in Fabric UI |

### Local Tools

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) or Azure Portal access
- [PowerShell](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell) + [Microsoft.Graph module](https://learn.microsoft.com/en-us/powershell/microsoftgraph/installation) (for `Grant-GraphPermission.ps1`)

---

## Step 1 — Create the Azure Automation Account

1. In the Azure Portal, create a new **Automation Account**.
2. Enable the **System-assigned Managed Identity** (in the Identity blade, or during creation).
3. Note the **Object ID** of the Managed Identity — you will need it in Step 3.
4. Verify that a **Python 3.10** runtime environment is available under **Runtime Environments**. Create one if not.

> **Tip**: The runbook uses only Python standard-library modules plus `automationassets` (built-in in Azure Automation). No extra packages need to be installed.

---

## Step 2 — Enable Fabric API Access for Service Principals

1. Open the [Microsoft Fabric Admin Portal](https://app.fabric.microsoft.com/admin-portal).
2. Navigate to **Tenant Settings** → **Developer settings**.
3. Enable **"Service principals can use Fabric APIs"**.
4. Optionally restrict this to an Entra security group containing only your Managed Identity.

---

## Step 3 — Grant Graph Permission to the Managed Identity

> Skip this step if you will only use Object IDs (not email/UPN addresses) for admin assignment.

1. Open `Resources/Grant-GraphPermission.ps1`.
2. Replace the placeholder with the Object ID noted in Step 1:

   ```powershell
   $ManagedIdentityObjectId = "<YOUR-MANAGED-IDENTITY-OBJECT-ID>"
   ```

3. Run the script with an account that has `AppRoleAssignment.ReadWrite.All` and `Application.Read.All`:

   ```powershell
   Connect-MgGraph -Scopes "AppRoleAssignment.ReadWrite.All", "Application.Read.All"
   .\Resources\Grant-GraphPermission.ps1
   ```

4. Verify the output ends with: `User.Read.All permission granted to the Managed Identity.`

---

## Step 4 — Import the Runbook

1. In your Automation Account, go to **Runbooks** → **Create a runbook**.
2. Set:
   - **Name**: `FabricItemManagement`
   - **Runbook type**: Python
   - **Runtime version**: 3.10
3. Paste the contents of `AzureAutomation/Runbook.py` into the editor.
4. Click **Save**, then **Publish**.

---

## Step 5 — Create the Automation Webhook

1. Open the published runbook → **Webhooks** → **Add webhook**.
2. Set:
   - **Name**: `FabricItemManagementWebhook`
   - **Enabled**: Yes
   - **Expiry**: an appropriate expiry date for your organization
3. **Copy the webhook URL immediately** — it is only shown once.
4. Click **OK** → **Create**.

> The URL looks like: `https://<region>.azure-automation.net/webhooks?token=<token>`

---

## Step 6 — Host the Web App

### Option A — Run locally (no deployment needed)

Because the wizard is a plain static web page, you can run it directly from your computer without deploying anything to Azure.

1. Clone or download this repository to your machine.
2. Open `AzureWebApp/index.html` in any modern browser (Chrome, Edge, Firefox).
3. The full 5-step wizard is immediately available.
4. On the final step, paste your Webhook URL and click **🚀 Deploy** — the browser POSTs directly to Azure Automation.

> This is the fastest way to get started and is perfectly suitable for internal or personal use. No web server, no hosting cost, no CI/CD pipeline required.

---

### Option B — Azure Static Web App (Portal)

1. Create a new **Static Web App** resource in the Portal.
2. After creation, deploy the `AzureWebApp/` folder using the **Azure Static Web Apps CLI**:

   ```bash
   npm install -g @azure/static-web-apps-cli
   swa deploy ./AzureWebApp --deployment-token <YOUR-SWA-DEPLOYMENT-TOKEN> --env production
   ```

### Option C — GitHub Actions (CI/CD)

Link the SWA to your GitHub repository. Azure will generate a workflow automatically. Set the **app location** to `AzureWebApp/`.

---

## Step 7 — Use the App

1. Navigate to your deployed SWA URL.
2. Click **Data Agent** on the welcome screen.
3. Complete the 5-step wizard:
   - **Step 1 — Workspace**: new or existing, provide the name.
   - **Step 2 — Capacity**: optionally assign to a named Fabric capacity.
   - **Step 3 — Agent**: name and optional description.
   - **Step 4 — Admin**: optional admin user (UPN or Object ID).
   - **Step 5 — Review**: confirm settings and enter the **Webhook URL** from Step 5.
4. Click **🚀 Deploy** to trigger the runbook.

---

## Testing

### End-to-End (Happy Path)

1. Open the SWA and complete the wizard with a new workspace name, a capacity, an agent name, and your UPN as admin.
2. In the Azure Portal → Automation Account → **Jobs**, open the most recent job.
3. Expected output:
   ```
   [INFO] Parameters read from webhook payload.
   [FOUND/NOT FOUND] ...workspace...
   [SUCCESS] Data Agent created:
     Name        : <your-agent-name>
   ```
4. In Microsoft Fabric, verify the workspace and Data Agent were created.

### Webhook Test via PowerShell

```powershell
$webhookUrl = "https://<region>.azure-automation.net/webhooks?token=<token>"

$payload = @{
    workspace_name       = "TestWorkspace"
    agent_name           = "MyTestAgent"
    agent_description    = "Created via PowerShell test"
    capacity_name        = ""
    admin_user_object_id = ""
} | ConvertTo-Json

Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $payload -ContentType "application/json"
```

Expected: HTTP `202 Accepted` with a JSON body containing a `jobId`.

### Direct Runbook Test (no SWA needed)

1. In the Automation Account, go to **Shared Resources** → **Variables** and create:

   | Variable | Type | Example |
   |---|---|---|
   | `workspace_name` | String | `TestWorkspace` |
   | `agent_name` | String | `TestAgent` |
   | `agent_description` | String | `Test run` |
   | `capacity_name` | String | *(empty if unused)* |
   | `admin_user_object_id` | String | *(empty if unused)* |

2. Open the runbook → **Start** → run with default parameters.
