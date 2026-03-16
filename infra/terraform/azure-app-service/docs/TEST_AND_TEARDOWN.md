# Test And Teardown

This file is a practical runbook for spinning up the Azure stack, testing it,
and removing it afterward.

## Goal

Use the infrastructure briefly for learning or validation, then destroy the
cost-driving resources when you are done.

## Suggested Order

1. Create the remote state bootstrap once
2. Create the main app stack
3. Test the app and deployment flow
4. Destroy the main app stack
5. Optionally destroy the bootstrap state resources too

## 1. Bootstrap Remote State

If the Terraform state storage does not exist yet:

```powershell
cd g:\bonzo-assistant\infra\terraform\bootstrap-state
terraform init
terraform apply
```

Then copy the bootstrap outputs into:

```text
g:\bonzo-assistant\infra\terraform\azure-app-service\backend.hcl
```

## 2. Create The Main App Stack

From the app stack folder:

```powershell
cd g:\bonzo-assistant\infra\terraform\azure-app-service
terraform init -backend-config=backend.hcl
terraform workspace select dev
terraform plan
terraform apply
```

If the `dev` workspace does not exist yet:

```powershell
terraform workspace new dev
```

## 3. Capture Useful Outputs

After apply, collect the main values you will test with:

```powershell
terraform output web_app_url
terraform output web_app_name
terraform output acr_name
terraform output acr_login_server
terraform output resource_group_name
```

## 4. Test The Deployment

Recommended first checks:

- Open the deployed `web_app_url`
- Confirm the app loads
- Confirm `mock_mode = true` behavior works as expected
- Confirm app settings are loading from Azure

If you want to test the container push flow manually:

```powershell
az acr login --name <acr-name>
docker build -t <acr-login-server>/bonzo-assistant:latest .
docker push <acr-login-server>/bonzo-assistant:latest
```

If you want to test GitHub automation too:

- run `deploy-infra.yml` with `plan`
- run `deploy-app.yml` manually for `dev`
- set GitHub environment variable `AUTO_DEPLOY_ENABLED=true` only while the
  `dev` app infrastructure actually exists if you want `main` pushes to deploy
  automatically

## 5. Destroy The Main App Stack

When testing is complete:

```powershell
cd g:\bonzo-assistant\infra\terraform\azure-app-service
terraform workspace select dev
terraform destroy
```

Important:

- Let Azure deletes finish even if they are slow
- Key Vault deletion in particular can take several minutes

## 6. Verify The Cost Drivers Are Gone

Confirm the main app resource group has been removed, or at least verify these
resources are gone:

- App Service plan
- Web App
- Azure Container Registry
- Azure App Configuration
- Key Vault

## 7. Decide Whether To Keep Bootstrap State

Keeping `bootstrap-state` is often useful because it is cheap and reusable for
future Terraform projects.

If you want to destroy it too:

```powershell
cd g:\bonzo-assistant\infra\terraform\bootstrap-state
terraform init
terraform destroy
```

Destroy bootstrap last, after the main app stack is already gone.

## 8. Optional Full Reset

If you want a complete cleanup beyond Azure resources, also remove:

- GitHub environment secrets and variables
- GitHub `dev` / `prod` environments if no longer needed
- Microsoft Entra app registration used for GitHub Actions
- Azure role assignments created for that identity

If you want to keep the GitHub environment but avoid failed automatic app
deploys after teardown:

- leave the GitHub environment in place
- set `AUTO_DEPLOY_ENABLED=false`
- next time, run `Deploy Infrastructure` first, then either turn
  `AUTO_DEPLOY_ENABLED=true` back on or run `Deploy App` manually

## Practical Cost Reminder

For this repo, the main ongoing costs are:

- App Service Plan `B1`
- Azure Container Registry `Basic`
- Azure App Configuration

If you create the stack briefly, test it, and then destroy it, your spend
should be much lower than leaving it running for a full month.
