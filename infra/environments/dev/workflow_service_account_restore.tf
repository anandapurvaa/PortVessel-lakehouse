resource "google_service_account" "workflow" {
  account_id   = "portvessel-workflow-${var.environment}"
  display_name = "PortVessel daily orchestration workflow"
}

resource "google_project_iam_member" "workflow_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.workflow.email}"
}

resource "google_project_iam_member" "workflow_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.workflow.email}"
}

resource "google_bigquery_dataset_iam_member" "workflow_cursor_editor" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.workflow.email}"
}
