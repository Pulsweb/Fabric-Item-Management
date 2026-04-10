# Approval Workflow

[← Back to README](../README.md)

---

## Overview

By default, the wizard submits the provisioning request directly to the Azure Automation Webhook — the Fabric item is created immediately with no human review. For organizations that want a **human-in-the-loop gate**, an approval step can be inserted between the SWA and the webhook.

This is useful when:

- Fabric capacity consumption needs to be authorized by the IT or Data Governance team before each provisioning
- A naming convention review is required before a workspace or agent is permanently created
- Provisioning is subject to a formal change-management or ITIL process
- Usage quotas need to be checked against a project or budget code before approval

---

## Proposed Architecture

```
SWA Wizard
    │
    │  POST request
    ▼
Logic App / Power Automate (Approval Gate)
    │
    ├──► Send approval request
    │       • Email (Outlook)
    │       • Adaptive Card in Microsoft Teams
    │
    │  Approver clicks Approve / Reject
    │
    ├──► [Approved] Forward original payload ──► Azure Automation Webhook ──► Runbook
    │
    └──► [Rejected] Notify requester
```

---

## Option A — Power Automate (No-Code)

The simplest path for organizations already using Microsoft 365.

### Steps

1. **Create a new Power Automate flow** with trigger: *When an HTTP request is received*.
2. Copy the generated HTTP endpoint URL — this is what you will paste in the SWA wizard instead of the direct webhook URL.
3. Add an **Approval** action (built-in connector):
   - Assign to: the IT admin or Data Governance team
   - Title: `Fabric provisioning request: [workspace_name] / [agent_name]`
   - Include the full payload details in the description for context
4. Add a **Condition** on the approval outcome:
   - **Approved** → HTTP action (POST) forwarding the original JSON body to the Azure Automation Webhook URL
   - **Rejected** → send a rejection notification to the requester (email or Teams message)

### Mapping to the SWA

In the wizard's **Step 5 — Review**, the user pastes the **Power Automate HTTP endpoint** instead of the direct Automation webhook URL. No changes to the SWA code are required.

---

## Option B — Azure Logic App (Enterprise / IaC-Friendly)

Preferred when:
- The organization uses Azure-native tooling
- The workflow needs to be version-controlled as Infrastructure as Code (Bicep/Terraform)
- More complex routing, retry logic, or audit logging is needed

### Trigger

Use the **HTTP Request** trigger to receive the JSON payload from the SWA.

### Approval Action

Use the **Office 365 Outlook — Send approval email** action or the **Teams — Post an Adaptive Card and wait for a response** action.

### Example Logic App skeleton (Bicep)

```bicep
resource logicApp 'Microsoft.Logic/workflows@2019-05-01' = {
  name: 'fabric-provisioning-approval'
  location: resourceGroup().location
  properties: {
    definition: {
      '$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#'
      triggers: {
        manual: {
          type: 'Request'
          kind: 'Http'
          inputs: {
            schema: {}
          }
        }
      }
      actions: {
        Send_approval_email: { /* ... */ }
        Condition: {
          actions: {
            Forward_to_webhook: {
              type: 'Http'
              inputs: {
                method: 'POST'
                uri: '<AUTOMATION_WEBHOOK_URL>'
                body: '@triggerBody()'
              }
            }
          }
          else: {
            actions: {
              Notify_rejection: { /* ... */ }
            }
          }
        }
      }
    }
  }
}
```

---

## What to Include in the Approval Request

Give approvers enough context to make an informed decision:

| Field | Description |
|---|---|
| `workspace_name` | The workspace to be created or reused |
| `agent_name` | The Data Agent to be created |
| `agent_description` | Stated purpose of the agent |
| `capacity_name` | Which capacity will consume CUs |
| `admin_user_object_id` | Who will be granted admin rights |
| Requester identity | Pull from the SWA session if authentication is added, or ask for it as an extra wizard field |
| Timestamp | When the request was submitted |

---

## Adding Requester Identity to the Wizard

If you want the approval email to identify who made the request, add a **Step 0 — Requester** to the wizard (`app.js`) that collects the user's email address, and include it in the JSON payload:

```json
{
  "workspace_name": "MyWorkspace",
  "agent_name": "MyAgent",
  "requester_email": "user@contoso.com",
  ...
}
```

The Runbook ignores unknown fields, so no backend change is required — only the approval flow needs to read `requester_email`.

---

## Security Considerations

- The Power Automate / Logic App endpoint becomes the new **externally exposed URL**. Apply IP restrictions or require authentication (e.g., Azure AD OAuth) if the SWA is not already restricted to internal users.
- The actual **Automation Webhook URL** (the one with the bearer token) should only be stored inside the Logic App / Power Automate flow — never exposed to the browser.
- Approval timeouts should be configured: auto-reject requests that are not actioned within a defined SLA (e.g., 48 hours) to avoid stale requests accumulating.
