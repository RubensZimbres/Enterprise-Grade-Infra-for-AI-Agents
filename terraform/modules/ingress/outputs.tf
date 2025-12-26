output "load_balancer_ip" {
  description = "The public IP of the Load Balancer. Point your DNS A-record here."
  value       = google_compute_global_address.lb_ip.address
}