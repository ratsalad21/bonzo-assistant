# Azure App Service Troubleshooting

This file is a running log of setup and deployment issues we hit while wiring
Azure, Terraform, and GitHub for `bonzo-assistant`.

Add new entries as we go so the next setup is faster.

## Entry Template

Use this format for new issues:

```text
## <Short title>

- Date:
- Area:
- Symptom:
- Cause:
- Fix:
- Follow-up:
```

## MFA Required During `az login`

- Date: 2026-03-16
- Area: Azure CLI authentication
- Symptom:
  `az login` failed with `AADSTS50076`, `invalid_grant`, and a message saying
  multi-factor authentication was required for tenant
  `23fc04a9-4a0c-42e5-b2f1-0c625936a388`.
- Cause:
  The tenant required an interactive MFA-capable sign-in flow. A normal login
  attempt was not enough after the directory policy/location change.
- Fix:

  ```powershell
  az logout
  az login --tenant 23fc04a9-4a0c-42e5-b2f1-0c625936a388 --use-device-code
  ```

  Complete the browser/device-code prompt, then verify access:

  ```powershell
  az account list --all -o table
  ```

- Follow-up:
  If login succeeds but Azure still says `No subscriptions found`, the account
  either does not have a subscription yet, is looking in the wrong tenant, or
  has not been granted access to the subscription.

## No Subscriptions Found After Login

- Date: 2026-03-16
- Area: Azure subscription access
- Symptom:
  Azure CLI reported `No subscriptions found for matte06@live.com`.
- Cause:
  Authentication can succeed while subscription discovery still fails. This is
  an access/tenant/subscription problem, not a Terraform problem.
- Fix:

  ```powershell
  az account list --all -o table
  ```

  If a subscription appears, set it explicitly:

  ```powershell
  az account set --subscription "<subscription-id>"
  az account show -o table
  ```

- Follow-up:
  If no subscription appears, confirm which tenant owns the subscription and
  whether the current account has permission in that tenant.

## `terraform init` Fails With Storage Backend 403

- Date: 2026-03-16
- Area: Terraform remote state backend
- Symptom:
  `terraform init -backend-config=backend.hcl` failed with:
  `Failed to get existing workspaces`, `403`, and
  `AuthorizationPermissionMismatch`.
- Cause:
  The backend in `backend.hcl` used Azure AD auth:

  ```hcl
  use_azuread_auth = true
  ```

  That means Terraform was trying to access the Azure Storage blob container
  using the signed-in Entra identity, but that identity did not yet have blob
  data-plane permissions on the state storage account.
- Fix:
  Assign `Storage Blob Data Contributor` to the signed-in user on the bootstrap
  Terraform state storage account, then wait a few minutes for RBAC
  propagation and retry:

  ```powershell
  terraform init -backend-config=backend.hcl
  ```

  Helpful verification commands:

  ```powershell
  az account show -o table
  az storage container list --account-name "<storage-account-name>" --auth-mode login
  ```

- Follow-up:
  This problem is about backend access only. It happens before Terraform can
  plan or apply the main app resources.

## User Appears As `(Guest)` In Azure Role Assignment

- Date: 2026-03-16
- Area: Azure IAM / Microsoft Entra identity
- Symptom:
  When assigning the storage role, the signed-in account only appeared as a
  guest user in the Azure portal.
- Cause:
  The account was operating as a guest identity in the tenant that owns the
  subscription. That is normal for invited Microsoft accounts and still works
  for RBAC assignments.
- Fix:
  Assign the required role to that guest identity as long as it is the same
  signed-in account and correct tenant/subscription context.

  Helpful verification commands:

  ```powershell
  az account show -o json
  az ad signed-in-user show -o json
  ```

- Follow-up:
  A guest identity can be valid for Terraform backend access. The important
  part is that the role is assigned to the identity actually used by `az login`.

## Recommended Scope For State Storage Role Assignment

- Date: 2026-03-16
- Area: Azure IAM scope
- Symptom:
  It was unclear whether the blob role should be assigned at subscription,
  resource group, or resource scope.
- Cause:
  Azure offers multiple valid scopes, and the portal makes it easy to wonder if
  a broader scope is required.
- Fix:
  For Terraform remote state in this setup, assigning
  `Storage Blob Data Contributor` at `This resource` on the bootstrap storage
  account is sufficient and keeps access narrowly scoped.
- Follow-up:
  Broader scopes can also work, but the storage-account resource scope is the
  clean default for this project.

## App Configuration Key Permission Propagation Error

- Date: 2026-03-16
- Area: Azure App Configuration / Terraform apply
- Symptom:
  `terraform apply` failed while creating
  `azurerm_app_configuration_key.settings[...]` with:
  `waiting for App Configuration Key "..."" read permission to be propagated: context canceled`.
- Cause:
  Terraform was creating App Configuration key-values immediately after creating
  the store, but the Terraform caller did not yet have `App Configuration Data Owner`
  on that store. Managing App Configuration key-values is a data-plane action,
  so management-plane permissions alone were not enough.
- Fix:
  Update the Terraform module so it grants the current caller
  `App Configuration Data Owner` on the App Configuration store before creating
  key-values, and make the key resources depend on that role assignment.
- Follow-up:
  After pulling this fix, rerun `terraform apply`. The same role assignment also
  helps the GitHub OIDC identity when the infrastructure workflow manages App
  Configuration keys.

## Linux Web App Health Check Argument Error

- Date: 2026-03-16
- Area: AzureRM provider schema / Terraform plan
- Symptom:
  Terraform failed on `azurerm_linux_web_app.this` with:
  `"site_config.0.health_check_path": all of
  site_config.0.health_check_eviction_time_in_min,site_config.0.health_check_path
  must be specified`.
- Cause:
  In the installed AzureRM provider version, setting `health_check_path`
  requires `health_check_eviction_time_in_min` to be set too.
- Fix:
  Set both values in the Linux Web App `site_config`, for example:

  ```hcl
  health_check_path                 = "/"
  health_check_eviction_time_in_min = 2
  ```

- Follow-up:
  If this error appears again after provider upgrades, check the AzureRM
  provider docs/schema for new required field pairings in `site_config`.

## App Service Plan Quota Error For Basic Workers

- Date: 2026-03-16
- Area: Azure App Service quota
- Symptom:
  Terraform failed while creating the App Service plan with an Azure response
  showing `401 Unauthorized` and:
  `Current Limit (Basic VMs): 0`.
- Cause:
  The subscription did not have available quota for Basic App Service workers.
  We first saw it while targeting `eastus`, and after changing regions the
  problem still looked like a broader subscription-level Basic App Service
  limitation rather than a simple Terraform or one-region syntax issue.
- Fix:
  Change the deployment region to a different Azure region such as `eastus2`
  and request App Service quota for `B1 VMs`.

  The successful path for this project was:

  - switch the default region to `eastus2`
  - request `B1 VMs = 1` quota in Azure for `East US 2`
  - wait for the quota request to complete
  - rerun `terraform plan` / `terraform apply`
- Follow-up:
  This is an Azure quota/capacity issue, not a Terraform syntax problem. If the
  new region shows the same Basic quota error, stop retrying applies and either
  request quota, use a different subscription, or switch the hosting target.

## App Service Says Image Was Not Found After Push

- Date: 2026-03-16
- Area: App Service container startup / ACR pull
- Symptom:
  App Service reported:
  `Failed to pull image ... Image pull failed because the image was not found`
  even after the `latest` tag had been pushed to ACR.
- Cause:
  The image reference on the Web App was correct, and the image was present in
  ACR, but App Service needed a little more time to refresh its pull state and
  for managed-identity-based ACR pull access to finish propagating.
- Fix:
  Verify the image tag exists in ACR, confirm the Web App container config is
  pointing at the expected registry/repository/tag, restart the Web App, and
  wait a few minutes.

  Helpful checks:

  ```powershell
  az acr repository show-tags --name <acr-name> --repository bonzo-assistant --output table
  az webapp config container show --name <web-app-name> --resource-group <resource-group>
  az webapp restart --name <web-app-name> --resource-group <resource-group>
  ```

- Follow-up:
  If the image tag exists and the config is correct, give App Service a little
  time before assuming the tag or image name is wrong. A short propagation delay
  can look like a missing-image problem.

## Streamlit Site Loads Forever Until WebSockets Are Enabled

- Date: 2026-03-16
- Area: App Service runtime configuration
- Symptom:
  The Web App was running and the container image was healthy, but the Streamlit
  page kept loading instead of finishing initialization.
- Cause:
  App Service had WebSockets disabled. Streamlit depends on WebSockets for the
  interactive UI to complete loading and stay responsive.
- Fix:
  Enable WebSockets on the Azure Web App and keep the Terraform config aligned.

  Helpful command:

  ```powershell
  az webapp config set --name <web-app-name> --resource-group <resource-group> --web-sockets-enabled true
  ```

- Follow-up:
  The Terraform module now sets `websockets_enabled = true` for the Linux Web
  App. If the site starts loading forever again, check the live Web App config
  before assuming the container is broken.

## GitHub OIDC Login Failed Because Federated Credential Was Missing

- Date: 2026-03-16
- Area: GitHub Actions / Azure OIDC
- Symptom:
  `azure/login` failed in GitHub Actions even though the client ID, tenant ID,
  and subscription ID were set in the GitHub environment.
- Cause:
  The Azure app registration existed, but it did not yet have a federated
  credential trusting the GitHub repository/environment subject.
- Fix:
  Add a federated credential to the app registration for:

  ```text
  repo:ratsalad21/bonzo-assistant:environment:dev
  ```

  with issuer:

  ```text
  https://token.actions.githubusercontent.com
  ```

  and audience:

  ```text
  api://AzureADTokenExchange
  ```

- Follow-up:
  If `azure/login` fails early, verify the app registration has the expected
  federated credential before debugging workflow YAML or secrets.

## GitHub Actions Built Old Dependencies Because Changes Were Only Local

- Date: 2026-03-16
- Area: GitHub Actions / source of truth
- Symptom:
  GitHub Actions failed on the Docker build with the old dependency error even
  though the package versions had already been fixed locally.
- Cause:
  The fixes existed only in the local workspace and had not yet been committed
  and pushed to GitHub. GitHub Actions builds the repository state on GitHub,
  not uncommitted local files.
- Fix:
  Commit and push the updated files, then rerun the workflow.
- Follow-up:
  Before using GitHub Actions to validate a fix, confirm the relevant files are
  actually committed and pushed.

## Local And GitHub Terraform Runs Fought Over "Current Caller" Access

- Date: 2026-03-16
- Area: Terraform identity design
- Symptom:
  GitHub `Deploy Infrastructure` could authenticate successfully but still
  failed while reading App Configuration keys, and Terraform planned to replace
  bootstrap access resources with the GitHub service principal object ID.
- Cause:
  The Terraform module originally granted Key Vault and App Configuration
  bootstrap permissions to `data.azurerm_client_config.current.object_id`.
  That meant local runs used the local user object ID, while GitHub runs used
  the GitHub service principal object ID. The two execution paths kept fighting
  over the same resources.
- Fix:
  Replace the "current caller" pattern with explicit variables:

  - `deployment_principal_object_id`
  - `local_operator_object_id`

  Then manage Key Vault/App Configuration bootstrap access from those explicit
  IDs instead of from whichever identity happens to run Terraform.
- Follow-up:
  For GitHub infrastructure runs, set `DEPLOYMENT_PRINCIPAL_OBJECT_ID` in the
  GitHub environment to the service principal object ID, not the application
  client ID.

## `RoleAssignmentExists` Happened During The Operator Identity Migration

- Date: 2026-03-16
- Area: Terraform identity migration / App Configuration RBAC
- Symptom:
  GitHub `Deploy Infrastructure` `apply` got through most of the migration and
  then failed with a `409 Conflict` / `RoleAssignmentExists` error while
  creating `operator_app_config_data_owner` for the GitHub principal.
- Cause:
  A manual `App Configuration Data Owner` role assignment for the GitHub
  service principal already existed on the App Configuration store, so
  Terraform could not create the same assignment itself.
- Fix:
  Remove the duplicate manual role assignment, then rerun `Deploy
  Infrastructure` with `apply` so Terraform can create and manage the role
  assignment in state.
- Follow-up:
  During the one-time migration from the old `current` resources to the new
  explicit operator resources, let Terraform own the final role assignments
  instead of keeping overlapping manual copies in place.

## `azure/webapps-deploy` Reported No Credentials After OIDC Login

- Date: 2026-03-16
- Area: GitHub Actions / App Service deployment
- Symptom:
  The `Deploy App` workflow reached the final deployment step and failed with:
  `No credentials found. Add an Azure login action before this action.`
- Cause:
  The workflow had already authenticated successfully with `azure/login`, but
  the custom-container deployment flow using `azure/webapps-deploy` still did
  not pick up usable credentials in this setup.
- Fix:
  Replace the final `azure/webapps-deploy` step with Azure CLI commands after
  the successful OIDC login:

  ```powershell
  az webapp config container set --name <web-app-name> --resource-group <resource-group> --docker-custom-image-name <image-ref>
  az webapp restart --name <web-app-name> --resource-group <resource-group>
  ```

  This uses the already-authenticated Azure CLI session from `azure/login`.
- Follow-up:
  For this repo, GitHub app deployment now expects the GitHub environment
  variable `AZURE_RESOURCE_GROUP` in addition to the existing web app and ACR
  values.
