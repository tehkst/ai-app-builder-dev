output "secret_ids" {
  description = "Created secret IDs."
  value       = { for key, secret in google_secret_manager_secret.secrets : key => secret.secret_id }
}

output "secret_names" {
  description = "Created secret resource names."
  value       = { for key, secret in google_secret_manager_secret.secrets : key => secret.name }
}
