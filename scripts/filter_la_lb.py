from pathlib import Path
import duckdb

input_path = (
    "data/processed/ais/year=2024/month=12/day=28/ais_ping.parquet"
)
output_path = (
    "data/processed/ais_scope/year=2024/month=12/day=28/"
    "ais_la_lb_candidate.parquet"
)

Path(output_path).parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        SELECT *
        FROM read_parquet('{input_path}')
        WHERE longitude BETWEEN -118.35 AND -117.90
          AND latitude BETWEEN 33.60 AND 34.10
    )
    TO '{output_path}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

summary = con.execute(f"""
    SELECT
        COUNT(*) AS row_count,
        COUNT(DISTINCT mmsi) AS vessel_count,
        MIN(observed_at_utc) AS min_observed_at,
        MAX(observed_at_utc) AS max_observed_at
    FROM read_parquet('{output_path}')
""").fetchdf()

print(summary)