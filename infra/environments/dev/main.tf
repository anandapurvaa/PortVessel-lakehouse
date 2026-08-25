terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "raw" {
  name                        = local.raw_bucket
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    project     = "portvessel"
    environment = var.environment
    layer       = "raw"
  }
}

resource "google_storage_bucket" "processed" {
  name                        = local.proc_bucket
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    project     = "portvessel"
    environment = var.environment
    layer       = "processed"
  }
}

resource "google_bigquery_dataset" "staging" {
  dataset_id                 = "portvessel_${var.environment}_staging"
  location                   = var.region
  delete_contents_on_destroy = false

  labels = {
    project     = "portvessel"
    environment = var.environment
    layer       = "staging"
  }
}

resource "google_bigquery_dataset" "silver" {
  dataset_id                 = "portvessel_${var.environment}_silver"
  location                   = var.region
  delete_contents_on_destroy = false

  labels = {
    project     = "portvessel"
    environment = var.environment
    layer       = "silver"
  }
}

resource "google_bigquery_dataset" "gold" {
  dataset_id                 = "portvessel_${var.environment}_gold"
  location                   = var.region
  delete_contents_on_destroy = false

  labels = {
    project     = "portvessel"
    environment = var.environment
    layer       = "gold"
  }
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "portvessel"
  description   = "PortVessel container images"
  format        = "DOCKER"
}

resource "google_service_account" "batch" {
  account_id   = "portvessel-batch-${var.environment}"
  display_name = "PortVessel batch processor"
}

resource "google_project_iam_member" "batch_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_project_iam_member" "batch_bq_job" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_bigquery_dataset_iam_member" "batch_staging_editor" {
  dataset_id = google_bigquery_dataset.staging.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_bigquery_dataset_iam_member" "batch_silver_editor" {
  dataset_id = google_bigquery_dataset.silver.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_bigquery_dataset_iam_member" "batch_gold_editor" {
  dataset_id = google_bigquery_dataset.gold.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.batch.email}"
}

output "raw_bucket" {
  value = google_storage_bucket.raw.name
}

output "processed_bucket" {
  value = google_storage_bucket.processed.name
}

output "batch_service_account" {
  value = google_service_account.batch.email
}
