variable "loader_image" {
  type = string
}

variable "loader_job_name" {
  type    = string
  default = "portvessel-bq-loader-dev"
}

resource "google_service_account" "loader" {
  account_id   = "portvessel-loader-${var.environment}"
  display_name = "PortVessel BigQuery loader"
}

resource "google_project_iam_member" "loader_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.loader.email}"
}

resource "google_bigquery_dataset_iam_member" "loader_staging_viewer" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.loader.email}"
}

resource "google_bigquery_dataset_iam_member" "loader_staging_editor" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.loader.email}"
}

resource "google_storage_bucket_iam_member" "loader_processed_viewer" {
  bucket = google_storage_bucket.processed.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.loader.email}"
}

resource "google_cloud_run_v2_job" "loader" {
  name     = var.loader_job_name
  location = var.region

  template {
    template {
      service_account = google_service_account.loader.email
      max_retries     = 1
      timeout         = "3600s"

      containers {
        name  = "loader"
        image = var.loader_image

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "GCS_PROCESSED_BUCKET"
          value = google_storage_bucket.processed.name
        }
        env {
          name  = "BQ_DATASET"
          value = google_bigquery_dataset.staging.dataset_id
        }
        env {
          name  = "BQ_TABLE"
          value = "ais_pings"
        }
        env {
          name  = "AUDIT_DATASET"
          value = google_bigquery_dataset.staging.dataset_id
        }
        env {
          name  = "AUDIT_TABLE"
          value = "ingestion_run_audit"
        }
        env {
          name  = "BQ_LOCATION"
          value = var.region
        }
      }
    }
  }
}

output "loader_job_name" {
  value = google_cloud_run_v2_job.loader.name
}
