from pathlib import Path
from time import perf_counter
import duckdb
import pandas as pd

DB_PATH = "data/warehouse/portvessel.duckdb"
REPORT = Path("reports/local_query_benchmark.csv")
REPORT.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(DB_PATH)
con.execute("INSTALL spatial")
con.execute("LOAD spatial")

queries = {
    "daily_ping_count": """
        SELECT COUNT(*) AS rows
        FROM read_parquet('data/processed/ais/year=2024/month=12/day=*/ais_ping.parquet')
    """,
    "anchorage_vessel_count": """
        SELECT COUNT(DISTINCT mmsi) AS vessels
        FROM read_parquet('data/processed/ais_scope/ais_anchorage_events_2024-12-27_2024-12-29.parquet')
    """,
    "daily_congestion": """
        SELECT metric_date, observed_port_calls, observed_vessels,
               median_port_duration_minutes
        FROM read_parquet('data/processed/ais_scope/agg_port_congestion_daily_2024-12-27_2024-12-29.parquet')
        ORDER BY metric_date
    """,
    "persistent_dwell_metrics": """
        SELECT anchorage_object_id,
               COUNT(*) AS episodes,
               MEDIAN(observed_dwell_minutes) AS median_minutes
        FROM read_parquet('data/processed/ais_scope/fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet')
        WHERE eligible_for_persistent_metrics
        GROUP BY anchorage_object_id
    """,
}

rows = []
for name, query in queries.items():
    for iteration in range(1, 4):
        start = perf_counter()
        result = con.execute(query).fetchdf()
        elapsed = perf_counter() - start
        rows.append({
            "query_name": name,
            "iteration": iteration,
            "wall_clock_seconds": elapsed,
            "result_rows": len(result),
        })

benchmark = pd.DataFrame(rows)
benchmark.to_csv(REPORT, index=False)
print(benchmark.to_string(index=False))
print(f"\nWrote {REPORT}")
