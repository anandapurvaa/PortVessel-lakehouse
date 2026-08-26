from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timezone

from google.cloud import bigquery, storage

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
BQ_LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")
PROCESSED_BUCKET = os.environ["GCS_PROCESSED_BUCKET"]
BQ_DATASET = os.environ.get("BQ_DATASET", "portvessel_dev_staging")
BQ_TABLE = os.environ.get("BQ_TABLE", "ais_pings")
AUDIT_DATASET = os.environ.get("AUDIT_DATASET", "portvessel_dev_staging")
AUDIT_TABLE = os.environ.get("AUDIT_TABLE", "ingestion_run_audit")
PIPELINE_NAME = os.environ.get("PIPELINE_NAME", "portvessel_ais_bq_loader")


def cursor_date(client: bigquery.Client) -> date:
    table_id = f"{PROJECT_ID}.{AUDIT_DATASET}.pipeline_cursor"
    query = f"""
        SELECT next_source_date
        FROM `{table_id}`
        WHERE pipeline_name = 'portvessel_noaa_daily_ingestion'
          AND status = 'ready'
        LIMIT 1
    """
    rows = list(client.query(query, location=BQ_LOCATION).result())
    if not rows:
        raise RuntimeError("No ready ingestion cursor found")
    return rows[0].next_source_date


def load_day(client: bigquery.Client, source_date: date) -> int:
    object_name = (
        f"processed/ais/year={source_date:%Y}/month={source_date:%m}/"
        f"day={source_date:%d}/ais_ping.parquet"
    )
    uri = f"gs://{PROCESSED_BUCKET}/{object_name}"
    table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
        autodetect=True,
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="observed_at_utc",
        ),
        clustering_fields=["mmsi"],
    )

    job = client.load_table_from_uri(
        uri,
        table_id,
        job_config=job_config,
        location=BQ_LOCATION,
    )
    job.result()
    return int(job.output_rows or 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-date")
    args = parser.parse_args()

    client = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
    source_date_value = args.source_date or os.environ.get("SOURCE_DATE")
    source_date = (
        date.fromisoformat(source_date_value)
        if source_date_value
        else cursor_date(client)
    )
    rows = load_day(client, source_date)
    print({
        "pipeline": PIPELINE_NAME,
        "source_date": source_date.isoformat(),
        "rows_loaded": rows,
        "target": f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}",
        "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
    })


if __name__ == "__main__":
    main()
