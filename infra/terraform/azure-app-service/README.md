# Azure App Service Terraform

This folder provisions a beginner-friendly Azure hosting stack for `bonzo-assistant`:

- Azure Resource Group
- Azure Container Registry
- Linux App Service Plan
- Linux App Service running the container
- Azure Key Vault
- Azure App Configuration

## Documentation Map

Use these docs together:

- `README.md`
  - primary setup and architecture guide
- `docs/TROUBLESHOOTING.md`
  - errors we hit and how we fixed them
- `docs/COSTS.md`
  - rough cost expectations for dev/test use
- `docs/TEST_AND_TEARDOWN.md`
  - short-lived apply, test, destroy workflow
- `docs/COMMANDS.md`
  - quick command reference for setup and debugging

For setup issues we hit along the way, keep notes in:

```text
docs/TROUBLESHOOTING.md
```

For rough cost expectations for this stack, see:

```text
docs/COSTS.md
```

For a short-lived apply/test/destroy runbook, see:

```text
docs/TEST_AND_TEARDOWN.md
```

For a command reference used during setup and debugging, see:

```text
docs/COMMANDS.md
```

For a quick guide to the Azure IDs used in GitHub and Terraform, see:

```text
docs/ID_REFERENCE.md
```

## Remote State First

Before you run this workspace, create the remote Terraform state storage in:

```text
../bootstrap-state
```

That bootstrap workspace creates the Azure Storage account and blob container
used by the `azurerm` backend.

The Azure `azurerm` backend stores state in Azure Blob Storage and supports
state locking using Azure Blob native locking/lease behavior.

Sources:

- HashiCorp `azurerm` backend docs: https://developer.hashicorp.com/terraform/language/settings/backends/azurerm
- Microsoft Learn state storage guide: https://learn.microsoft.com/en-us/azure/developer/terraform/store-state-in-azure-storage

## What Goes Where

- App Service runs the container
- ACR stores the Docker image
- Key Vault stores `OPENAI_API_KEY`
- App Configuration stores non-secret app settings like:
  - `OPENAI_MODEL`
  - `EMBEDDING_MODEL`
  - `MOCK_MODE`
  - `APP_MODEL_CONTEXT_WINDOW`

The app is wired so it can:

- read `OPENAI_API_KEY` from an App Service environment variable backed by Key Vault
- read non-secret settings from Azure App Configuration using managed identity

## Before You Apply

1. Build and test the app locally.
2. Copy `terraform.tfvars.example` to `terraform.tfvars`.
3. Fill in any values you want to override.
4. If you want real OpenAI calls, set `openai_api_key`.
5. If you want a free learning deployment first, keep `mock_mode = true`.

## Terraform Commands

From this folder:

```powershell
terraform init -backend-config=backend.hcl
terraform workspace new dev
terraform plan -out tfplan
terraform apply tfplan
```

If you already created the workspace:

```powershell
terraform workspace select dev
```

The Terraform workspace name becomes the Azure environment label used in App Configuration.

Start by copying:

```text
backend.hcl.example
```

to:

```text
backend.hcl
```

and then replace the values with the outputs from the bootstrap-state workspace.

## Push The Container Image

After Terraform creates ACR, build and push the image:

```powershell
az acr login --name <acr-name>
docker build -t <acr-login-server>/bonzo-assistant:latest .
docker push <acr-login-server>/bonzo-assistant:latest
```

You can get the full expected image name from the Terraform output:

```powershell
terraform output docker_image_reference
```

## Important Notes

- App Service is configured to persist app files under `/home/site/data/...`
- `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true` is set so local docs, chat history, and Chroma data have persistent storage
- WebSockets must be enabled on the App Service app because the hosted Streamlit UI relies on them
- App Service uses a system-assigned managed identity
- That identity gets:
  - `AcrPull` on ACR
  - `App Configuration Data Reader` on App Configuration
  - secret read access in Key Vault
- The Terraform caller also gets `App Configuration Data Owner` on the App Configuration store so Terraform can create the initial key-values during apply
- Terraform ignores later changes to the running container image tag so GitHub Actions can deploy new image SHAs without Terraform immediately rolling them back on the next infra apply

## GitHub Actions CD

This repo includes two deployment workflows:

- `deploy-app.yml`
  - automatically deploys `main` to the `dev` GitHub environment after the `CI` workflow succeeds
  - can also be run manually for `dev` or `prod`
  - builds the Docker image, pushes it to ACR, and points App Service at the pushed SHA tag
- `deploy-infra.yml`
  - runs Terraform manually for the `dev` or `prod` workspace
  - supports `plan` and `apply`

Recommended GitHub environment setup:

- Create GitHub environments named `dev` and `prod`
- Add environment secrets:
  - `AZURE_CLIENT_ID`
  - `AZURE_TENANT_ID`
  - `AZURE_SUBSCRIPTION_ID`
  - `OPENAI_API_KEY` if you are not staying in mock mode
- Add environment variables:
  - `AZURE_WEBAPP_NAME`
  - `AZURE_RESOURCE_GROUP`
  - `AZURE_CONTAINER_REGISTRY_NAME`
  - `AZURE_CONTAINER_REGISTRY_LOGIN_SERVER`
  - `AZURE_CONTAINER_REPOSITORY`
  - `TF_STATE_RESOURCE_GROUP`
  - `TF_STATE_STORAGE_ACCOUNT`
  - `TF_STATE_CONTAINER`
  - `DEPLOYMENT_PRINCIPAL_OBJECT_ID`

Helpful Terraform outputs to copy into GitHub:

- `terraform output web_app_name`
- `terraform output acr_name`
- `terraform output acr_login_server`

The Azure identity used by GitHub Actions should have:

- `AcrPush` on ACR for app deployments
- `Website Contributor` on the App Service app for container deployments
- `Storage Blob Data Contributor` on the Terraform state storage account or container
- enough Azure rights to create/update the infrastructure resources managed by Terraform

For the infrastructure workflow, the simplest beginner-friendly option is:

- `Contributor` on the resource group used by this workspace
- `User Access Administrator` on that same resource group

Why both are needed:

- `Contributor` lets Terraform create and update most Azure resources
- `User Access Administrator` lets Terraform create the role assignments in this repo, such as:
  - `AcrPull` for the App Service managed identity
  - `App Configuration Data Reader` for the App Service managed identity
  - `App Configuration Data Owner` for the Terraform caller so it can write App Configuration keys

If you prefer one broader role while learning, `Owner` on the resource group also works, but it is more permission than most teams want long term.

## Click-By-Click GitHub To Azure Setup

This is the easiest order to follow the first time.

### 1. Create the Azure resources first

Use the Terraform steps in this folder so Azure creates:

- the App Service app
- the ACR registry
- the Key Vault
- the App Configuration store

The GitHub environment values later come from these Terraform outputs.

### 2. Create a Microsoft Entra app registration for GitHub Actions

In the Azure portal:

1. Go to `Microsoft Entra ID`
2. Open `App registrations`
3. Click `New registration`
4. Give it a name such as `bonzo-assistant-github`
5. Leave it as a single-tenant app unless you know you need something else
6. Create it

After that, save these values:

- `Application (client) ID`
- `Directory (tenant) ID`

You will also use your Azure subscription ID from the subscription that hosts the app.

### 3. Add federated credentials for GitHub environments

Open the app registration and:

1. Go to `Certificates & secrets`
2. Open `Federated credentials`
3. Click `Add credential`
4. Choose the GitHub Actions scenario

Create one credential for `dev` and one for `prod`.

Use these values:

- Organization: your GitHub org or username
- Repository: your repo name
- Entity type: `Environment`
- Environment name: `dev` for the first credential

Then repeat for `prod`.

The important idea is that the Azure identity should trust:

- `repo:<owner>/<repo>:environment:dev`
- `repo:<owner>/<repo>:environment:prod`

That keeps each GitHub environment mapped to its matching Azure trust rule.

### 4. Grant Azure roles to that app registration

Use the service principal created for the app registration and grant:

- for `deploy-app.yml`
  - `AcrPush` on the ACR resource
  - `Website Contributor` on the App Service resource
- for `deploy-infra.yml`
  - `Storage Blob Data Contributor` on the Terraform state storage account or state container
  - `Contributor` on the resource group
  - `User Access Administrator` on the resource group

If you are still in a learning phase, you can scope these at the resource group instead of each individual resource to keep setup simpler.

### 5. Create GitHub environments

In GitHub:

1. Open the repo
2. Go to `Settings`
3. Open `Environments`
4. Create `dev`
5. Create `prod`

If you want a safer production flow, add required reviewers to `prod`.

### 6. Add GitHub environment secrets

For both `dev` and `prod`, add these secrets:

- `AZURE_CLIENT_ID`
  - from the Azure app registration
- `AZURE_TENANT_ID`
  - from Microsoft Entra ID
- `AZURE_SUBSCRIPTION_ID`
  - from the Azure subscription
- `OPENAI_API_KEY`
  - only if that environment will run with `mock_mode = false`

### 7. Add GitHub environment variables

For both `dev` and `prod`, add these variables:

- `AZURE_WEBAPP_NAME`
- `AZURE_RESOURCE_GROUP`
- `AZURE_CONTAINER_REGISTRY_NAME`
- `AZURE_CONTAINER_REGISTRY_LOGIN_SERVER`
- `AZURE_CONTAINER_REPOSITORY`
- `TF_STATE_RESOURCE_GROUP`
- `TF_STATE_STORAGE_ACCOUNT`
- `TF_STATE_CONTAINER`
- `DEPLOYMENT_PRINCIPAL_OBJECT_ID`

Optional variables the infrastructure workflow can also use:

- `NAME_PREFIX`
- `LOCATION`
- `APP_SERVICE_PLAN_SKU_NAME`
- `ACR_SKU`
- `APP_CONFIGURATION_SKU`
- `CONTAINER_IMAGE_TAG`
- `MOCK_MODE`
- `OPENAI_MODEL`
- `EMBEDDING_MODEL`
- `OPENAI_BASE_URL`
- `APP_MODEL_CONTEXT_WINDOW`
- `APP_CONFIGURATION_KEY_PREFIX`
- `LOCAL_OPERATOR_OBJECT_ID`

### 8. Fill those values from Terraform outputs

After your first infrastructure apply, these commands are the most useful:

```powershell
terraform output web_app_name
terraform output acr_name
terraform output acr_login_server
terraform output resource_group_name
```

The bootstrap-state workspace gives you:

```powershell
terraform output resource_group_name
terraform output storage_account_name
terraform output container_name
```

That maps into GitHub like this:

- `AZURE_WEBAPP_NAME` = `web_app_name`
- `AZURE_RESOURCE_GROUP` = `resource_group_name`
- `AZURE_CONTAINER_REGISTRY_NAME` = `acr_name`
- `AZURE_CONTAINER_REGISTRY_LOGIN_SERVER` = `acr_login_server`
- `AZURE_CONTAINER_REPOSITORY` = usually `bonzo-assistant`
- `TF_STATE_RESOURCE_GROUP` = bootstrap-state `resource_group_name`
- `TF_STATE_STORAGE_ACCOUNT` = bootstrap-state `storage_account_name`
- `TF_STATE_CONTAINER` = bootstrap-state `container_name`
- `DEPLOYMENT_PRINCIPAL_OBJECT_ID` = object ID of the GitHub service principal, not the application/client ID

### 9. Run the workflows

Normal path:

1. push to `main`
2. `CI` runs
3. if `CI` passes, `deploy-app.yml` deploys to the `dev` environment

Manual path:

1. open GitHub Actions
2. run `Deploy Infrastructure`
3. choose `dev` or `prod`
4. choose `plan` or `apply`

You can also run `Deploy App` manually for either environment.

Important reminder:

- GitHub Actions builds and deploys the code that is committed and pushed to
  GitHub, not uncommitted local workspace changes

## How The App Reads Config In Azure

At startup, the app:

1. reads normal environment variables
2. checks `APP_CONFIGURATION_ENDPOINT`
3. if present, loads matching keys from Azure App Configuration
4. keeps existing App Service environment variables as overrides

That means:

- secrets can stay in Key Vault
- shared non-secrets can stay in App Configuration
- App Service app settings can still override anything for emergencies
