output "resource_group_name" {
  description = "Resource group holding the Terraform state storage."
  value       = azurerm_resource_group.this.name
}

output "storage_account_name" {
  description = "Storage account name for the Terraform backend."
  value       = azurerm_storage_account.this.name
}

output "container_name" {
  description = "Blob container name for the Terraform backend."
  value       = azurerm_storage_container.this.name
}

output "backend_config_snippet" {
  description = "Copy these values into backend.hcl for the main workspace."
  value       = <<EOT
resource_group_name  = "${azurerm_resource_group.this.name}"
storage_account_name = "${azurerm_storage_account.this.name}"
container_name       = "${azurerm_storage_container.this.name}"
key                  = "azure-app-service/dev.tfstate"
use_azuread_auth     = true
EOT
}
