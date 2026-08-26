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
  error_code STRING,
  error_message STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() NOT NULL
)
PARTITION BY DATE(started_at)
CLUSTER BY pipeline_name, status;

CREATE TABLE IF NOT EXISTS `cloudprojects-506123.portvessel_dev_staging.data_quality_results` (
  check_id STRING NOT NULL,
  run_id STRING NOT NULL,
  pipeline_name STRING NOT NULL,
  source_date DATE NOT NULL,
  check_name STRING NOT NULL,
  check_type STRING NOT NULL,
  status STRING NOT NULL,
  observed_value FLOAT64,
  expected_value FLOAT64,
  details STRING,
  checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() NOT NULL
)
PARTITION BY DATE(checked_at)
CLUSTER BY pipeline_name, source_date, status;

CREATE TABLE IF NOT EXISTS `cloudprojects-506123.portvessel_dev_staging.schema_registry` (
  dataset_name STRING NOT NULL,
  table_name STRING NOT NULL,
  schema_version STRING NOT NULL,
  schema_hash STRING NOT NULL,
  schema_json JSON NOT NULL,
  compatibility_mode STRING NOT NULL,
  is_active BOOL NOT NULL,
  registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() NOT NULL
)
PARTITION BY DATE(registered_at)
CLUSTER BY dataset_name, table_name, is_active;

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
  event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP() NOT NULL
)
PARTITION BY DATE(event_time)
CLUSTER BY pipeline_name, input_asset, output_asset;