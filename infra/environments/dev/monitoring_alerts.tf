resource "google_monitoring_notification_channel" "email" {
  display_name = "PortVessel operations email"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_alert_policy" "workflow_failures" {
  display_name = "PortVessel workflow failures"
  combiner     = "OR"

  conditions {
    display_name = "Workflow execution failed"

    condition_matched_log {
      filter = join(" ", [
        "resource.type=\"workflows.googleapis.com/Workflow\"",
        "resource.labels.workflow_id=\"portvessel-daily-orchestration-dev\"",
        "severity>=ERROR",
      ])
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]

  alert_strategy {
    notification_rate_limit {
      period = "300s"
    }
  }

  documentation {
    content   = "A PortVessel workflow execution failed. Inspect the workflow execution, Cloud Run Job logs, and pipeline cursor before retrying."
    mime_type = "text/markdown"
  }

  user_labels = {
    project     = "portvessel"
    environment = var.environment
    severity    = "critical"
  }
}

resource "google_monitoring_alert_policy" "quality_failures" {
  display_name = "PortVessel data quality failures"
  combiner     = "OR"

  conditions {
    display_name = "Quality Job failed"

    condition_matched_log {
      filter = join(" ", [
        "resource.type=\"cloud_run_job\"",
        "resource.labels.job_name=\"portvessel-quality-dev\"",
        "severity>=ERROR",
      ])
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]

  alert_strategy {
    notification_rate_limit {
      period = "300s"
    }
  }

  documentation {
    content   = "The PortVessel quality stage logged an error. Cursor advancement should be blocked; inspect the quality Job execution and data_quality_results."
    mime_type = "text/markdown"
  }

  user_labels = {
    project     = "portvessel"
    environment = var.environment
    severity    = "warning"
  }
}
