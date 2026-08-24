from pathlib import Path
from typing import Any
import duckdb
from fastapi import FastAPI, HTTPException, Query

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "warehouse" / "portvessel.duckdb"
CONGESTION = ROOT / "data" / "processed" / "ais_scope" / "agg_port_congestion_daily_2024-12-27_2024-12-29.parquet"
DWELL = ROOT / "data" / "processed" / "ais_scope" / "fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet"
VESSEL_FLAGS = ROOT / "data" / "processed" / "ais_scope" / "vessel_operational_risk_flags_2024-12-27_2024-12-29.parquet"

app = FastAPI(title="PortVessel API", version="0.1.0")


def query_rows(sql: str) -> list[dict[str, Any]]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(sql).fetchdf().to_dict(orient="records")
    finally:
        con.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics/congestion")
def congestion() -> list[dict[str, Any]]:
    if not CONGESTION.exists():
        raise HTTPException(status_code=404, detail="Congestion dataset not found")
    return query_rows(f"""
        SELECT *
        FROM read_parquet('{CONGESTION.as_posix()}')
        ORDER BY metric_date, port_id
    """)


@app.get("/metrics/dwell")
def dwell() -> list[dict[str, Any]]:
    if not DWELL.exists():
        raise HTTPException(status_code=404, detail="Dwell dataset not found")
    return query_rows(f"""
        SELECT
            anchorage_object_id,
            anchorage_name,
            COUNT(*) FILTER (WHERE eligible_for_persistent_metrics) AS episodes,
            COUNT(DISTINCT mmsi) FILTER (WHERE eligible_for_persistent_metrics) AS vessels,
            MEDIAN(observed_dwell_minutes) FILTER (WHERE eligible_for_persistent_metrics) AS median_minutes,
            QUANTILE_CONT(observed_dwell_minutes, 0.90) FILTER (WHERE eligible_for_persistent_metrics) AS p90_minutes
        FROM read_parquet('{DWELL.as_posix()}')
        GROUP BY 1, 2
        HAVING episodes > 0
        ORDER BY episodes DESC
    """)


@app.get("/vessels/{mmsi}")
def vessel(mmsi: int) -> dict[str, Any]:
    if not VESSEL_FLAGS.exists():
        raise HTTPException(status_code=404, detail="Vessel flags dataset not found")
    rows = query_rows(f"""
        SELECT *
        FROM read_parquet('{VESSEL_FLAGS.as_posix()}')
        WHERE mmsi = {mmsi}
    """)
    if not rows:
        raise HTTPException(status_code=404, detail="Vessel not found")
    return rows[0]


@app.get("/vessels")
def vessels(limit: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
    if not VESSEL_FLAGS.exists():
        raise HTTPException(status_code=404, detail="Vessel flags dataset not found")
    return query_rows(f"""
        SELECT *
        FROM read_parquet('{VESSEL_FLAGS.as_posix()}')
        ORDER BY max_persistent_anchorage_dwell_minutes DESC NULLS LAST
        LIMIT {limit}
    """)