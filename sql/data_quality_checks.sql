DECLARE run_date DATE DEFAULT @run_date;
DECLARE current_run_id STRING DEFAULT @run_id;
DECLARE pipeline STRING DEFAULT 'portvessel_noaa_daily_ingestion';

CREATE TEMP TABLE metrics AS
SELECT
  COUNT(*) AS total_rows,
  COUNTIF(is_quarantined = FALSE OR is_quarantined IS NULL) AS valid_rows,
  COUNTIF(mmsi IS NULL) AS null_mmsi,
  COUNTIF(observed_at_utc IS NULL) AS null_timestamp,
  COUNTIF(latitude IS NULL OR longitude IS NULL) AS null_coordinates,
  COUNTIF(
    latitude IS NOT NULL
    AND longitude IS NOT NULL
    AND (latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180)
  ) AS invalid_coordinates
FROM `cloudprojects-506123.portvessel_dev_staging.ais_pings`
WHERE DATE(observed_at_utc) = run_date;

CREATE TEMP TABLE checks AS
SELECT check_name, check_type, status, observed_value, expected_value, details
FROM metrics,
UNNEST([
  STRUCT('row_count' AS check_name, 'volume' AS check_type, IF(total_rows > 0, 'PASS', 'FAIL') AS status, CAST(total_rows AS FLOAT64) AS observed_value, 1.0 AS expected_value, 'At least one row expected' AS details),
  STRUCT('valid_row_count', 'volume', IF(valid_rows > 0, 'PASS', 'FAIL'), CAST(valid_rows AS FLOAT64), 1.0, 'At least one valid row expected'),
  STRUCT('null_mmsi', 'validity', IF(null_mmsi = 0, 'PASS', 'WARN'), CAST(null_mmsi AS FLOAT64), 0.0, 'Null MMSI count'),
  STRUCT('null_timestamp', 'validity', IF(null_timestamp = 0, 'PASS', 'FAIL'), CAST(null_timestamp AS FLOAT64), 0.0, 'Null timestamp count'),
  STRUCT('null_coordinates', 'validity', IF(null_coordinates = 0, 'PASS', 'WARN'), CAST(null_coordinates AS FLOAT64), 0.0, 'Null coordinate count'),
  STRUCT('invalid_coordinates', 'validity', IF(invalid_coordinates = 0, 'PASS', 'FAIL'), CAST(invalid_coordinates AS FLOAT64), 0.0, 'Out-of-range coordinate count')
]);

MERGE `cloudprojects-506123.portvessel_dev_staging.data_quality_results` AS target
USING (
  SELECT
    current_run_id AS run_id,
    pipeline AS pipeline_name,
    run_date AS source_date,
    check_name,
    check_type,
    status,
    observed_value,
    expected_value,
    details
  FROM checks
) AS source
ON target.run_id = source.run_id
AND target.check_name = source.check_name
WHEN MATCHED THEN UPDATE SET
  pipeline_name = source.pipeline_name,
  source_date = source.source_date,
  check_type = source.check_type,
  status = source.status,
  observed_value = source.observed_value,
  expected_value = source.expected_value,
  details = source.details,
  checked_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (
  check_id,
  run_id,
  pipeline_name,
  source_date,
  check_name,
  check_type,
  status,
  observed_value,
  expected_value,
  details,
  checked_at
) VALUES (
  GENERATE_UUID(),
  source.run_id,
  source.pipeline_name,
  source.source_date,
  source.check_name,
  source.check_type,
  source.status,
  source.observed_value,
  source.expected_value,
  source.details,
  CURRENT_TIMESTAMP()
);

ASSERT (SELECT COUNT(*) FROM checks WHERE status = 'FAIL') = 0 AS 'Data quality checks failed';
