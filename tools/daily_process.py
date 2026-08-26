from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path


def run(command: list[str]) -> None:
    print("RUN", " ".join(command))
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-date", required=True, type=date.fromisoformat)
    parser.add_argument("--database", default="data/local/portvessel.duckdb")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    manifest = root / "data/reference/normalized/reference_features.ndjson"
    ais = root / "data/fixtures" / f"ais_{args.process_date.isoformat()}_sample.parquet"
    db = root / args.database

    if not manifest.exists():
        raise FileNotFoundError(manifest)
    if not ais.exists():
        raise FileNotFoundError(ais)

    sql = f"""
    INSTALL spatial;
    LOAD spatial;
    SET geometry_always_xy = true;
    CREATE OR REPLACE TABLE run_metadata AS
    SELECT DATE '{args.process_date.isoformat()}' AS process_date,
           current_timestamp AS started_at,
           '{ais.name}' AS ais_file,
           '{manifest.name}' AS reference_file;
    """
    run(["duckdb", str(db), "-c", sql])

    for filename in [
        "local_spatial_init.sql",
        "duckdb_spatial_enrichment.sql",
        "sessionize_vessel_states.sql",
        "build_daily_sessions.sql",
        "build_daily_port_events.sql",
        "build_berth_events.sql",
        "build_port_calls.sql",
        "build_daily_congestion.sql",
    ]:
        run(["duckdb", str(db), "-c", f".read scripts/{filename}" if filename == "local_spatial_init.sql" else f".read sql/{filename}"])

    print(json.dumps({"status": "PASS", "process_date": args.process_date.isoformat(), "database": str(db)}))


if __name__ == "__main__":
    main()
