output "deploy_service_account_email" {
  description = "Deployment service account email."
  value       = google_service_account.deploy.email
}

output "workload_identity_provider" {
  description = "Workload Identity Provider resource name."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "workload_identity_pool" {
  description = "Workload Identity Pool resource name."
  value       = google_iam_workload_identity_pool.github.name
}
