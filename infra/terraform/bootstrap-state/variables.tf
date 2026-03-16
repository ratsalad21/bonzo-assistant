variable "name_prefix" {
  description = "Short lowercase prefix used in Azure resource names."
  type        = string
  default     = "bonzo"
}

variable "location" {
  description = "Azure region for the Terraform state resources."
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Optional custom name for the Terraform state resource group."
  type        = string
  default     = ""
}

variable "storage_account_name" {
  description = "Optional custom storage account name for Terraform state."
  type        = string
  default     = ""
}

variable "container_name" {
  description = "Blob container name for Terraform state files."
  type        = string
  default     = "tfstate"
}

variable "storage_account_tier" {
  description = "Storage account tier for Terraform state."
  type        = string
  default     = "Standard"
}

variable "storage_account_replication_type" {
  description = "Replication type for the Terraform state storage account."
  type        = string
  default     = "LRS"
}
