# Azure ID Reference

These Azure identifiers look similar but come from different places and are
used for different purposes.

## `AZURE_CLIENT_ID`

What it is:

- the application/client ID of the Microsoft Entra app registration used by
  GitHub Actions

Where it comes from:

- `Microsoft Entra ID` -> `App registrations` -> `bonzo-assistant-github`
- field: `Application (client) ID`

How this repo uses it:

- GitHub secret `AZURE_CLIENT_ID`
- used by `azure/login` with OIDC

## `AZURE_TENANT_ID`

What it is:

- the Microsoft Entra directory/tenant ID

Where it comes from:

- `Microsoft Entra ID` overview
- field: `Tenant ID`

How this repo uses it:

- GitHub secret `AZURE_TENANT_ID`
- tells Azure which tenant the GitHub identity should authenticate against

## `AZURE_SUBSCRIPTION_ID`

What it is:

- the Azure subscription ID that owns the deployed resources

Where it comes from:

- Azure subscription overview
- or `az account show`

How this repo uses it:

- GitHub secret `AZURE_SUBSCRIPTION_ID`
- scopes GitHub Actions to the correct subscription

## `DEPLOYMENT_PRINCIPAL_OBJECT_ID`

What it is:

- the object ID of the GitHub deployment service principal in Microsoft Entra

Where it comes from:

- service principal for the app registration
- can be found with:

```powershell
az ad sp list --display-name bonzo-assistant-github --query "[0].id" -o tsv
```

How this repo uses it:

- GitHub environment variable `DEPLOYMENT_PRINCIPAL_OBJECT_ID`
- lets Terraform grant stable App Configuration and Key Vault bootstrap access
  to the GitHub deployment identity

## `LOCAL_OPERATOR_OBJECT_ID`

What it is:

- the object ID of your human user account in Microsoft Entra

Where it comes from:

- your user record in `Microsoft Entra ID` -> `Users`
- or:

```powershell
az ad signed-in-user show --query id -o tsv
```

How this repo uses it:

- optional GitHub/Terraform value `LOCAL_OPERATOR_OBJECT_ID`
- lets Terraform keep local operator access stable too, instead of fighting with
  the GitHub service principal over "current caller" access

## Quick Mental Model

- `client ID` = app identity name used for login
- `tenant ID` = directory boundary
- `subscription ID` = billing/resource boundary
- `object ID` = actual Entra object instance for a user or service principal
