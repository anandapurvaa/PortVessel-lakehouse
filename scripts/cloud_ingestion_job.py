from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import polars as pl
from google.cloud import storage

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
RAW_BUCKET = os.environ["GCS_RAW_BUCKET"]
PROCESSED_BUCKET = os.environ["GCS_PROCESSED_BUCKET"]
RAW_PREFIX = os.environ.get("RAW_PREFIX", "raw/noaa_ais")
PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processed/ais")
QUARANTINE_PREFIX = os.environ.get("QUARANTINE_PREFIX", "quarantine/ais")
MANIFEST_PREFIX = os.environ.get("MANIFEST_PREFIX", "manifests/ais")
NOAA_BASE_URL = os.environ.get("NOAA_AIS_BASE_URL", "https://noaaocm.blob.core.windows.net/ais/csv2/csv{year}")

SOURCE_COLUMNS = ["mmsi", "base_date_time", "longitude", "latitude", "sog", "cog", "heading", "vessel_name", "imo", "call_sign", "vessel_type", "status", "length", "width", "draft", "cargo", "transceiver"]
OUTPUT_COLUMNS = ["mmsi", "imo", "call_sign", "vessel_name", "observed_at_utc", "latitude", "longitude", "sog_knots", "cog_degrees", "heading_degrees", "nav_status", "vessel_type", "draft_m", "length_m", "width_m", "cargo_type", "transceiver_class", "source_file", "source_uri", "source_sha256", "ingestion_run_id", "ingested_at_utc", "record_hash", "quality_flag", "is_quarantined"]


def source_url(day: date) -> str:
    return f"{NOAA_BASE_URL.format(year=day.year)}/ais-{day:%Y-%m-%d}.csv.zst"


def upload(client: storage.Client, bucket_name: str, path: Path, object_name: str, content_type: str) -> None:
    client.bucket(bucket_name).blob(object_name).upload_from_filename(str(path), content_type=content_type)


def download(url: str, destination: Path) -> dict:
    partial = destination.with_name(destination.name + ".part")
    for attempt in range(1, 5):
        try:
            digest = hashlib.sha256()
            total = 0
            with urlopen(Request(url, headers={"User-Agent": "PortVessel/1.0"}), timeout=300) as response, partial.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    total += len(chunk)
            partial.replace(destination)
            return {"url": url, "bytes": total, "sha256": digest.hexdigest(), "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            partial.unlink(missing_ok=True)
            if attempt == 4:
                raise RuntimeError(f"Download failed: {url}") from exc
            time.sleep(2**attempt)
    raise RuntimeError(f"Download failed: {url}")


def normalize(csv_path: Path, url: str, sha256: str, run_id: str) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    header = pl.read_csv(csv_path, n_rows=0).columns
    lookup = {c.lower().strip(): c for c in header}
    missing = [c for c in SOURCE_COLUMNS if c not in lookup]
    if missing:
        raise ValueError(f"Missing source columns: {missing}")
    selected = [lookup[c] for c in SOURCE_COLUMNS]
    frame = (
        pl.scan_csv(csv_path, has_header=True, infer_schema=False, encoding="utf8-lossy", truncate_ragged_lines=True, ignore_errors=True)
        .select(selected)
        .rename(dict(zip(selected, SOURCE_COLUMNS)))
        .with_columns([
            pl.col("mmsi").str.strip_chars().alias("mmsi_raw"),
            pl.col("base_date_time").str.strip_chars().str.strptime(pl.Datetime(time_zone="UTC"), strict=False).alias("observed_at_utc"),
            pl.col("longitude").cast(pl.Float64, strict=False), pl.col("latitude").cast(pl.Float64, strict=False),
            pl.col("sog").cast(pl.Float64, strict=False).alias("sog_knots"), pl.col("cog").cast(pl.Float64, strict=False).alias("cog_degrees"), pl.col("heading").cast(pl.Float64, strict=False).alias("heading_degrees"), pl.col("status").cast(pl.Int64, strict=False).alias("nav_status"), pl.col("vessel_type").cast(pl.Int64, strict=False), pl.col("draft").cast(pl.Float64, strict=False).alias("draft_m"), pl.col("length").cast(pl.Float64, strict=False).alias("length_m"), pl.col("width").cast(pl.Float64, strict=False).alias("width_m"), pl.col("cargo").cast(pl.Int64, strict=False).alias("cargo_type"),
        ])
        .with_columns([
            pl.col("mmsi_raw").cast(pl.Int64, strict=False).alias("mmsi"), pl.col("imo").str.strip_chars(), pl.col("call_sign").str.strip_chars(), pl.col("vessel_name").str.strip_chars(), pl.col("transceiver").str.strip_chars().alias("transceiver_class"), pl.lit(str(csv_path)).alias("source_file"), pl.lit(url).alias("source_uri"), pl.lit(sha256).alias("source_sha256"), pl.lit(run_id).alias("ingestion_run_id"), pl.lit(datetime.now(timezone.utc)).cast(pl.Datetime(time_zone="UTC")).alias("ingested_at_utc"),
        ])
        .with_columns([
            (pl.col("mmsi").is_null() | pl.col("observed_at_utc").is_null() | pl.col("latitude").is_null() | pl.col("longitude").is_null() | ~pl.col("latitude").is_between(-90, 90) | ~pl.col("longitude").is_between(-180, 180)).alias("is_quarantined"),
            pl.when(pl.col("mmsi").is_null()).then(pl.lit("missing_mmsi")).when(pl.col("observed_at_utc").is_null()).then(pl.lit("invalid_timestamp")).when(pl.col("latitude").is_null() | pl.col("longitude").is_null()).then(pl.lit("invalid_coordinate")).when(~pl.col("latitude").is_between(-90, 90) | ~pl.col("longitude").is_between(-180, 180)).then(pl.lit("coordinate_out_of_range")).otherwise(pl.lit(None, dtype=pl.String)).alias("quality_flag"),
        ])
        .with_columns(pl.struct(["mmsi_raw", "observed_at_utc", "latitude", "longitude"]).map_elements(lambda v: hashlib.sha256(json.dumps(v, sort_keys=True, default=str).encode()).hexdigest(), return_dtype=pl.String).alias("record_hash"))
        .collect(engine="streaming")
    )
    quarantined = frame.filter(pl.col("is_quarantined"))
    valid = frame.filter(~pl.col("is_quarantined")).unique(subset=["record_hash"])
    return valid.select(OUTPUT_COLUMNS), quarantined.select(OUTPUT_COLUMNS), {"rows_read": frame.height, "valid_rows": valid.height, "quarantined_rows": quarantined.height, "source_uri": url, "source_sha256": sha256}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-date")
    parser.add_argument("--run-id")
    args = parser.parse_args()

    source_date_value = args.source_date or os.environ.get("SOURCE_DATE")
    if not source_date_value:
        raise RuntimeError("SOURCE_DATE is required")

    day = date.fromisoformat(source_date_value)
    run_id = (
        args.run_id
        or os.environ.get("RUN_ID")
        or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    url = source_url(day)
    storage_client = storage.Client(project=PROJECT_ID)

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        archive = work / f"ais-{day:%Y-%m-%d}.csv.zst"
        csv_path = work / f"ais-{day:%Y-%m-%d}.csv"
        metadata = download(url, archive)
        raw_name = f"{RAW_PREFIX}/source_date={day}/ais-{day:%Y-%m-%d}.csv.zst"
        upload(storage_client, RAW_BUCKET, archive, raw_name, "application/zstd")
        result = subprocess.run(["zstd", "-d", "-f", str(archive), "-o", str(csv_path)], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        valid, quarantine, report = normalize(csv_path, url, metadata["sha256"], run_id)
        processed_name = f"{PROCESSED_PREFIX}/year={day:%Y}/month={day:%m}/day={day:%d}/ais_ping.parquet"
        quarantine_name = f"{QUARANTINE_PREFIX}/year={day:%Y}/month={day:%m}/day={day:%d}/ais_quarantine.parquet"
        valid_path = work / "ais_ping.parquet"; quarantine_path = work / "ais_quarantine.parquet"
        valid.write_parquet(valid_path, compression="zstd"); quarantine.write_parquet(quarantine_path, compression="zstd")
        upload(storage_client, PROCESSED_BUCKET, valid_path, processed_name, "application/octet-stream")
        upload(storage_client, PROCESSED_BUCKET, quarantine_path, quarantine_name, "application/octet-stream")
        report.update({"run_id": run_id, "source_date": args.source_date, "raw_object": f"gs://{RAW_BUCKET}/{raw_name}", "processed_object": f"gs://{PROCESSED_BUCKET}/{processed_name}", "quarantine_object": f"gs://{PROCESSED_BUCKET}/{quarantine_name}", "source_size_bytes": metadata["bytes"], "retrieved_at_utc": metadata["retrieved_at_utc"]})
        manifest_name = f"{MANIFEST_PREFIX}/source_date={day}/run_id={run_id}.json"
        storage_client.bucket(PROCESSED_BUCKET).blob(manifest_name).upload_from_string(json.dumps(report, indent=2), content_type="application/json")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
