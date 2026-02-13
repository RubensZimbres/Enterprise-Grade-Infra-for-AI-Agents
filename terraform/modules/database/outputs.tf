output "instance_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "secret_id" {
  description = "The ID of the Secret Manager secret containing the DB password"
  value       = google_secret_manager_secret.db_pass_secret.secret_id
}
