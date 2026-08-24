from pathlib import Path
import duckdb
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "portvessel.duckdb"
REPORT_PATH = ROOT / "reports" / "data_quality_report.json"

con = duckdb.connect(str(DB_PATH), read_only=True)

queries = {
    "canonical_ping_counts": """
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT record_hash) AS unique_records,
            COUNT(DISTINCT mmsi) AS vessels,
            COUNT(*) FILTER (WHERE mmsi IS NULL) AS null_mmsi,
            COUNT(*) FILTER (WHERE observed_at_utc IS NULL) AS null_timestamp,
            COUNT(*) FILTER (WHERE latitude NOT BETWEEN -90 AND 90) AS invalid_latitude,
            COUNT(*) FILTER (WHERE longitude NOT BETWEEN -180 AND 180) AS invalid_longitude
        FROM read_parquet(
            'data/processed/ais/year=*/month=*/day=*/ais_ping.parquet'
        )
    """,
    "port_state_counts": """
        SELECT
            vessel_state,
            COUNT(*) AS rows,
            COUNT(DISTINCT mmsi) AS vessels
        FROM read_parquet(
            'data/processed/ais_scope/port_state_events_2024-12-27_2024-12-29.parquet'
        )
        GROUP BY vessel_state
        ORDER BY vessel_state
    """,
    "dwell_quality_counts": """
        SELECT
            dwell_quality,
            eligible_for_complete_metrics,
            eligible_for_persistent_metrics,
            COUNT(*) AS episodes,
            COUNT(DISTINCT mmsi) AS vessels
        FROM read_parquet(
            'data/processed/ais_scope/fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet'
        )
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
    """,
    "port_call_quality_counts": """
        SELECT
            port_call_quality,
            COUNT(*) AS port_calls,
            COUNT(DISTINCT mmsi) AS vessels,
            COUNT(*) FILTER (WHERE observed_port_duration_minutes < 0)
                AS invalid_durations
        FROM read_parquet(
            'data/processed/ais_scope/fct_port_call_2024-12-27_2024-12-29.parquet'
        )
        GROUP BY port_call_quality
        ORDER BY port_call_quality
    """,
}

report = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "datasets": {},
}

for name, sql in queries.items():
    report["datasets"][name] = con.execute(sql).fetchdf().to_dict(orient="records")

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print(json.dumps(report, indent=2, default=str))
print(f"\nWrote {REPORT_PATH}")
