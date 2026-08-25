import hashlib
import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from google.cloud import bigquery, storage

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
SOURCE_BUCKET = os.environ["GCS_SOURCE_BUCKET"]
SOURCE_OBJECT = os.environ["SOURCE_OBJECT"]
BQ_DATASET = os.environ["BQ_DATASET"]
BQ_TABLE = os.environ["BQ_TABLE"]
SOURCE_DATE = os.environ.get("SOURCE_DATE", "")
RUN_ID = os.environ.get(
    "RUN_ID",
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
)
BQ_LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")
AUDIT_DATASET = os.environ.get("AUDIT_DATASET", "portvessel_dev_staging")
AUDIT_TABLE = os.environ.get("AUDIT_TABLE", "ingestion_run_audit")

LINEAGE_COLUMNS = {
    "source_object",
    "source_sha256",
    "source_retrieved_at_utc",
    "loaded_at_utc",
    "ingestion_run_id",
}

BOOLEAN_COLUMNS = {
    "is_left_censored",
    "is_right_censored",
    "eligible_for_complete_metrics",
    "meets_minimum_ping_count",
    "meets_minimum_dwell_minutes",
    "eligible_for_persistent_metrics",
    "has_observed_anchorage",
}

AUDIT_SCHEMA = [
    bigquery.SchemaField("run_id", "STRING"),
    bigquery.SchemaField("source_date", "DATE"),
    bigquery.SchemaField("source_uri", "STRING"),
    bigquery.SchemaField("source_object", "STRING"),
    bigquery.SchemaField("source_sha256", "STRING"),
    bigquery.SchemaField("source_size_bytes", "INT64"),
    bigquery.SchemaField("target_dataset", "STRING"),
    bigquery.SchemaField("target_table", "STRING"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("started_at_utc", "TIMESTAMP"),
    bigquery.SchemaField("completed_at_utc", "TIMESTAMP"),
    bigquery.SchemaField("row_count", "INT64"),
    bigquery.SchemaField("error_message", "STRING"),
]


def get_table(client, table_id):
    try:
        return client.get_table(table_id)
    except Exception:
        return None


def ensure_audit_table(client, table_id):
    table = get_table(client, table_id)

    if table is None:
        table = bigquery.Table(table_id, schema=AUDIT_SCHEMA)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="started_at_utc",
        )
        table.clustering_fields = ["target_table", "status"]
        client.create_table(table)
        return

    existing_by_name = {field.name: field for field in table.schema}
    missing_fields = [
        field for field in AUDIT_SCHEMA
        if field.name not in existing_by_name
    ]

    if not missing_fields:
        return

    for field in missing_fields:
        if field.mode == "REQUIRED":
            raise RuntimeError(
                f"Cannot add required audit column {field.name} "
                "to an existing BigQuery table."
            )

    table.schema = list(table.schema) + missing_fields
    client.update_table(table, ["schema"])


def write_audit(
    bq,
    audit_table,
    source_uri,
    source_sha256,
    source_size_bytes,
    status,
    started_at,
    completed_at,
    row_count,
    error_message=None,
):
    query = f"""
        INSERT INTO `{audit_table}`
        (
          run_id, source_date, source_uri, source_object, source_sha256,
          source_size_bytes, target_dataset, target_table, status,
          started_at_utc, completed_at_utc, row_count, error_message
        )
        VALUES
        (
          @run_id, @source_date, @source_uri, @source_object, @source_sha256,
          @source_size_bytes, @target_dataset, @target_table, @status,
          @started_at, @completed_at, @row_count, @error_message
        )
    """

    config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("run_id", "STRING", RUN_ID),
            bigquery.ScalarQueryParameter(
                "source_date",
                "DATE",
                date.fromisoformat(SOURCE_DATE) if SOURCE_DATE else None,
            ),
            bigquery.ScalarQueryParameter("source_uri", "STRING", source_uri),
            bigquery.ScalarQueryParameter("source_object", "STRING", SOURCE_OBJECT),
            bigquery.ScalarQueryParameter("source_sha256", "STRING", source_sha256),
            bigquery.ScalarQueryParameter("source_size_bytes", "INT64", source_size_bytes),
            bigquery.ScalarQueryParameter("target_dataset", "STRING", BQ_DATASET),
            bigquery.ScalarQueryParameter("target_table", "STRING", BQ_TABLE),
            bigquery.ScalarQueryParameter("status", "STRING", status),
            bigquery.ScalarQueryParameter("started_at", "TIMESTAMP", started_at),
            bigquery.ScalarQueryParameter("completed_at", "TIMESTAMP", completed_at),
            bigquery.ScalarQueryParameter("row_count", "INT64", row_count),
            bigquery.ScalarQueryParameter("error_message", "STRING", error_message),
        ],
        use_legacy_sql=False,
    )
    bq.query(query, job_config=config, location=BQ_LOCATION).result()


def main():
    started_at = datetime.now(timezone.utc)
    source_uri = f"gs://{SOURCE_BUCKET}/{SOURCE_OBJECT}"
    final_table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
    audit_table_id = f"{PROJECT_ID}.{AUDIT_DATASET}.{AUDIT_TABLE}"
    temp_table_id = f"{PROJECT_ID}.{BQ_DATASET}._load_{RUN_ID.lower()}"

    bq = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
    storage_client = storage.Client(project=PROJECT_ID)
    blob = storage_client.bucket(SOURCE_BUCKET).blob(SOURCE_OBJECT)

    ensure_audit_table(bq, audit_table_id)

    source_sha256 = "unknown"
    source_size_bytes = None
    temp_path = None

    try:
        if not blob.exists(storage_client):
            raise FileNotFoundError(f"Missing source object: {source_uri}")

        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = Path(temp.name)

        blob.download_to_filename(temp_path)
        source_sha256 = hashlib.sha256(temp_path.read_bytes()).hexdigest()
        source_size_bytes = temp_path.stat().st_size
        retrieved_at = datetime.now(timezone.utc).isoformat()

        if get_table(bq, final_table_id) is not None:
            duplicate_query = f"""
                SELECT COUNT(*) AS row_count
                FROM `{final_table_id}`
                WHERE source_object = @source_object
                  AND source_sha256 = @source_sha256
            """
            duplicate_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("source_object", "STRING", SOURCE_OBJECT),
                    bigquery.ScalarQueryParameter("source_sha256", "STRING", source_sha256),
                ],
                use_legacy_sql=False,
            )
            duplicate_rows = list(
                bq.query(
                    duplicate_query,
                    job_config=duplicate_config,
                    location=BQ_LOCATION,
                ).result()
            )
            if duplicate_rows and duplicate_rows[0].row_count > 0:
                completed_at = datetime.now(timezone.utc)
                write_audit(
                    bq, audit_table_id, source_uri, source_sha256,
                    source_size_bytes, "skipped_duplicate", started_at,
                    completed_at, duplicate_rows[0].row_count,
                )
                print(json.dumps({
                    "run_id": RUN_ID,
                    "status": "skipped_duplicate",
                    "source_date": SOURCE_DATE,
                    "source_uri": source_uri,
                    "source_sha256": source_sha256,
                    "target_table": final_table_id,
                }))
                return

        load_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True,
        )
        load_job = bq.load_table_from_uri(
            source_uri,
            temp_table_id,
            job_config=load_config,
            location=BQ_LOCATION,
        )
        load_job.result()

        temp_schema = bq.get_table(temp_table_id).schema
        source_columns = [field.name for field in temp_schema]
        data_columns = [
            name for name in source_columns
            if name not in LINEAGE_COLUMNS
        ]

        expressions = []
        for name in data_columns:
            if name in BOOLEAN_COLUMNS:
                expressions.append(f"""
                    CASE
                      WHEN LOWER(TRIM(CAST(`{name}` AS STRING)))
                        IN ('true', '1', 't', 'yes', 'y') THEN TRUE
                      WHEN LOWER(TRIM(CAST(`{name}` AS STRING)))
                        IN ('false', '0', 'f', 'no', 'n') THEN FALSE
                      ELSE NULL
                    END AS `{name}`
                """)
            else:
                expressions.append(f"`{name}`")

        select_columns = ",\n".join(expressions)
        metadata_sql = """
            @source_object AS source_object,
            @source_sha256 AS source_sha256,
            @retrieved_at AS source_retrieved_at_utc,
            @loaded_at AS loaded_at_utc,
            @run_id AS ingestion_run_id
        """
        parameters = [
            bigquery.ScalarQueryParameter("source_object", "STRING", SOURCE_OBJECT),
            bigquery.ScalarQueryParameter("source_sha256", "STRING", source_sha256),
            bigquery.ScalarQueryParameter("retrieved_at", "STRING", retrieved_at),
            bigquery.ScalarQueryParameter("loaded_at", "TIMESTAMP", started_at),
            bigquery.ScalarQueryParameter("run_id", "STRING", RUN_ID),
        ]

        if get_table(bq, final_table_id) is None:
            create_query = f"""
                CREATE TABLE `{final_table_id}` AS
                SELECT {select_columns}, {metadata_sql}
                FROM `{temp_table_id}`
                WHERE FALSE
            """
            bq.query(
                create_query,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=parameters,
                    use_legacy_sql=False,
                ),
                location=BQ_LOCATION,
            ).result()

        insert_query = f"""
            INSERT INTO `{final_table_id}`
            SELECT {select_columns}, {metadata_sql}
            FROM `{temp_table_id}`
        """
        bq.query(
            insert_query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=parameters,
                use_legacy_sql=False,
            ),
            location=BQ_LOCATION,
        ).result()

        count_query = f"""
            SELECT COUNT(*) AS row_count
            FROM `{final_table_id}`
            WHERE source_object = @source_object
              AND source_sha256 = @source_sha256
        """
        count_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("source_object", "STRING", SOURCE_OBJECT),
                bigquery.ScalarQueryParameter("source_sha256", "STRING", source_sha256),
            ],
            use_legacy_sql=False,
        )
        count_rows = list(
            bq.query(count_query, job_config=count_config, location=BQ_LOCATION).result()
        )
        row_count = count_rows[0].row_count
        completed_at = datetime.now(timezone.utc)
        write_audit(
            bq, audit_table_id, source_uri, source_sha256,
            source_size_bytes, "loaded", started_at,
            completed_at, row_count,
        )

        print(json.dumps({
            "run_id": RUN_ID,
            "status": "loaded",
            "source_date": SOURCE_DATE,
            "source_uri": source_uri,
            "source_sha256": source_sha256,
            "target_table": final_table_id,
            "row_count": row_count,
        }))
    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        try:
            write_audit(
                bq, audit_table_id, source_uri, source_sha256,
                source_size_bytes, "failed", started_at,
                completed_at, None, str(exc),
            )
        except Exception as audit_exc:
            print(f"Audit write failed: {audit_exc}")
        raise
    finally:
        bq.delete_table(temp_table_id, not_found_ok=True)
        if temp_path:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
