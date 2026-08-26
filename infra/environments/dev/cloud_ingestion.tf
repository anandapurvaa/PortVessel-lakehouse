variable "ingestion_image" {
  type = string
}

variable "ingestion_job_name" {
  type    = string
  default = "portvessel-ingestion-dev"
}

resource "google_service_account" "ingestion" {
  account_id   = "portvessel-ingestion-${var.environment}"
  display_name = "PortVessel ingestion job"
}

resource "google_storage_bucket_iam_member" "ingestion_raw_admin" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_storage_bucket_iam_member" "ingestion_processed_admin" {
  bucket = google_storage_bucket.processed.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_project_iam_member" "ingestion_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_bigquery_dataset_iam_member" "ingestion_staging_editor" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_cloud_run_v2_job" "ingestion" {
  name     = var.ingestion_job_name
  location = var.region

  template {
    template {
      service_account = google_service_account.ingestion.email
      max_retries     = 1
      timeout         = "3600s"

      containers {
        name  = "ingestion"
        image = var.ingestion_image

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "GCS_RAW_BUCKET"
          value = google_storage_bucket.raw.name
        }
        env {
          name  = "GCS_PROCESSED_BUCKET"
          value = google_storage_bucket.processed.name
        }
        env {
          name  = "RAW_PREFIX"
          value = "raw/noaa_ais"
        }
        env {
          name  = "PROCESSED_PREFIX"
          value = "processed/ais"
        }
        env {
          name  = "QUARANTINE_PREFIX"
          value = "quarantine/ais"
        }
        env {
          name  = "MANIFEST_PREFIX"
          value = "manifests/ais"
        }
        env {
          name  = "BQ_LOCATION"
          value = var.region
        }
        env {
          name  = "CURSOR_DATASET"
          value = google_bigquery_dataset.staging.dataset_id
        }
        env {
          name  = "CURSOR_TABLE"
          value = "pipeline_cursor"
        }
        env {
          name  = "PIPELINE_START_DATE"
          value = "2024-01-01"
        }
      }
    }
  }
}

output "ingestion_job_name" {
  value = google_cloud_run_v2_job.ingestion.name
}

output "ingestion_service_account" {
  value = google_service_account.ingestion.email
}
