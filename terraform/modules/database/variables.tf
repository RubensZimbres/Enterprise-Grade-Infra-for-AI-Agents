variable "project_id" {}
variable "region" {}

variable "network_id" {
  description = "The VPC ID where AlloyDB will live (from network module)"
  type        = string
}
