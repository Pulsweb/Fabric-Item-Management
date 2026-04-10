# Troubleshooting

[← Back to README](../README.md)

---

## Common Errors

| Symptom | Likely Cause | Resolution |
|---|---|---|
| `IDENTITY_ENDPOINT / IDENTITY_HEADER not found` | System-assigned Managed Identity is not enabled | Enable in **Automation Account → Identity → System assigned** |
| `Fabric API returns 403 Forbidden` | `Service principals can use Fabric APIs` is disabled | Enable in **Fabric Admin Portal → Tenant Settings → Developer settings** |
| `Capacity 'X' not found` | The MI does not have at least Contributor rights on the capacity | Assign the MI as Contributor on the Fabric capacity in the Azure Portal |
| `Unable to resolve UPN` | `User.Read.All` not granted to the MI | Run `Resources/Grant-GraphPermission.ps1` with the correct Object ID |
| `Workspace 'X' already exists but the Managed Identity is not a member` | Workspace exists but MI has no access | Add the MI as a member of the workspace in Fabric UI, then re-run |
| `ItemDisplayNameAlreadyInUse` | A Data Agent with that name already exists in the workspace | Use a different agent name, or delete the existing agent in Fabric first |
| SWA shows "Connection error / Failed to fetch" | Browser CORS preflight blocked by Azure Automation (old app version) | Update to the latest `AzureWebApp/app.js` — it now uses `mode: no-cors` which avoids the preflight entirely |
| `[WARN] Unable to parse RequestBody` | The JSON body sent by the SWA is malformed | Check the payload in the **Input** tab of the Automation job |
| Runbook job shows `202 Accepted` but nothing is created | Parameters were not passed to the runbook (old version of Runbook.py) | Ensure you are using the latest version of `AzureAutomation/Runbook.py` |

---

## How to Read the Runbook Output

1. In the Azure Portal, go to **Automation Account → Jobs**.
2. Open the most recent job.
3. Use the **Output** tab for `print()` messages (normal flow).
4. Use the **Exception** tab for Python stack traces (unhandled errors).
5. Use the **All Logs** tab to see all streams together.

A successful run ends with:
```
[SUCCESS] Data Agent created:
  Name        : <agent-name>
  ID          : <item-id>
  Workspace   : <workspace-id>
  Type        : DataAgent
```

---

## Checking What the Webhook Received

Open the job and click the **Input** tab. You will see the raw `webhookData` string passed to the runbook by Azure Automation. This is useful for diagnosing JSON parsing failures — look for unescaped characters or missing fields in the `RequestBody`.

---

## Verifying Graph Permissions

If UPN resolution fails, confirm that the `User.Read.All` application permission was granted:

```powershell
Connect-MgGraph -Scopes "Application.Read.All"
$sp = Get-MgServicePrincipal -Filter "id eq '<MANAGED-IDENTITY-OBJECT-ID>'"
Get-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $sp.Id |
    Select-Object AppRoleId, PrincipalDisplayName
```

The output should include a role assignment with the `User.Read.All` App Role ID (`df021288-bdef-4463-88db-98f22de89214`).
