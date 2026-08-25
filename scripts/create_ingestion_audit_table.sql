CREATE TABLE IF NOT EXISTS
  `cloudprojects-506123.portvessel_dev_staging.ingestion_run_audit`
(
  run_id STRING NOT NULL,
  source_date DATE,
  source_uri STRING NOT NULL,
  source_object STRING NOT NULL,
  source_sha256 STRING NOT NULL,
  source_size_bytes INT64,
  target_dataset STRING NOT NULL,
  target_table STRING NOT NULL,
  status STRING NOT NULL,
  started_at_utc TIMESTAMP NOT NULL,
  completed_at_utc TIMESTAMP,
  row_count INT64,
  error_message STRING
)
PARTITION BY DATE(started_at_utc)
CLUSTER BY target_table, status;