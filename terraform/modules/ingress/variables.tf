variable "project_id" {}
variable "region" {}
variable "frontend_service_name" {}
variable "domain_name" {}
variable "iap_client_id" {
  description = "OAuth2 Client ID for IAP"
  type        = string
}
variable "iap_client_secret" {
  description = "OAuth2 Client Secret for IAP"
  type        = string
  sensitive   = true
}