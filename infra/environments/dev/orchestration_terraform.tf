variable "workflow_name" {
  type    = string
  default = "portvessel-daily-orchestration-dev"
}

resource "google_service_account" "workflow" {
  account_id   = "portvessel-workflow-${var.environment}"
  display_name = "PortVessel daily orchestration workflow"
}

resource "google_project_iam_member" "workflow_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.workflow.email}"
}

resource "google_bigquery_dataset_iam_member" "workflow_cursor_editor" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.workflow.email}"
}

resource "google_project_iam_member" "workflow_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.workflow.email}"
}

resource "google_workflows_workflow" "daily" {
  name            = var.workflow_name
  region          = var.region
  service_account = google_service_account.workflow.id
  source_contents = file("${path.module}/../../../workflow/orchestration_workflow.yaml")
}

resource "google_cloud_scheduler_job" "workflow_trigger" {
  name      = "portvessel-workflow-daily-${var.environment}"
  region    = var.region
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
