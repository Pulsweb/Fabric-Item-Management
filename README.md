<img src="AzureWebApp/logo.png" alt="Fabric Item Management" width="128" />

# Fabric Item Management

> **Enabling the controlled use of specific Microsoft Fabric items without exposing them to the entire organization.**

A template solution that lets end users provision Fabric items (starting with Data Agents) through a guided web wizard without ever needing direct Fabric creation rights. Governance, cost control, and naming conventions are enforced server-side by an Azure Automation Runbook running under a Managed Identity.

---

## Context & Problem

Many organizations want to leverage Microsoft Fabric items—such as Data Agents, Lakehouses, and Notebooks—without exposing the full Fabric surface area to every user. Their main concerns typically include:
- Capacity overconsumption, especially in environments where Power BI workloads are already running
- Redundant investments, duplicating existing cloud or data platform capabilities
- Governance, including who can create which items, in which locations, and under which naming conventions

While security groups can be applied at the tenant or capacity level, this model remains all‑or‑nothing. In practice, this does not align with many real‑world scenarios—for example, allowing users to create Data Agents on a specific capacity without granting them permission to create other items such as Notebooks.
⚠️ Important: I do not recommend disabling Fabric workloads. Microsoft Fabric was designed as a unified SaaS platform, where tightly integrated workloads deliver a consistent experience and maximum value. Although the need for more granular controls is well understood and actively monitored by the Product Group, it is not currently available.

This solution addresses a key question: *How can we enable targeted, controlled, and gradual access to specific Fabric items—without compromising cost control, governance, or platform performance?*

---

## Quick Links

| | |
|---|---|
| 🏗️ [Architecture & How It Works](Docs/architecture.md) | Component diagram, data flow, security model |
| 🚀 [Deployment Guide](Docs/deployment-guide.md) | Run locally (open `index.html`) or deploy to Azure Static Web App |
| ✅ [Approval Workflow](Docs/approval-workflow.md) | Add a human-in-the-loop gate before provisioning |
| 🔧 [Troubleshooting](Docs/troubleshooting.md) | Common errors and fixes |
| 🔭 [Extending the Solution](Docs/extending.md) | Add new item types, audit logging, naming rules |

---

## What It Does

End users open a 5-step wizard in the browser and fill in a workspace name, optional capacity, agent name, and an optional admin user. The form POSTs a JSON payload to an Azure Automation Webhook. A Python Runbook — running as a System-assigned Managed Identity — handles all Fabric API calls server-side. The user never needs Fabric creation rights.

```
End user  →  Azure Static Web App (wizard)
                     │
                     │  POST JSON
                     ▼
          Azure Automation Webhook
                     │
                     ▼
          Azure Automation Runbook (Python 3.10)
          ├─► Fabric REST API  — create workspace, assign capacity, create Data Agent
          └─► Microsoft Graph  — resolve UPN → Object ID, assign workspace roles
```

---

## Story

Leo an end user don't have permission to create Fabric Item, he open the Web App and specify is need :

### Welcome screen — item type selection
![Welcome screen](Media/screenshot-welcome.png)

### Step 1 — Workspace
![Step 1: Workspace](Media/screenshot-step1-workspace.png)

### Step 2 — Fabric Capacity (If required)
![Step 2: Capacity](Media/screenshot-step2-capacity.png)

### Step 3 — Conversational Agent
![Step 3: Agent](Media/screenshot-step3-agent.png)

### Step 4 — Administrator
![Step 4: Admin](Media/screenshot-step4-admin.png)

### Step 5 — Review & Submit
![Step 5: Review & Submit](Media/screenshot-step5-review.png)

Leo copy the Azure Automation Webhook URL containing the token that that administrator shared (it could be made diferently), something like that https://###.webhook.usw3.azure-automation.net/webhooks?token=###

### Step 6 — Deployment triggered
![Step 6: Deployment triggered](Media/screenshot-processing.png)

### Step 7 — 
![Step 7: Deployment triggered](Media/screenshot-AzureRubboksExecution.png)

### Step 8 — Data Agent configuration
![Step 8: Deployment triggered](Media/screenshot-AzureRubboksExecution.png)


---

## Security at a Glance

- **No credentials stored** — authentication uses the System-assigned Managed Identity only.
- **Webhook URL is the only secret** — treat it like a password; do not commit it to source control.
- **Least-privilege** — the Managed Identity has only `User.Read.All` on Graph and membership on target Fabric workspaces.
- **XSS prevention** — all user input is passed through `escapeHtml()` before DOM insertion.

See [Architecture](Docs/architecture.md) for the full security model.

---

## Authors

Co-designed with the invaluable input of [Emilie Beau](https://www.linkedin.com/in/emilie-beau/) and [Christopher Maneu](https://www.linkedin.com/in/cmaneu/), and accelerated using VS Code Copilot and Claude Sonnet 4.6.

---

**Built with ❤️ for the Microsoft Fabric community**


