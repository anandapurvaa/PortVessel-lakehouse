from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import polars as pl

SOURCE_DATE = "2024-12-28"
INPUT = Path(f"data/extracted/{SOURCE_DATE}/AIS_{SOURCE_DATE.replace('-', '_')}.csv")
OUTPUT_DIR = Path("data/processed/ais/year=2024/month=12/day=28")
QUARANTINE_DIR = Path("data/quarantine/ais/year=2024/month=12/day=28")
REPORT_PATH = Path("reports/ais_2024_12_28_normalization.json")
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
INGESTED_AT = datetime.now(timezone.utc)

if not INPUT.exists():
    raise FileNotFoundError(INPUT)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

expected_columns = [
    "MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG", "Heading",
    "VesselName", "IMO", "CallSign", "VesselType", "Status", "Length",
    "Width", "Draft", "Cargo", "TransceiverClass",
]

lf = pl.scan_csv(
    INPUT,
    has_header=True,
    infer_schema=False,
    encoding="utf8-lossy",
    truncate_ragged_lines=True,
    ignore_errors=True,
    quote_char='"',
)

canonical = (
    lf.select(expected_columns)
    .with_columns(
        pl.col("MMSI").str.strip_chars().alias("mmsi_raw"),
        pl.col("BaseDateTime").str.strip_chars().str.strptime(
            pl.Datetime(time_zone="UTC"), "%Y-%m-%dT%H:%M:%S", strict=False
        ).alias("observed_at_utc"),
        pl.col("LAT").cast(pl.Float64, strict=False).alias("latitude"),
        pl.col("LON").cast(pl.Float64, strict=False).alias("longitude"),
        pl.col("SOG").cast(pl.Float64, strict=False).alias("sog_knots"),
        pl.col("COG").cast(pl.Float64, strict=False).alias("cog_degrees"),
        pl.col("Heading").cast(pl.Float64, strict=False).alias("heading_degrees"),
        pl.col("VesselType").cast(pl.Int64, strict=False).alias("vessel_type"),
        pl.col("Status").cast(pl.Int64, strict=False).alias("nav_status"),
        pl.col("Length").cast(pl.Float64, strict=False).alias("length_m"),
        pl.col("Width").cast(pl.Float64, strict=False).alias("width_m"),
        pl.col("Draft").cast(pl.Float64, strict=False).alias("draft_m"),
        pl.col("Cargo").cast(pl.Int64, strict=False).alias("cargo_type"),
    )
    .with_columns(
        pl.col("mmsi_raw").cast(pl.Int64, strict=False).alias("mmsi"),
        pl.col("IMO").str.strip_chars().alias("imo"),
        pl.col("CallSign").str.strip_chars().alias("call_sign"),
        pl.col("VesselName").str.strip_chars().alias("vessel_name"),
        pl.col("TransceiverClass").str.strip_chars().alias("transceiver_class"),
        pl.lit(str(INPUT)).alias("source_file"),
        pl.lit(RUN_ID).alias("ingestion_run_id"),
        pl.lit(INGESTED_AT).cast(pl.Datetime(time_zone="UTC")).alias("ingested_at_utc"),
    )
    .with_columns(
        pl.struct(["mmsi_raw", "observed_at_utc", "latitude", "longitude"])
        .map_elements(
            lambda value: hashlib.sha256(
                json.dumps(value, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest(),
            return_dtype=pl.String,
        )
        .alias("record_hash")
    )
    .with_columns(
        (
            pl.col("mmsi").is_null()
            | pl.col("observed_at_utc").is_null()
            | pl.col("latitude").is_null()
            | pl.col("longitude").is_null()
            | (pl.col("latitude") < -90)
            | (pl.col("latitude") > 90)
            | (pl.col("longitude") < -180)
            | (pl.col("longitude") > 180)
        ).alias("is_quarantined")
    )
    .with_columns(
        pl.when(pl.col("mmsi").is_null()).then(pl.lit("missing_mmsi"))
        .when(pl.col("observed_at_utc").is_null()).then(pl.lit("invalid_timestamp"))
        .when(pl.col("latitude").is_null() | pl.col("longitude").is_null()).then(pl.lit("invalid_coordinate"))
        .when(
            (pl.col("latitude") < -90)
            | (pl.col("latitude") > 90)
            | (pl.col("longitude") < -180)
            | (pl.col("longitude") > 180)
        ).then(pl.lit("coordinate_out_of_range"))
        .otherwise(pl.lit(None, dtype=pl.String))
        .alias("quality_flag")
    )
)

all_rows = canonical.collect(engine="streaming")
valid = all_rows.filter(~pl.col("is_quarantined"))
quarantine = all_rows.filter(pl.col("is_quarantined"))

valid_before_dedup = valid.height
valid = valid.unique(subset=["record_hash"], maintain_order=False)

audit_columns = [
    "mmsi", "imo", "call_sign", "vessel_name", "observed_at_utc",
    "latitude", "longitude", "sog_knots", "cog_degrees", "heading_degrees",
    "nav_status", "vessel_type", "draft_m", "length_m", "width_m",
    "cargo_type", "transceiver_class", "source_file", "ingestion_run_id",
    "ingested_at_utc", "record_hash", "quality_flag", "is_quarantined",
]

valid.select(audit_columns).write_parquet(
    OUTPUT_DIR / "ais_ping.parquet", compression="zstd"
)
quarantine.select(audit_columns).write_parquet(
    QUARANTINE_DIR / "ais_quarantine.parquet", compression="zstd"
)

report = {
    "run_id": RUN_ID,
    "input": str(INPUT),
    "input_bytes": INPUT.stat().st_size,
    "rows_read": all_rows.height,
    "valid_rows_before_deduplication": valid_before_dedup,
    "valid_rows_after_deduplication": valid.height,
    "quarantined_rows": quarantine.height,
    "duplicate_rows_removed": valid_before_dedup - valid.height,
    "quality_flag_counts": quarantine.group_by("quality_flag").len().to_dicts(),
    "valid_output": str(OUTPUT_DIR / "ais_ping.parquet"),
    "quarantine_output": str(QUARANTINE_DIR / "ais_quarantine.parquet"),
}

REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
