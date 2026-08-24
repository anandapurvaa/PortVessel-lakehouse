from pathlib import Path
import duckdb

INPUT = "data/processed/ais_scope/ais_anchorage_events_2024-12-27_2024-12-29.parquet"
OUTPUT = "data/processed/ais_scope/anchorage_episodes_2024-12-27_2024-12-29_v2.parquet"

WINDOW_START = "2024-12-27 00:00:00"
WINDOW_END = "2024-12-30 00:00:00"
CENSOR_MARGIN_MINUTES = 60
EPISODE_GAP_MINUTES = 60
QUALITY_GAP_MINUTES = 30

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        WITH ordered AS (
            SELECT
                *,
                LAG(observed_at_utc) OVER (
                    PARTITION BY mmsi, anchorage_object_id
                    ORDER BY observed_at_utc
                ) AS previous_observed_at_utc
            FROM read_parquet('{INPUT}')
        ),
        gaps AS (
            SELECT
                *,
                EXTRACT(EPOCH FROM (
                    observed_at_utc - previous_observed_at_utc
                )) / 60.0 AS gap_minutes
            FROM ordered
        ),
        marked AS (
            SELECT
                *,
                CASE
                    WHEN previous_observed_at_utc IS NULL THEN 1
                    WHEN gap_minutes > {EPISODE_GAP_MINUTES} THEN 1
                    ELSE 0
                END AS is_new_episode
            FROM gaps
        ),
        numbered AS (
            SELECT
                *,
                SUM(is_new_episode) OVER (
                    PARTITION BY mmsi, anchorage_object_id
                    ORDER BY observed_at_utc
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS episode_number
            FROM marked
        ),
        aggregated AS (
            SELECT
                md5(
                    CAST(mmsi AS VARCHAR) || '|' ||
                    anchorage_object_id || '|' ||
                    CAST(MIN(observed_at_utc) AS VARCHAR)
                ) AS anchorage_episode_id,
                mmsi,
                anchorage_object_id,
                ANY_VALUE(anchorage_name) AS anchorage_name,
                ANY_VALUE(anchorage_information) AS anchorage_information,
                MIN(observed_at_utc) AS entry_observed_at_utc,
                MAX(observed_at_utc) AS exit_observed_at_utc,
                DATE_DIFF('minute', MIN(observed_at_utc), MAX(observed_at_utc))
                    AS observed_duration_minutes,
                COUNT(*) AS ping_count,
                COALESCE(MAX(gap_minutes), 0) AS max_gap_minutes,
                MIN(source_file) AS first_source_file,
                MAX(source_file) AS last_source_file,
                CAST(MIN(observed_at_utc) AS TIMESTAMP) <=
                    TIMESTAMP '{WINDOW_START}' + INTERVAL {CENSOR_MARGIN_MINUTES} MINUTE
                    AS is_left_censored,
                CAST(MAX(observed_at_utc) AS TIMESTAMP) >=
                    TIMESTAMP '{WINDOW_END}' - INTERVAL {CENSOR_MARGIN_MINUTES} MINUTE
                    AS is_right_censored
            FROM numbered
            GROUP BY mmsi, anchorage_object_id, episode_number
        )
        SELECT
            *,
            CASE
                WHEN is_left_censored AND is_right_censored
                    THEN 'partial_start_and_end'
                WHEN is_left_censored
                    THEN 'partial_start'
                WHEN is_right_censored
                    THEN 'partial_end'
                WHEN max_gap_minutes > {QUALITY_GAP_MINUTES}
                    THEN 'gap_uncertain'
                ELSE 'observed_continuous'
            END AS episode_quality,
            {EPISODE_GAP_MINUTES}::INTEGER AS episode_gap_threshold_minutes,
            {CENSOR_MARGIN_MINUTES}::INTEGER AS censor_margin_minutes,
            TIMESTAMP '{WINDOW_START}' AS source_window_start,
            TIMESTAMP '{WINDOW_END}' AS source_window_end
        FROM aggregated
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print("Output:", OUTPUT)
print(con.execute(f"""
    SELECT
        COUNT(*) AS episodes,
        COUNT(DISTINCT mmsi) AS vessels,
        AVG(observed_duration_minutes) AS mean_duration_minutes,
        MAX(observed_duration_minutes) AS max_duration_minutes
    FROM read_parquet('{OUTPUT}')
""").fetchdf())

print("\nQuality:")
print(con.execute(f"""
    SELECT episode_quality, COUNT(*) AS episodes
    FROM read_parquet('{OUTPUT}')
    GROUP BY episode_quality
    ORDER BY episode_quality
""").fetchdf())

print("\nComplete episodes:")
print(con.execute(f"""
    SELECT
        COUNT(*) AS episodes,
        AVG(observed_duration_minutes) AS mean_duration_minutes,
        MAX(observed_duration_minutes) AS max_duration_minutes
    FROM read_parquet('{OUTPUT}')
    WHERE episode_quality = 'observed_continuous'
""").fetchdf())
