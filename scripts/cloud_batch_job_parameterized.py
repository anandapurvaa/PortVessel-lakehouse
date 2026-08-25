import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
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

LINEAGE_COLUMNS = {
    "source_object",
    "source_sha256",
    "source_retrieved_at_utc",
    "loaded_at_utc",
    "ingestion_run_id",
}


def table_exists(client, table_id):
    try:
        client.get_table(table_id)
        return True
    except Exception:
        return False


def main():
    started_at = datetime.now(timezone.utc)
    source_uri = f"gs://{SOURCE_BUCKET}/{SOURCE_OBJECT}"
    final_table = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
    temp_table = (
        f"{PROJECT_ID}.{BQ_DATASET}._load_"
        f"{RUN_ID.lower()}"
    )

    storage_client = storage.Client(project=PROJECT_ID)
    blob = storage_client.bucket(SOURCE_BUCKET).blob(SOURCE_OBJECT)

    if not blob.exists(storage_client):
        raise FileNotFoundError(f"Missing source object: {source_uri}")

    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp_path = Path(temp.name)

    bq = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)

    try:
        blob.download_to_filename(temp_path)
        source_sha256 = hashlib.sha256(temp_path.read_bytes()).hexdigest()
        source_size_bytes = temp_path.stat().st_size
        retrieved_at = datetime.now(timezone.utc).isoformat()

        if table_exists(bq, final_table):
            duplicate_query = f"""
                SELECT COUNT(*) AS row_count
                FROM `{final_table}`
                WHERE source_object = @source_object
                  AND source_sha256 = @source_sha256
            """
            duplicate_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(
                        "source_object", "STRING", SOURCE_OBJECT
                    ),
                    bigquery.ScalarQueryParameter(
                        "source_sha256", "STRING", source_sha256
                    ),
                ],
                use_legacy_sql=False,
            )
            rows = list(
                bq.query(
                    duplicate_query,
                    job_config=duplicate_config,
                    location=BQ_LOCATION,
                ).result()
            )
            if rows and rows[0].row_count > 0:
                print(json.dumps({
                    "run_id": RUN_ID,
                    "status": "skipped_duplicate",
                    "source_date": SOURCE_DATE,
                    "source_uri": source_uri,
                    "source_sha256": source_sha256,
                    "target_table": final_table,
                }))
                return

        load_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True,
        )
        load_job = bq.load_table_from_uri(
            source_uri,
            temp_table,
            job_config=load_config,
            location=BQ_LOCATION,
        )
        load_job.result()

        temp_schema = bq.get_table(temp_table).schema
        source_columns = [field.name for field in temp_schema]
        BOOLEAN_COLUMNS = {
            "is_left_censored",
            "is_right_censored",
            "eligible_for_complete_metrics",
            "meets_minimum_ping_count",
            "meets_minimum_dwell_minutes",
            "eligible_for_persistent_metrics",
            "has_observed_anchorage",
        }

        data_columns = [
            name for name in source_columns
            if name not in LINEAGE_COLUMNS
        ]

        select_expressions = []

        for name in data_columns:
            if name in BOOLEAN_COLUMNS:
                select_expressions.append(
                    f"""
                    CASE
                        WHEN LOWER(TRIM(CAST(`{name}` AS STRING))) IN
                            ('true', '1', 't', 'yes', 'y')
                            THEN TRUE
                        WHEN LOWER(TRIM(CAST(`{name}` AS STRING))) IN
                            ('false', '0', 'f', 'no', 'n')
                            THEN FALSE
                        ELSE NULL
                    END AS `{name}`
                    """
                )
            else:
                select_expressions.append(f"`{name}`")

        select_columns = ",\n".join(select_expressions)

        metadata_sql = """
            @source_object AS source_object,
            @source_sha256 AS source_sha256,
            @retrieved_at AS source_retrieved_at_utc,
            @loaded_at AS loaded_at_utc,
            @run_id AS ingestion_run_id
        """

        parameters = [
            bigquery.ScalarQueryParameter(
                "source_object", "STRING", SOURCE_OBJECT
            ),
            bigquery.ScalarQueryParameter(
                "source_sha256", "STRING", source_sha256
            ),
            bigquery.ScalarQueryParameter(
                "retrieved_at", "STRING", retrieved_at
            ),
            bigquery.ScalarQueryParameter(
                "loaded_at", "TIMESTAMP", started_at
            ),
            bigquery.ScalarQueryParameter(
                "run_id", "STRING", RUN_ID
            ),
        ]

        if not table_exists(bq, final_table):
            create_query = f"""
                CREATE TABLE `{final_table}` AS
                SELECT
                    {select_columns},
                    {metadata_sql}
                FROM `{temp_table}`
                WHERE FALSE
            """
            create_config = bigquery.QueryJobConfig(
                query_parameters=parameters,
                use_legacy_sql=False,
            )
            bq.query(
                create_query,
                job_config=create_config,
                location=BQ_LOCATION,
            ).result()

        insert_query = f"""
            INSERT INTO `{final_table}`
            SELECT
                {select_columns},
                {metadata_sql}
            FROM `{temp_table}`
        """
        insert_config = bigquery.QueryJobConfig(
            query_parameters=parameters,
            use_legacy_sql=False,
        )
        insert_job = bq.query(
            insert_query,
            job_config=insert_config,
            location=BQ_LOCATION,
        )
        insert_job.result()

        bq.delete_table(temp_table, not_found_ok=True)

        print(json.dumps({
            "run_id": RUN_ID,
            "status": "loaded",
            "source_date": SOURCE_DATE,
            "source_uri": source_uri,
            "source_sha256": source_sha256,
            "source_size_bytes": source_size_bytes,
            "target_table": final_table,
            "load_job_id": load_job.job_id,
            "insert_job_id": insert_job.job_id,
        }))
    finally:
        temp_path.unlink(missing_ok=True)
        bq.delete_table(temp_table, not_found_ok=True)


if __name__ == "__main__":
    main()
