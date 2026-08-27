variable "transform_image" {
  type        = string
  description = "Container image for the PortVessel dbt transformation job"
}

variable "transform_job_name" {
  type    = string
  default = "portvessel-dbt-transform-dev"
}

resource "google_service_account" "transform" {
  account_id   = "portvessel-transform-${var.environment}"
  display_name = "PortVessel dbt transformation job"
}

resource "google_project_iam_member" "transform_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.transform.email}"
}

resource "google_bigquery_dataset_iam_member" "transform_staging_viewer" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.transform.email}"
}

resource "google_bigquery_dataset_iam_member" "transform_dbt_seed_viewer" {
  dataset_id = "portvessel_${var.environment}"
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.transform.email}"
}

resource "google_bigquery_dataset_iam_member" "transform_silver_editor" {
  dataset_id = google_bigquery_dataset.silver.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.transform.email}"
}

resource "google_bigquery_dataset_iam_member" "transform_gold_editor" {
  dataset_id = google_bigquery_dataset.gold.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.transform.email}"
}

resource "google_cloud_run_v2_job" "transform" {
  name     = var.transform_job_name
  location = var.region
  project  = var.project_id

  template {
    template {
      service_account = google_service_account.transform.email
      max_retries     = 1
      timeout         = "3600s"

      containers {
        name  = "transform"
        image = var.transform_image

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "BQ_LOCATION"
          value = var.region
        }

        env {
          name  = "DBT_TARGET_DATASET"
          value = "portvessel_${var.environment}"
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job_iam_member" "workflow_transform_runner" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.transform.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.workflow.email}"
}

output "transform_job_name" {
  value = google_cloud_run_v2_job.transform.name
}
