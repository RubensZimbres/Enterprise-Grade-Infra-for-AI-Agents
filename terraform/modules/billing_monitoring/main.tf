# --- 1. Billing Budget ---
resource "google_billing_budget" "budget" {
  billing_account = var.billing_account
  display_name    = "Monthly Budget - AI Platform"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "100" # Example: 100 USD
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }
}

# --- 2. Cloud Trace is enabled by default for most projects,
# but we ensure the APIs are enabled in the root module.

# --- 3. Monitoring: Anomaly Trigger (Logging based) ---
resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Notification Channel"
  type         = "email"
  labels = {
    email_address = var.notification_email
  }
}

resource "google_monitoring_alert_policy" "anomaly_alert" {
  display_name = "AI Platform - Anomaly Detection"
  combiner     = "OR"
  conditions {
    display_name = "High Error Rate"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/error_count\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]
}

# Log Metric to count errors
resource "google_logging_metric" "error_count" {
  name   = "user/error_count"
  filter = "resource.type=\"cloud_run_revision\" AND severity>=ERROR"
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}
