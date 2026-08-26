variable "quality_job_name" {
  type    = string
  default = "portvessel-quality-dev"
}

resource "google_cloud_run_v2_job" "quality" {
  name     = var.quality_job_name
  location = var.region

  template {
    template {
      service_account = google_service_account.workflow.email
      max_retries     = 1
      timeout         = "1800s"

      containers {
        name  = "quality"
        image = var.quality_image

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "BQ_LOCATION"
          value = var.region
        }
        env {
          name  = "QUALITY_DATASET"
          value = google_bigquery_dataset.staging.dataset_id
        }
      }
    }
  }
}

resource "google_project_iam_member" "workflow_quality_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.workflow.email}"
}

resource "google_bigquery_dataset_iam_member" "workflow_quality_editor" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.workflow.email}"
}

output "quality_job_name" {
  value = google_cloud_run_v2_job.quality.name
}
