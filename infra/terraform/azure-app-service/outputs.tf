output "resource_group_name" {
  description = "Resource group containing the app resources."
  value       = azurerm_resource_group.this.name
}

output "web_app_name" {
  description = "Azure App Service name."
  value       = azurerm_linux_web_app.this.name
}

output "web_app_url" {
  description = "Public HTTPS URL for the app."
  value       = "https://${azurerm_linux_web_app.this.default_hostname}"
}

output "acr_login_server" {
  description = "ACR login server to use when tagging and pushing the image."
  value       = azurerm_container_registry.acr.login_server
}

output "acr_name" {
  description = "Azure Container Registry name."
  value       = azurerm_container_registry.acr.name
}

output "docker_image_reference" {
  description = "Full container image reference App Service expects."
  value       = "${azurerm_container_registry.acr.login_server}/${var.container_repository}:${var.container_image_tag}"
}

output "app_configuration_endpoint" {
  description = "Endpoint the app uses to load non-secret settings."
  value       = azurerm_app_configuration.this.endpoint
}

output "key_vault_name" {
  description = "Key Vault name storing the OpenAI secret."
  value       = azurerm_key_vault.this.name
}
