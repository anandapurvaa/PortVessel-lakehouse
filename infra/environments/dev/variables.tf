variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "europe-west3"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "billing_account_id" {
  type        = string
  description = "Billing account ID used only for validation outside Terraform"
  default     = ""
}

locals {
  name_prefix = "portvessel-${var.environment}"
  raw_bucket  = "${var.project_id}-portvessel-${var.environment}-raw"
  proc_bucket = "${var.project_id}-portvessel-${var.environment}-processed"
}
