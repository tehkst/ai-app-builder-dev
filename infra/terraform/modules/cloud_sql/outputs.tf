output "instance_name" {
  description = "Cloud SQL instance name."
  value       = google_sql_database_instance.instance.name
}

output "connection_name" {
  description = "Cloud SQL connection name."
  value       = google_sql_database_instance.instance.connection_name
}

output "database_name" {
  description = "Application database name."
  value       = google_sql_database.database.name
}
