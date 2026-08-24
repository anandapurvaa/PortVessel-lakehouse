from pathlib import Path
import duckdb

INPUT = (
    "data/processed/ais_scope/"
    "fct_anchorage_dwell_2024-12-27_2024-12-29_v2.parquet"
)
OUTPUT = (
    "data/processed/ais_scope/"
    "fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet"
)

MIN_PINGS = 3
MIN_DWELL_MINUTES = 10

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        SELECT
            *,
            ping_count >= {MIN_PINGS}
                AS meets_minimum_ping_count,
            observed_dwell_minutes >= {MIN_DWELL_MINUTES}
                AS meets_minimum_dwell_minutes,
            eligible_for_complete_metrics
                AND ping_count >= {MIN_PINGS}
                AND observed_dwell_minutes >= {MIN_DWELL_MINUTES}
                AS eligible_for_persistent_metrics,
            CASE
                WHEN NOT eligible_for_complete_metrics THEN 'not_complete'
                WHEN ping_count < {MIN_PINGS} THEN 'too_few_pings'
                WHEN observed_dwell_minutes < {MIN_DWELL_MINUTES} THEN 'too_short'
                ELSE 'persistent_observed_dwell'
            END AS persistence_quality
        FROM read_parquet('{INPUT}')
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(con.execute(f"""
    SELECT
        persistence_quality,
        COUNT(*) AS episodes,
        COUNT(DISTINCT mmsi) AS vessels,
        AVG(observed_dwell_minutes) AS mean_minutes
    FROM read_parquet('{OUTPUT}')
    GROUP BY persistence_quality
    ORDER BY persistence_quality
""").fetchdf())

print(f"Wrote {OUTPUT}")
