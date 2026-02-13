variable "project_id" {}
variable "region" {}
variable "vpc_name" {}
variable "subnet_name" {}
variable "db_host" {
  description = "The private IP address of the Database instance"
  type        = string
}

variable "db_secret_id" {
  description = "The ID of the secret containing the DB password"
  type        = string
}

variable "redis_host" {
  description = "The host of the Redis instance"
  type        = string
}
<<<<<<< HEAD

variable "stripe_secret_key_id" {
  description = "The ID of the secret containing the Stripe Secret Key"
  type        = string
}

variable "redis_password_id" {
  description = "The ID of the secret containing the Redis Password"
  type        = string
}
=======
>>>>>>> 703160704334d46f22c789973015b880a18296f2
