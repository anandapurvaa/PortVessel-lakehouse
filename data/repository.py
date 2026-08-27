"""BigQuery data access layer for the Port Vessel Dash application.

This module queries the production-style Gold marts directly:
- portvessel_dev_gold.agg_port_congestion_daily
- portvessel_dev_gold.fct_port_calls
- portvessel_dev_gold.fct_anchorage_dwell

Authentication uses Application Default Credentials. For local development:
    gcloud auth application-default login

For deployment, use a Cloud Run service account with at minimum:
- roles/bigquery.jobUser on the Google Cloud project
- roles/bigquery.dataViewer on portvessel_dev_gold
"""

from functools import lru_cache

import pandas as pd
from google.cloud import bigquery


PROJECT_ID = "cloudprojects-506123"
DATASET_ID = "portvessel_dev_gold"
PORT_ID = "USLAX"

DAILY_TABLE = f"{PROJECT_ID}.{DATASET_ID}.agg_port_congestion_daily"
PORT_CALLS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.fct_port_calls"
ANCHORAGE_TABLE = f"{PROJECT_ID}.{DATASET_ID}.fct_anchorage_dwell"


@lru_cache(maxsize=1)
def _bigquery_client():
    """Create and reuse the authenticated BigQuery client."""
    return bigquery.Client(project=PROJECT_ID)


def _query(sql: str, params: list[bigquery.ScalarQueryParameter] | None = None) -> pd.DataFrame:
    """Execute parameterized Standard SQL and return a pandas DataFrame."""
    job_config = bigquery.QueryJobConfig(
        query_parameters=params or [],
        use_legacy_sql=False,
    )
    return _bigquery_client().query(sql, job_config=job_config).result().to_dataframe()


def _minutes_to_hours(df: pd.DataFrame, minute_columns: list[str]) -> pd.DataFrame:
    """Add hour-based presentation columns while retaining raw minute fields."""
    for minute_column in minute_columns:
        if minute_column in df.columns:
            hour_column = minute_column.replace("_minutes", "_hours")
            df[hour_column] = pd.to_numeric(df[minute_column], errors="coerce") / 60.0
    return df


def get_daily_congestion() -> pd.DataFrame:
    """Return daily quality-aware congestion metrics for the Overview page."""
    sql = f"""
    SELECT
      metric_date,
      port_id,
      port_name,
      detected_port_calls,
      detected_vessels,
      complete_port_calls,
      observed_port_calls,
      partial_calls,
      left_censored_calls,
      right_censored_calls,
      both_censored_calls,
      invalid_calls,
      port_calls_with_observed_anchorage_wait,
      port_calls_with_observed_berth_proximity_dwell,
      median_port_duration_minutes,
      p90_port_duration_minutes,
      mean_port_duration_minutes,
      median_anchorage_wait_minutes,
      p90_anchorage_wait_minutes,
      mean_anchorage_wait_minutes,
      median_berth_proximity_dwell_minutes,
      p90_berth_proximity_dwell_minutes,
      mean_berth_proximity_dwell_minutes,
      ingestion_run_id,
      loaded_at_utc
    FROM `{DAILY_TABLE}`
    WHERE port_id = @port_id
    ORDER BY metric_date
    """

    df = _query(sql, [bigquery.ScalarQueryParameter("port_id", "STRING", PORT_ID)])
    df["metric_date"] = pd.to_datetime(df["metric_date"])

    df = _minutes_to_hours(
        df,
        [
            "median_port_duration_minutes",
            "p90_port_duration_minutes",
            "mean_port_duration_minutes",
            "median_anchorage_wait_minutes",
            "p90_anchorage_wait_minutes",
            "mean_anchorage_wait_minutes",
            "median_berth_proximity_dwell_minutes",
            "p90_berth_proximity_dwell_minutes",
            "mean_berth_proximity_dwell_minutes",
        ],
    )

    df["complete_port_call_coverage_rate"] = (
        pd.to_numeric(df["complete_port_calls"], errors="coerce")
        / pd.to_numeric(df["detected_port_calls"], errors="coerce")
    )

    return df


def get_port_calls() -> pd.DataFrame:
    """Return vessel-level port calls for the Port Calls explorer page."""
    sql = f"""
    SELECT
      port_call_id,
      CAST(mmsi AS STRING) AS mmsi,
      CAST(imo AS STRING) AS imo,
      vessel_name,
      port_id,
      port_name,
      arrival_observed_at_utc,
      departure_observed_at_utc,
      arrival_date,
      port_duration_minutes,
      anchorage_wait_minutes,
      berth_dwell_minutes,
      state_interval_count,
      ping_count,
      anchorage_interval_count,
      berth_interval_count,
      observed_duration_minutes,
      has_left_censored_interval,
      has_right_censored_interval,
      has_partial_interval,
      has_unobserved_anchorage_duration,
      has_unobserved_berth_duration,
      port_call_quality_status,
      latest_ingestion_run_id,
      loaded_at_utc
    FROM `{PORT_CALLS_TABLE}`
    WHERE port_id = @port_id
    ORDER BY arrival_observed_at_utc DESC
    """

    df = _query(sql, [bigquery.ScalarQueryParameter("port_id", "STRING", PORT_ID)])

    for column in [
        "arrival_observed_at_utc",
        "departure_observed_at_utc",
        "loaded_at_utc",
    ]:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], utc=True)

    df["arrival_date"] = pd.to_datetime(df["arrival_date"])

    return _minutes_to_hours(
        df,
        [
            "port_duration_minutes",
            "anchorage_wait_minutes",
            "berth_dwell_minutes",
            "observed_duration_minutes",
        ],
    )


def get_anchorage_dwells() -> pd.DataFrame:
    """Return anchorage intervals for the Anchorage page."""
    sql = f"""
    SELECT
      anchorage_dwell_id,
      CAST(mmsi AS STRING) AS mmsi,
      CAST(imo AS STRING) AS imo,
      vessel_name,
      port_id,
      port_name,
      zone_id,
      zone_name,
      anchorage_entered_at_utc,
      anchorage_exited_at_utc,
      entry_date,
      anchorage_dwell_minutes,
      ping_count,
      observed_duration_minutes,
      has_multiple_pings,
      is_duration_observed,
      is_left_censored,
      is_right_censored,
      duration_observability_status,
      anchorage_dwell_quality_status,
      latest_ingestion_run_id,
      loaded_at_utc
    FROM `{ANCHORAGE_TABLE}`
    WHERE port_id = @port_id
    ORDER BY anchorage_entered_at_utc DESC
    """

    df = _query(sql, [bigquery.ScalarQueryParameter("port_id", "STRING", PORT_ID)])

    for column in [
        "anchorage_entered_at_utc",
        "anchorage_exited_at_utc",
        "loaded_at_utc",
    ]:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], utc=True)

    df["entry_date"] = pd.to_datetime(df["entry_date"])

    return _minutes_to_hours(
        df,
        [
            "anchorage_dwell_minutes",
            "observed_duration_minutes",
        ],
    )


def get_anchorage_daily() -> pd.DataFrame:
    """Aggregate observed anchorage dwells for the anchorage trend chart."""
    sql = f"""
    SELECT
      entry_date,
      COUNT(*) AS observed_anchorage_dwells,
      APPROX_QUANTILES(anchorage_dwell_minutes, 100)[SAFE_OFFSET(50)]
        AS median_anchorage_dwell_minutes,
      APPROX_QUANTILES(anchorage_dwell_minutes, 100)[SAFE_OFFSET(90)]
        AS p90_anchorage_dwell_minutes,
      ROUND(AVG(anchorage_dwell_minutes), 1) AS mean_anchorage_dwell_minutes
    FROM `{ANCHORAGE_TABLE}`
    WHERE port_id = @port_id
      AND anchorage_dwell_quality_status = 'observed'
      AND anchorage_dwell_minutes IS NOT NULL
    GROUP BY entry_date
    ORDER BY entry_date
    """

    df = _query(sql, [bigquery.ScalarQueryParameter("port_id", "STRING", PORT_ID)])
    df["entry_date"] = pd.to_datetime(df["entry_date"])

    return _minutes_to_hours(
        df,
        [
            "median_anchorage_dwell_minutes",
            "p90_anchorage_dwell_minutes",
            "mean_anchorage_dwell_minutes",
        ],
    )
