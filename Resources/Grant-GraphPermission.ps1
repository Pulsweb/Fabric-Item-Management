# ============================================================
# Grants the User.Read.All (Application) permission on
# Microsoft Graph to the Automation Account's Managed Identity
# ============================================================

# Object ID of the Managed Identity (replace with your actual value — visible in
# Automation Account → Identity → System assigned → Object ID)
$ManagedIdentityObjectId = "###-###-###-###-############"

# Connect to Microsoft Graph with sufficient permissions
Connect-MgGraph -Scopes "AppRoleAssignment.ReadWrite.All", "Application.Read.All"

# Retrieve the Microsoft Graph service principal
$GraphSP = Get-MgServicePrincipal -Filter "appId eq '00000003-0000-0000-c000-000000000000'"

# Retrieve the App Role ID for User.Read.All (application permission, not delegated)
$AppRole = $GraphSP.AppRoles | Where-Object { $_.Value -eq "User.Read.All" -and $_.AllowedMemberTypes -contains "Application" }

Write-Host "App Role found: $($AppRole.Id) ($($AppRole.Value))"

# Assign the role to the Managed Identity
$Body = @{
    PrincipalId = $ManagedIdentityObjectId
    ResourceId  = $GraphSP.Id
    AppRoleId   = $AppRole.Id
}

New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $ManagedIdentityObjectId -BodyParameter $Body

Write-Host "✅ User.Read.All permission granted to the Managed Identity."
