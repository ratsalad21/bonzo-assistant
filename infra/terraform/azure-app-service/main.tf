data "azurerm_client_config" "current" {}

locals {
  environment         = terraform.workspace == "default" ? var.default_environment : terraform.workspace
  compact_prefix      = lower(replace(var.name_prefix, "-", ""))
  compact_environment = lower(replace(local.environment, "-", ""))
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
  numeric = true
}

locals {
  name_core              = "${var.name_prefix}-${local.environment}-${random_string.suffix.result}"
  resource_group_name    = "${local.name_core}-rg"
  service_plan_name      = "${local.name_core}-plan"
  web_app_name           = "${local.name_core}-app"
  acr_name               = substr("${local.compact_prefix}${local.compact_environment}${random_string.suffix.result}acr", 0, 50)
  key_vault_name         = substr("${local.compact_prefix}${local.compact_environment}${random_string.suffix.result}kv", 0, 24)
  app_configuration_name = substr("${local.compact_prefix}${local.compact_environment}${random_string.suffix.result}appcs", 0, 50)
  app_configuration_settings = merge(
    {
      OPENAI_MODEL             = var.openai_model
      EMBEDDING_MODEL          = var.embedding_model
      MOCK_MODE                = tostring(var.mock_mode)
      APP_MODEL_CONTEXT_WINDOW = tostring(var.app_model_context_window)
    },
    var.openai_base_url != "" ? { OPENAI_BASE_URL = var.openai_base_url } : {}
  )
  app_service_app_settings = merge(
    {
      WEBSITES_PORT                       = "8501"
      WEBSITES_ENABLE_APP_SERVICE_STORAGE = "true"
      APP_CONFIGURATION_ENDPOINT          = azurerm_app_configuration.this.endpoint
      APP_CONFIGURATION_LABEL             = local.environment
      APP_CONFIGURATION_PREFIX            = var.app_configuration_key_prefix
      DOCS_DIR                            = "/home/site/data/docs"
      CHAT_HISTORY_DIR                    = "/home/site/data/chat_history"
      CHROMA_DB_PATH                      = "/home/site/data/chroma_db"
    },
    length(azurerm_key_vault_secret.openai_api_key) > 0 ? {
      OPENAI_API_KEY = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_api_key[0].versionless_id})"
    } : {}
  )
}

resource "azurerm_resource_group" "this" {
  name     = local.resource_group_name
  location = var.location
}

resource "azurerm_container_registry" "acr" {
  name                = local.acr_name
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = var.acr_sku
  admin_enabled       = false
}

resource "azurerm_service_plan" "this" {
  name                = local.service_plan_name
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  os_type             = "Linux"
  sku_name            = var.app_service_plan_sku_name
}

resource "azurerm_key_vault" "this" {
  name                       = local.key_vault_name
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
}

resource "azurerm_key_vault_access_policy" "current" {
  key_vault_id = azurerm_key_vault.this.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Delete",
    "Get",
    "List",
    "Set",
  ]
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  count        = trimspace(var.openai_api_key) != "" ? 1 : 0
  name         = "openai-api-key"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.this.id

  depends_on = [azurerm_key_vault_access_policy.current]
}

resource "azurerm_app_configuration" "this" {
  name                = local.app_configuration_name
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = lower(var.app_configuration_sku)
}

resource "azurerm_role_assignment" "current_app_config_data_owner" {
  scope                = azurerm_app_configuration.this.id
  role_definition_name = "App Configuration Data Owner"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_app_configuration_key" "settings" {
  for_each               = local.app_configuration_settings
  configuration_store_id = azurerm_app_configuration.this.id
  key                    = "${var.app_configuration_key_prefix}${each.key}"
  label                  = local.environment
  value                  = each.value

  depends_on = [azurerm_role_assignment.current_app_config_data_owner]
}

resource "azurerm_linux_web_app" "this" {
  name                = local.web_app_name
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  service_plan_id     = azurerm_service_plan.this.id
  https_only          = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                               = true
    health_check_path                       = "/"
    health_check_eviction_time_in_min       = 2
    container_registry_use_managed_identity = true
    websockets_enabled                      = true

    application_stack {
      docker_image_name   = "${var.container_repository}:${var.container_image_tag}"
      docker_registry_url = "https://${azurerm_container_registry.acr.login_server}"
    }
  }

  app_settings = local.app_service_app_settings

  lifecycle {
    # GitHub Actions can advance the running image tag independently of Terraform.
    # Ignoring just the image name keeps app CD from being reverted by a later
    # infrastructure apply while still letting Terraform manage the rest.
    ignore_changes = [site_config[0].application_stack[0].docker_image_name]
  }
}

resource "azurerm_key_vault_access_policy" "app_service" {
  key_vault_id = azurerm_key_vault.this.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_web_app.this.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_web_app.this.identity[0].principal_id
}

resource "azurerm_role_assignment" "app_config_reader" {
  scope                = azurerm_app_configuration.this.id
  role_definition_name = "App Configuration Data Reader"
  principal_id         = azurerm_linux_web_app.this.identity[0].principal_id
}
