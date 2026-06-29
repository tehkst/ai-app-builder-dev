output "error_metric_name" {
  description = "Error log metric name."
  value       = google_logging_metric.errors.name
}

output "alert_policy_name" {
  description = "Alert policy name."
  value       = google_monitoring_alert_policy.errors.name
}

output "dashboard_id" {
  description = "Dashboard ID."
  value       = google_monitoring_dashboard.platform.id
}
