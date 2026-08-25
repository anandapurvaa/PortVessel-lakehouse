DECLARE failures INT64 DEFAULT 0;

SET failures = failures + (
  SELECT COUNT(*)
  FROM `cloudprojects-506123.portvessel_dev_gold.fct_anchorage_dwell`
  WHERE mmsi IS NULL
     OR entry_observed_at_utc IS NULL
     OR exit_observed_at_utc IS NULL
);

SET failures = failures + (
  SELECT COUNT(*)
  FROM `cloudprojects-506123.portvessel_dev_gold.fct_port_call`
  WHERE mmsi IS NULL
     OR arrival_observed_at_utc IS NULL
);

SET failures = failures + (
  SELECT COUNT(*)
  FROM `cloudprojects-506123.portvessel_dev_gold.agg_port_congestion_daily`
  WHERE metric_date IS NULL
     OR port_id IS NULL
);

SET failures = failures + (
  SELECT COUNT(*)
  FROM `cloudprojects-506123.portvessel_dev_gold.vessel_operational_risk_flags`
  WHERE mmsi IS NULL
);

SELECT
  failures,
  CASE
    WHEN failures = 0 THEN 'PASS'
    ELSE 'FAIL'
  END AS status;

ASSERT failures = 0 AS 'Gold-table validation failed';