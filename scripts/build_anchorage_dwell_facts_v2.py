from pathlib import Path
import duckdb

INPUT = (
    "data/processed/ais_scope/"
    "anchorage_episodes_2024-12-27_2024-12-29.parquet"
)
OUTPUT = (
    "data/processed/ais_scope/"
    "fct_anchorage_dwell_2024-12-27_2024-12-29_v2.parquet"
)

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        SELECT
            anchorage_episode_id AS anchorage_dwell_id,
            mmsi,
            anchorage_object_id,
            anchorage_name,
            entry_observed_at_utc,
            exit_observed_at_utc,
            observed_duration_minutes AS observed_dwell_minutes,
            ping_count,
            max_gap_minutes,
            is_left_censored,
            is_right_censored,
            episode_quality,
            CASE
                WHEN is_left_censored AND is_right_censored
                    THEN 'partial_window'
                WHEN is_left_censored
                    THEN 'partial_start'
                WHEN is_right_censored
                    THEN 'partial_end'
                WHEN episode_quality = 'gap_uncertain'
                    THEN 'gap_uncertain'
                ELSE 'complete_observed'
            END AS dwell_quality,
            CASE
                WHEN is_left_censored OR is_right_censored
                    THEN FALSE
                WHEN episode_quality = 'gap_uncertain'
                    THEN FALSE
                ELSE TRUE
            END AS eligible_for_complete_metrics,
            first_source_file,
            last_source_file,
            source_window_start,
            source_window_end
        FROM read_parquet('{INPUT}')
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(con.execute(f"""
    SELECT
        dwell_quality,
        eligible_for_complete_metrics,
        COUNT(*) AS episodes,
        COUNT(DISTINCT mmsi) AS vessels,
        AVG(observed_dwell_minutes) AS mean_dwell_minutes
    FROM read_parquet('{OUTPUT}')
    GROUP BY 1, 2
    ORDER BY 1, 2
""").fetchdf())

print(f"Wrote {OUTPUT}")