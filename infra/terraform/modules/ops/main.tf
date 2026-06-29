resource "google_monitoring_notification_channel" "email" {
  count        = var.contact_email == null ? 0 : 1
  project      = var.project_id
  display_name = "AI Software Factory alerts"
  type         = "email"

  labels = {
    email_address = var.contact_email
  }
}

resource "google_logging_metric" "errors" {
  project = var.project_id
  name    = "${var.environment}_application_errors"
  filter  = "resource.type=\"cloud_run_revision\" AND severity>=ERROR"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

resource "google_monitoring_alert_policy" "errors" {
  project      = var.project_id
  display_name = "${var.environment} application errors"
  combiner     = "OR"

  conditions {
    display_name = "Error log entries"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.errors.name}\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.error_threshold

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [
    for channel in google_monitoring_notification_channel.email : channel.name
  ]
  enabled = true
}

resource "google_monitoring_dashboard" "platform" {
  project = var.project_id
  dashboard_json = jsonencode({
    displayName = "AI Software Factory ${var.environment}"
    mosaicLayout = {
      columns = 12
      tiles   = []
    }
  })
}
