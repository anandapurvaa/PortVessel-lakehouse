from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timezone
from pathlib import Path

from google.cloud import bigquery

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")
DATASET = os.environ.get("QUALITY_DATASET", "portvessel_dev_staging")
SQL_PATH = os.environ.get("QUALITY_SQL_PATH", "/app/sql/data_quality_checks.sql")
EXPECTED_CHECKS = 6

def write_pipeline_run(
    client: bigquery.Client,
    run_id: str,
    source_date_value: str,
    status: str,
    quality_check_count: int,
) -> None:
    query = f"""
    INSERT INTO `{PROJECT_ID}.{DATASET}.pipeline_runs`
    (
      run_id,
      pipeline_name,
      source_date,
      pipeline_version,
      status,
      started_at,
      completed_at,
      input_rows,
      output_rows,
      quarantined_rows,
      quality_check_count,
      created_at
    )
    VALUES
    (
      @run_id,
      'portvessel_noaa_daily_ingestion',
      @source_date,
      'quality-v1',
      @status,
      CURRENT_TIMESTAMP(),
      CURRENT_TIMESTAMP(),
      NULL,
      NULL,
      NULL,
      @quality_check_count,
      CURRENT_TIMESTAMP()
    )
    """

    config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
            bigquery.ScalarQueryParameter("source_date", "DATE", source_date_value),
            bigquery.ScalarQueryParameter("status", "STRING", status),
            bigquery.ScalarQueryParameter(
                "quality_check_count", "INT64", quality_check_count
            ),
        ]
    )

    client.query(query, job_config=config, location=LOCATION).result()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-date")
    parser.add_argument("--run-id")
    args = parser.parse_args()

    source_date_value = args.source_date or os.environ.get("SOURCE_DATE")
    if not source_date_value:
        raise RuntimeError("SOURCE_DATE is required")

    run_id = args.run_id or os.environ.get("RUN_ID")
    if not run_id:
        run_id = datetime.now(timezone.utc).strftime("quality-%Y%m%dT%H%M%S%fZ")

    sql = Path(SQL_PATH).read_text(encoding="utf-8")
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    params = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "run_date", "DATE", date.fromisoformat(source_date_value)
            ),
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
        ]
    )
    client.query(sql, job_config=params, location=LOCATION).result()

    check_rows = list(client.query(
        f"""
        SELECT check_name, status, observed_value, details
        FROM `{PROJECT_ID}.{DATASET}.data_quality_results`
        WHERE run_id = @run_id
        ORDER BY check_name
        """,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("run_id", "STRING", run_id)]
        ),
        location=LOCATION,
    ).result())

    if len(check_rows) != EXPECTED_CHECKS:
        raise RuntimeError(
            f"Expected {EXPECTED_CHECKS} quality checks for {run_id}; "
            f"found {len(check_rows)}"
        )

    failed = [row for row in check_rows if row.status == "FAIL"]
    if failed:
        raise RuntimeError(f"Data quality checks failed for {run_id}: {failed}")

    write_pipeline_run(
    client=client,
    run_id=run_id,
    source_date_value=source_date_value,
    status="SUCCEEDED",
    quality_check_count=len(check_rows),
)
    print({
        "status": "PASS",
        "run_id": run_id,
        "source_date": source_date_value,
        "checks": len(check_rows),
    })


if __name__ == "__main__":
    main()
