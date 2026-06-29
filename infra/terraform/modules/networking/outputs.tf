output "network_id" {
  description = "VPC network ID."
  value       = google_compute_network.network.id
}

output "network_name" {
  description = "VPC network name."
  value       = google_compute_network.network.name
}

output "subnet_id" {
  description = "Subnet ID."
  value       = google_compute_subnetwork.subnet.id
}

output "serverless_connector_id" {
  description = "Serverless connector ID."
  value       = google_vpc_access_connector.serverless.id
}

output "private_service_connection" {
  description = "Private services connection ID."
  value       = google_service_networking_connection.private_services.id
}
