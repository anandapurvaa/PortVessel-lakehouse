from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from google.cloud import bigquery

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")
DATASET = os.environ.get("METADATA_DATASET", "portvessel_dev_staging")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-date", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--pipeline-version", default=os.environ.get("PIPELINE_VERSION", "v1"))
    parser.add_argument("--input-rows", type=int, default=0)
    parser.add_argument("--output-rows", type=int, default=0)
    parser.add_argument("--quarantined-rows", type=int, default=0)
    parser.add_argument("--quality-check-count", type=int, default=0)
    parser.add_argument("--error-code")
    parser.add_argument("--error-message")
    args = parser.parse_args()

    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    query = f"""
    INSERT INTO `{PROJECT_ID}.{DATASET}.pipeline_runs`
    (run_id, pipeline_name, source_date, pipeline_version, status,
     started_at, completed_at, input_rows, output_rows, quarantined_rows,
     quality_check_count, error_code, error_message, created_at)
    VALUES
    (@run_id, 'portvessel_noaa_daily_ingestion', @source_date, @pipeline_version,
     @status, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), @input_rows,
     @output_rows, @quarantined_rows, @quality_check_count, @error_code,
     @error_message, CURRENT_TIMESTAMP())
    """
    config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("run_id", "STRING", args.run_id),
        bigquery.ScalarQueryParameter("source_date", "DATE", args.source_date),
        bigquery.ScalarQueryParameter("pipeline_version", "STRING", args.pipeline_version),
        bigquery.ScalarQueryParameter("status", "STRING", args.status),
        bigquery.ScalarQueryParameter("input_rows", "INT64", args.input_rows),
        bigquery.ScalarQueryParameter("output_rows", "INT64", args.output_rows),
        bigquery.ScalarQueryParameter("quarantined_rows", "INT64", args.quarantined_rows),
        bigquery.ScalarQueryParameter("quality_check_count", "INT64", args.quality_check_count),
        bigquery.ScalarQueryParameter("error_code", "STRING", args.error_code),
        bigquery.ScalarQueryParameter("error_message", "STRING", args.error_message),
    ])
    client.query(query, job_config=config, location=LOCATION).result()
    print({"status": "recorded", "run_id": args.run_id, "source_date": args.source_date})


if __name__ == "__main__":
    main()
