# Terraform State Bootstrap

This folder creates the Azure Storage resources used for remote Terraform state.

It exists as a separate bootstrap step because the main App Service workspace
cannot safely store its own state in infrastructure that it is also creating.

## What It Creates

- Azure Resource Group
- Azure Storage Account
- Private blob container for Terraform state

## Why This Matters

The Azure `azurerm` backend stores Terraform state in Azure Blob Storage and
uses Azure Blob locking/leases to protect the state file from concurrent writes.

Sources:

- HashiCorp `azurerm` backend docs: https://developer.hashicorp.com/terraform/language/settings/backends/azurerm
- Microsoft Learn state storage guide: https://learn.microsoft.com/en-us/azure/developer/terraform/store-state-in-azure-storage

## Usage

From this folder:

```powershell
terraform init
terraform apply
```

Then copy the output values into a file named `backend.hcl` in the main
workspace folder:

```text
infra/terraform/azure-app-service/backend.hcl
```

You can start from:

```text
infra/terraform/azure-app-service/backend.hcl.example
```

## Next Step

After the state storage exists, initialize the main workspace with:

```powershell
terraform -chdir=..\azure-app-service init -backend-config=backend.hcl
```
