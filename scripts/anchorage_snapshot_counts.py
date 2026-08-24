from pathlib import Path
import duckdb

INPUT = (
    "data/processed/ais_scope/year=2024/month=12/day=28/"
    "ais_anchorage_events.parquet"
)
OUTPUT = Path(
    "reports/anchorage_snapshot_counts_2024_12_28.csv"
)

if not Path(INPUT).exists():
    raise FileNotFoundError(
        f"Missing input file: {INPUT}. Run classify_anchorage_ais.py first."
    )

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

query = f"""
    SELECT
        date_trunc('hour', observed_at_utc) AS hour_utc,
        anchorage_object_id,
        COALESCE(anchorage_name, '[unnamed feature]') AS anchorage_name,
        COUNT(DISTINCT mmsi) AS vessels_observed,
        COUNT(*) AS pings
    FROM read_parquet('{INPUT}')
    GROUP BY 1, 2, 3
    ORDER BY 1, 2
"""

result = con.execute(query).fetchdf()
result.to_csv(OUTPUT, index=False)

print(result.to_string(index=False))
print(f"\nWrote {OUTPUT}")
