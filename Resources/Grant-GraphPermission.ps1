# ============================================================
# Grants the User.Read.All (Application) permission on
# Microsoft Graph to the Automation Account's Managed Identity
# ============================================================

# Object ID of the Managed Identity (replace with your actual value — visible in
# Automation Account → Identity → System assigned → Object ID)
$ManagedIdentityObjectId = "###-###-###-###-############"

# Connect to Microsoft Graph with sufficient permissions
Connect-MgGraph -Scopes "AppRoleAssignment.ReadWrite.All", "Application.Read.All"

# Retrieve the Microsoft Graph service principal — explicitly include AppRoles
# (Graph PowerShell SDK v2 does not expand all properties by default)
$GraphSP = Get-MgServicePrincipal -Filter "appId eq '00000003-0000-0000-c000-000000000000'" `
           -Property "id,appId,displayName,appRoles"

# Retrieve the App Role ID for User.Read.All (application permission, not delegated)
$AppRole = $GraphSP.AppRoles | Where-Object { $_.Value -eq "User.Read.All" -and $_.AllowedMemberTypes -contains "Application" }

if (-not $AppRole -or -not $AppRole.Id) {
    Write-Error "❌ Could not find the User.Read.All application role on Microsoft Graph."
    Write-Host  "   Try re-running after a moment, or verify the Graph PowerShell module version."
    exit 1
}

Write-Host "App Role found: $($AppRole.Id) ($($AppRole.Value))"

# Assign the role to the Managed Identity
$Body = @{
    PrincipalId = $ManagedIdentityObjectId
    ResourceId  = $GraphSP.Id
    AppRoleId   = $AppRole.Id
}

try {
    New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $ManagedIdentityObjectId -BodyParameter $Body -ErrorAction Stop
    Write-Host "✅ User.Read.All permission granted to the Managed Identity."
} catch {
    if ($_.Exception.Message -match "Permission being assigned already exists") {
        Write-Host "✅ User.Read.All is already assigned to the Managed Identity — no action needed."
    } else {
        Write-Error "❌ Failed to assign the role: $_"
        exit 1
    }
}
