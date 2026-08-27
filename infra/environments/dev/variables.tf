variable "project_id" {
  type        = string
  description = "Existing GCP project ID"
}

variable "region" {
  type        = string
  description = "GCP region for regional resources and BigQuery datasets"
}

variable "environment" {
  type        = string
  description = "Deployment environment, for example dev or prod"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,15}$", var.environment))
    error_message = "environment must be 2-16 characters, starting with a letter, using lowercase letters, digits, or hyphens."
  }
}

variable "workflow_name" {
  type        = string
  description = "Name of the daily orchestration workflow"
  default     = "portvessel-daily-orchestration-dev"
}
