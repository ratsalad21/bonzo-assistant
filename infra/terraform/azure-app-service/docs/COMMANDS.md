# Azure Terraform Command Cheat Sheet

This is a quick-reference list of the commands that were most useful while
setting up and debugging the Azure App Service deployment for `bonzo-assistant`.

## Terraform Basics

```powershell
terraform init -backend-config=backend.hcl
```

Initializes the Terraform workspace and connects it to remote state.

```powershell
terraform workspace select dev
terraform workspace new dev
```

Selects or creates the environment workspace.

```powershell
terraform plan
terraform apply
terraform destroy
```

Shows changes, creates/updates infrastructure, or removes it.

```powershell
terraform output
terraform output web_app_url
```

Shows useful created-resource values after apply.

## Azure Login And Subscription Checks

```powershell
az login --use-device-code
```

Signs into Azure in a way that works well with MFA.

```powershell
az account list --all -o table
az account show -o table
az account set --subscription "<subscription-id>"
```

Confirms which subscription and tenant you are actually using.

## ACR Image Checks

```powershell
az acr login --name <acr-name>
```

Authenticates Docker to your Azure Container Registry.

```powershell
docker build -t <acr-login-server>/bonzo-assistant:latest .
docker push <acr-login-server>/bonzo-assistant:latest
```

Builds and pushes the image App Service expects.

```powershell
az acr repository show-tags --name <acr-name> --repository bonzo-assistant --output table
```

Confirms the expected image tag really exists in ACR.

## Web App Runtime Checks

```powershell
az webapp list --query "[?contains(name, 'bonzo')].[name,resourceGroup]" -o table
```

Finds the Web App name and resource group.

```powershell
az webapp show --name <web-app-name> --resource-group <resource-group> --query "{state:state, defaultHostName:defaultHostName}" -o json
```

Checks whether the Web App is running and shows the main hostname.

```powershell
az webapp restart --name <web-app-name> --resource-group <resource-group>
```

Restarts the Web App after image pushes or config changes.

```powershell
az webapp config container show --name <web-app-name> --resource-group <resource-group>
```

Shows the exact registry/image reference App Service is trying to run.

```powershell
az webapp config appsettings list --name <web-app-name> --resource-group <resource-group> -o json
```

Shows the live app settings, including `WEBSITES_PORT`.

```powershell
az webapp identity show --name <web-app-name> --resource-group <resource-group> --query principalId -o tsv
```

Gets the managed identity principal ID used for ACR and App Configuration access.

## Web App Logging

```powershell
az webapp log config --name <web-app-name> --resource-group <resource-group> --application-logging filesystem --docker-container-logging filesystem --level information
```

Turns on App Service filesystem logs for debugging.

```powershell
az webapp log tail --name <web-app-name> --resource-group <resource-group>
```

Streams live logs from the Web App.

```powershell
az webapp log download --name <web-app-name> --resource-group <resource-group> --log-file appservice-logs.zip
```

Downloads the full App Service log bundle when tailing is not enough.

## Role And Access Checks

```powershell
az role assignment list --all --query "[?roleDefinitionName=='AcrPull'].[principalId,scope]" -o table
```

Checks whether the Web App identity has `AcrPull`.

```powershell
az storage container list --account-name "<storage-account-name>" --auth-mode login
```

Useful for confirming blob access to the Terraform remote state backend.

## Good Mental Model

Use the commands in this order when something breaks:

1. Confirm the right Azure subscription
2. Confirm the image exists in ACR
3. Confirm the Web App is pointing at the expected image
4. Confirm the Web App is running
5. Turn on logs and inspect startup behavior
