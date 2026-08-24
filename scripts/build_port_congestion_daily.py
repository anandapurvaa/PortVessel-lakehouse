from pathlib import Path
import duckdb

INPUT = "data/processed/ais_scope/fct_port_call_2024-12-27_2024-12-29.parquet"
OUTPUT = "data/processed/ais_scope/agg_port_congestion_daily_2024-12-27_2024-12-29.parquet"

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        SELECT
            CAST(arrival_observed_at_utc AS DATE) AS metric_date,
            port_id,
            port_name,
            COUNT(*) AS observed_port_calls,
            COUNT(DISTINCT mmsi) AS observed_vessels,
            COUNT(*) FILTER (
                WHERE has_observed_anchorage
            ) AS port_calls_with_anchorage,
            MEDIAN(observed_port_duration_minutes) AS median_port_duration_minutes,
            QUANTILE_CONT(observed_port_duration_minutes, 0.90)
                AS p90_port_duration_minutes,
            AVG(observed_port_duration_minutes) AS mean_port_duration_minutes,
            COUNT(*) FILTER (
                WHERE port_call_quality = 'observed_with_anchorage'
            ) AS observed_with_anchorage_calls,
            COUNT(*) FILTER (
                WHERE port_call_quality LIKE 'partial%'
            ) AS partial_calls
        FROM read_parquet('{INPUT}')
        GROUP BY 1, 2, 3
        ORDER BY 1, 2
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(con.execute(f"""
    SELECT *
    FROM read_parquet('{OUTPUT}')
    ORDER BY metric_date
""").fetchdf().to_string(index=False))

print(f"Wrote {OUTPUT}")
