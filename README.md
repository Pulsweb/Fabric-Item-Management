# Fabric Item Management

> **Enabling the controlled use of specific Microsoft Fabric items without exposing them to the entire organization.**

A template solution that lets end users provision Fabric items (starting with Data Agents) through a guided web wizard — without ever needing direct Fabric creation rights. Governance, cost control, and naming conventions are enforced server-side by an Azure Automation Runbook running under a Managed Identity.

---

## Outcome

> 📸 *Screenshots will be added here. Replace this section with your own images once available.*

<!-- Add your screenshots below. Example:
![Wizard welcome screen](Media/screenshot-welcome.png)
![Step 3 – Agent creation](Media/screenshot-agent-step.png)
![Azure Automation job output](Media/screenshot-job-output.png)
![Data Agent in Fabric workspace](Media/screenshot-fabric-agent.png)
-->

---

## Quick Links

| | |
|---|---|
| 🏗️ [Architecture & How It Works](docs/architecture.md) | Component diagram, data flow, security model |
| 🚀 [Deployment Guide](docs/deployment-guide.md) | Step-by-step setup from zero to running |
| ✅ [Approval Workflow](docs/approval-workflow.md) | Add a human-in-the-loop gate before provisioning |
| 🔧 [Troubleshooting](docs/troubleshooting.md) | Common errors and fixes |
| 🔭 [Extending the Solution](docs/extending.md) | Add new item types, audit logging, naming rules |

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

## Repository Structure

```
Fabric-Item-Management/
├── README.md
├── docs/
│   ├── architecture.md          # Architecture diagram and component descriptions
│   ├── deployment-guide.md      # Step-by-step deployment instructions
│   ├── approval-workflow.md     # Approval workflow integration guide
│   ├── troubleshooting.md       # Common errors and resolutions
│   └── extending.md             # How to add new item types, audit logging, etc.
├── AzureWebApp/                  # Azure Static Web App
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── staticwebapp.config.json
├── AzureAutomation/
│   └── Runbook.py               # Azure Automation Runbook (Python 3.10)
├── Resources/
│   └── Grant-GraphPermission.ps1
└── Media/                        # Screenshots and images
```

---

## Security at a Glance

- **No credentials stored** — authentication uses the System-assigned Managed Identity only.
- **Webhook URL is the only secret** — treat it like a password; do not commit it to source control.
- **Least-privilege** — the Managed Identity has only `User.Read.All` on Graph and membership on target Fabric workspaces.
- **XSS prevention** — all user input is passed through `escapeHtml()` before DOM insertion.

See [Architecture](docs/architecture.md) for the full security model.

---

## Authors

Co-designed with the invaluable input of **Emilie** and **Christopher**, and accelerated using VS Code Copilot and Claude Sonnet 4.6.

*Keep it simple. Keep it controlled. Keep it scalable.*

---

**Built with ❤️ for the Microsoft Fabric community**
