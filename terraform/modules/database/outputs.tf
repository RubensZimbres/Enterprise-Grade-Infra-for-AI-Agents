output "cluster_id" {
  value = google_alloydb_cluster.default.id
}

output "instance_ip" {
  description = "The private IP address of the AlloyDB instance"
  value       = google_alloydb_instance.primary.ip_address
}

output "secret_id" {
  description = "The ID of the Secret Manager secret containing the DB password"
  value       = google_secret_manager_secret.db_pass_secret.secret_id
}