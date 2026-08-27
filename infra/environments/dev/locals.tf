locals {
  raw_bucket  = "${var.project_id}-portvessel-${var.environment}-raw"
  proc_bucket = "${var.project_id}-portvessel-${var.environment}-processed"
}
