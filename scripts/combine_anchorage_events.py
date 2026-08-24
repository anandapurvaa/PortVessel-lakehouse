from pathlib import Path
import duckdb

output = (
    "data/processed/ais_scope/"
    "ais_anchorage_events_2024-12-27_2024-12-29.parquet"
)

Path(output).parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        SELECT *
        FROM read_parquet([
            'data/processed/ais_scope/year=2024/month=12/day=27/ais_anchorage_events.parquet',
            'data/processed/ais_scope/year=2024/month=12/day=28/ais_anchorage_events.parquet',
            'data/processed/ais_scope/year=2024/month=12/day=29/ais_anchorage_events.parquet'
        ])
    )
    TO '{output}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(
    con.execute(f"""
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT record_hash) AS unique_pings,
            COUNT(DISTINCT mmsi) AS vessels,
            MIN(observed_at_utc) AS first_observation,
            MAX(observed_at_utc) AS last_observation
        FROM read_parquet('{output}')
    """).fetchdf()
)