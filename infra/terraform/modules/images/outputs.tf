output "repository_name" {
  description = "Repository resource name."
  value       = google_artifact_registry_repository.repository.name
}

output "repository_id" {
  description = "Repository ID."
  value       = google_artifact_registry_repository.repository.repository_id
}

output "repository_url" {
  description = "Docker repository URL prefix."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repository.repository_id}"
}
