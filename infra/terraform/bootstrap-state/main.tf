locals {
  compact_prefix = lower(replace(var.name_prefix, "-", ""))
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
  numeric = true
}

locals {
  resolved_resource_group_name = var.resource_group_name != "" ? var.resource_group_name : "${var.name_prefix}-tfstate-rg"
  resolved_storage_account_name = var.storage_account_name != "" ? lower(var.storage_account_name) : substr(
    "${local.compact_prefix}tfstate${random_string.suffix.result}",
    0,
    24,
  )
}

resource "azurerm_resource_group" "this" {
  name     = local.resolved_resource_group_name
  location = var.location
}

resource "azurerm_storage_account" "this" {
  name                            = local.resolved_storage_account_name
  resource_group_name             = azurerm_resource_group.this.name
  location                        = azurerm_resource_group.this.location
  account_tier                    = var.storage_account_tier
  account_replication_type        = var.storage_account_replication_type
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = true
  public_network_access_enabled   = true
  allow_nested_items_to_be_public = false
}

resource "azurerm_storage_container" "this" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}
