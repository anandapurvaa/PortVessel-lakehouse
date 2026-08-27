resource "google_workflows_workflow" "daily" {
  name            = var.workflow_name
  region          = var.region
  project         = var.project_id
  service_account = google_service_account.workflow.id
  source_contents = file("${path.root}/../../../workflow/orchestration_workflow.yaml")
}

resource "google_cloud_scheduler_job" "workflow_trigger" {
  name      = "portvessel-workflow-daily-${var.environment}"
  region    = var.region
  project   = var.project_id
  schedule  = "0 2 * * *"
  time_zone = "Europe/Berlin"

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/workflows/${var.workflow_name}/executions"

    headers = {
      "Content-Type" = "application/json"
    }

    body = base64encode(jsonencode({
      argument = jsonencode({
        project        = var.project_id
        region         = var.region
        ingestion_job  = google_cloud_run_v2_job.ingestion.name
        loader_job     = google_cloud_run_v2_job.loader.name
        transform_job  = google_cloud_run_v2_job.transform.name
        quality_job    = google_cloud_run_v2_job.quality.name
        cursor_dataset = google_bigquery_dataset.staging.dataset_id
        cursor_table   = "pipeline_cursor"
        pipeline_name  = "portvessel_noaa_daily_ingestion"
      })
    }))

    oauth_token {
      service_account_email = google_service_account.workflow.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }
}
