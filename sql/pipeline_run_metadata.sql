CREATE TABLE IF NOT EXISTS `cloudprojects-506123.portvessel_dev_staging.pipeline_runs` (
  run_id STRING NOT NULL,
  pipeline_name STRING NOT NULL,
  source_date DATE NOT NULL,
  pipeline_version STRING NOT NULL,
  status STRING NOT NULL,
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  input_rows INT64,
  output_rows INT64,
  quarantined_rows INT64,
  quality_check_count INT64,
  error_code STRING,
  error_message STRING,
  created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(started_at)
CLUSTER BY pipeline_name, status, source_date;

CREATE TABLE IF NOT EXISTS `cloudprojects-506123.portvessel_dev_staging.lineage_events` (
  event_id STRING NOT NULL,
  run_id STRING NOT NULL,
  pipeline_name STRING NOT NULL,
  source_system STRING NOT NULL,
  source_uri STRING,
  source_sha256 STRING,
  input_asset STRING NOT NULL,
  output_asset STRING NOT NULL,
  transformation_version STRING NOT NULL,
  event_time TIMESTAMP NOT NULL
)
PARTITION BY DATE(event_time)
CLUSTER BY pipeline_name, input_asset, output_asset;
