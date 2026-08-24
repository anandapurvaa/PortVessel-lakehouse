from pathlib import Path
import duckdb

INPUT = "data/processed/ais_scope/port_state_events_2024-12-27_2024-12-29.parquet"
OUTPUT = "data/processed/ais_scope/fct_port_call_2024-12-27_2024-12-29.parquet"
PORT_ID = "la_lb_candidate_area"
PORT_NAME = "Los Angeles / Long Beach candidate area"
VISIT_GAP_MINUTES = 180

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        WITH inside AS (
            SELECT
                *,
                LAG(observed_at_utc) OVER (
                    PARTITION BY mmsi
                    ORDER BY observed_at_utc
                ) AS previous_observed_at_utc
            FROM read_parquet('{INPUT}')
        ),
        visit_marks AS (
            SELECT
                *,
                CASE
                    WHEN previous_observed_at_utc IS NULL THEN 1
                    WHEN EXTRACT(EPOCH FROM (
                        observed_at_utc - previous_observed_at_utc
                    )) / 60.0 > {VISIT_GAP_MINUTES} THEN 1
                    ELSE 0
                END AS new_visit
            FROM inside
        ),
        visits AS (
            SELECT
                *,
                SUM(new_visit) OVER (
                    PARTITION BY mmsi
                    ORDER BY observed_at_utc
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS visit_number
            FROM visit_marks
        ),
        facts AS (
            SELECT
                md5(
                    CAST(mmsi AS VARCHAR) || '|' ||
                    CAST(MIN(observed_at_utc) AS VARCHAR) || '|' ||
                    '{PORT_ID}'
                ) AS port_call_id,
                mmsi,
                '{PORT_ID}' AS port_id,
                '{PORT_NAME}' AS port_name,
                MIN(observed_at_utc) AS arrival_observed_at_utc,
                MAX(observed_at_utc) AS departure_observed_at_utc,
                DATE_DIFF(
                    'minute',
                    MIN(observed_at_utc),
                    MAX(observed_at_utc)
                ) AS observed_port_duration_minutes,
                COUNT(*) AS ping_count,
                COUNT(DISTINCT geofence_id) FILTER (
                    WHERE vessel_state = 'anchorage'
                ) AS anchorage_features_observed,
                MIN(observed_at_utc) FILTER (
                    WHERE vessel_state = 'anchorage'
                ) AS anchorage_entry_observed_at_utc,
                MAX(observed_at_utc) FILTER (
                    WHERE vessel_state = 'anchorage'
                ) AS anchorage_last_observed_at_utc,
                MIN(source_file) AS first_source_file,
                MAX(source_file) AS last_source_file
            FROM visits
            GROUP BY mmsi, visit_number
        )
        SELECT
            *,
            anchorage_entry_observed_at_utc IS NOT NULL
                AS has_observed_anchorage,
            CASE
                WHEN arrival_observed_at_utc <= TIMESTAMP '2024-12-27 01:00:00'
                    THEN 'partial_start'
                WHEN departure_observed_at_utc >= TIMESTAMP '2024-12-30 00:00:00'
                    THEN 'partial_end'
                WHEN anchorage_entry_observed_at_utc IS NOT NULL
                    THEN 'observed_with_anchorage'
                ELSE 'observed_port_area_only'
            END AS port_call_quality,
            {VISIT_GAP_MINUTES}::INTEGER AS visit_gap_threshold_minutes
        FROM facts
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(con.execute(f"""
    SELECT
        port_call_quality,
        COUNT(*) AS port_calls,
        COUNT(DISTINCT mmsi) AS vessels,
        AVG(observed_port_duration_minutes) AS mean_duration_minutes
    FROM read_parquet('{OUTPUT}')
    GROUP BY port_call_quality
    ORDER BY port_call_quality
""").fetchdf())

print(f"Wrote {OUTPUT}")
