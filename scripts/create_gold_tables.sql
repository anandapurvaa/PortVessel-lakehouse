CREATE TABLE IF NOT EXISTS
  `cloudprojects-506123.portvessel_dev_gold.fct_anchorage_dwell`
(
  anchorage_dwell_id STRING,
  mmsi INT64,
  anchorage_object_id STRING,
  anchorage_name STRING,
  entry_observed_at_utc TIMESTAMP,
  exit_observed_at_utc TIMESTAMP,
  observed_dwell_minutes INT64,
  ping_count INT64,
  max_gap_minutes FLOAT64,
  is_left_censored BOOL,
  is_right_censored BOOL,
  episode_quality STRING,
  dwell_quality STRING,
  eligible_for_complete_metrics BOOL,
  meets_minimum_ping_count BOOL,
  meets_minimum_dwell_minutes BOOL,
  eligible_for_persistent_metrics BOOL,
  persistence_quality STRING,
  first_source_file STRING,
  last_source_file STRING,
  source_window_start TIMESTAMP,
  source_window_end TIMESTAMP,
  source_object STRING,
  source_sha256 STRING,
  source_retrieved_at_utc STRING,
  loaded_at_utc TIMESTAMP,
  ingestion_run_id STRING
)
PARTITION BY DATE(entry_observed_at_utc)
CLUSTER BY anchorage_object_id, mmsi;

CREATE TABLE IF NOT EXISTS
  `cloudprojects-506123.portvessel_dev_gold.fct_port_call`
(
  port_call_id STRING,
  mmsi INT64,
  port_id STRING,
  port_name STRING,
  arrival_observed_at_utc TIMESTAMP,
  departure_observed_at_utc TIMESTAMP,
  observed_port_duration_minutes INT64,
  ping_count INT64,
  anchorage_features_observed INT64,
  anchorage_entry_observed_at_utc TIMESTAMP,
  anchorage_last_observed_at_utc TIMESTAMP,
  has_observed_anchorage BOOL,
  port_call_quality STRING,
  visit_gap_threshold_minutes INT64,
  first_source_file STRING,
  last_source_file STRING,
  source_object STRING,
  source_sha256 STRING,
  source_retrieved_at_utc STRING,
  loaded_at_utc TIMESTAMP,
  ingestion_run_id STRING
)
PARTITION BY DATE(arrival_observed_at_utc)
CLUSTER BY port_id, mmsi;

CREATE TABLE IF NOT EXISTS
  `cloudprojects-506123.portvessel_dev_gold.agg_port_congestion_daily`
(
  metric_date DATE,
  port_id STRING,
  port_name STRING,
  observed_port_calls INT64,
  observed_vessels INT64,
  port_calls_with_anchorage INT64,
  median_port_duration_minutes FLOAT64,
  p90_port_duration_minutes FLOAT64,
  mean_port_duration_minutes FLOAT64,
  observed_with_anchorage_calls INT64,
  partial_calls INT64,
  source_object STRING,
  source_sha256 STRING,
  source_retrieved_at_utc STRING,
  loaded_at_utc TIMESTAMP,
  ingestion_run_id STRING
)
PARTITION BY metric_date
CLUSTER BY port_id;

CREATE TABLE IF NOT EXISTS
  `cloudprojects-506123.portvessel_dev_gold.vessel_operational_risk_flags`
(
  mmsi INT64,
  port_call_count INT64,
  port_calls_with_anchorage INT64,
  partial_port_calls INT64,
  persistent_anchorage_episode_count INT64,
  max_port_duration_minutes INT64,
  mean_port_duration_minutes FLOAT64,
  max_persistent_anchorage_dwell_minutes INT64,
  mean_persistent_anchorage_dwell_minutes FLOAT64,
  max_observation_gap_minutes FLOAT64,
  operational_flag STRING,
  source_object STRING,
  source_sha256 STRING,
  source_retrieved_at_utc STRING,
  loaded_at_utc TIMESTAMP,
  ingestion_run_id STRING
)
CLUSTER BY mmsi, operational_flag;
