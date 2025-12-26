variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "domain_name" {
  description = "Domain name for the frontend (e.g., ai.example.com)"
  type        = string
  default     = ""
}

variable "iap_client_id" {
  description = "OAuth2 Client ID for IAP"
  type        = string
}

variable "iap_client_secret" {
  description = "OAuth2 Client Secret for IAP"
  type        = string
  sensitive   = true
}