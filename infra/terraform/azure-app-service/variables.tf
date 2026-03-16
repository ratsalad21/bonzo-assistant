variable "default_environment" {
  description = "Environment name to use when the Terraform workspace is still `default`."
  type        = string
  default     = "dev"
}

variable "name_prefix" {
  description = "Short lowercase prefix used in Azure resource names."
  type        = string
  default     = "bonzo"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "eastus2"
}

variable "app_service_plan_sku_name" {
  description = "SKU for the Linux App Service plan."
  type        = string
  default     = "B1"
}

variable "acr_sku" {
  description = "SKU for the Azure Container Registry."
  type        = string
  default     = "Basic"
}

variable "app_configuration_sku" {
  description = "SKU for Azure App Configuration."
  type        = string
  default     = "standard"

  validation {
    condition = contains(
      ["free", "developer", "standard", "premium"],
      lower(var.app_configuration_sku)
    )
    error_message = "app_configuration_sku must be one of: free, developer, standard, premium."
  }
}

variable "container_repository" {
  description = "Container repository name inside ACR."
  type        = string
  default     = "bonzo-assistant"
}

variable "container_image_tag" {
  description = "Container tag App Service should pull."
  type        = string
  default     = "latest"
}

variable "mock_mode" {
  description = "Whether the hosted app should run in mock mode."
  type        = bool
  default     = true
}

variable "openai_api_key" {
  description = "Optional OpenAI API key. Leave blank when staying in mock mode."
  type        = string
  default     = ""
  sensitive   = true

  validation {
    condition     = var.mock_mode || trimspace(var.openai_api_key) != ""
    error_message = "Set openai_api_key when mock_mode is false."
  }
}

variable "openai_model" {
  description = "Chat model stored in App Configuration."
  type        = string
  default     = "gpt-4.1-mini"
}

variable "embedding_model" {
  description = "Embedding model stored in App Configuration."
  type        = string
  default     = "text-embedding-3-small"
}

variable "openai_base_url" {
  description = "Optional alternate OpenAI-compatible endpoint."
  type        = string
  default     = ""
}

variable "app_model_context_window" {
  description = "Context-window budget stored in App Configuration."
  type        = number
  default     = 128000
}

variable "app_configuration_key_prefix" {
  description = "Prefix used for App Configuration keys."
  type        = string
  default     = "bonzo:"
}

variable "deployment_principal_object_id" {
  description = "Optional object ID for the GitHub/Azure deployment principal that should manage App Configuration and Key Vault bootstrap access."
  type        = string
  default     = ""
}

variable "local_operator_object_id" {
  description = "Optional object ID for a local user or admin principal that should keep App Configuration and Key Vault bootstrap access."
  type        = string
  default     = ""
}
