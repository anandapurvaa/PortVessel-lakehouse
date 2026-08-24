from pathlib import Path
import duckdb

PORT_CALLS = "data/processed/ais_scope/fct_port_call_2024-12-27_2024-12-29.parquet"
DWELL = "data/processed/ais_scope/fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet"
OUTPUT = "data/processed/ais_scope/vessel_operational_risk_flags_2024-12-27_2024-12-29.parquet"

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        WITH port_calls AS (
            SELECT
                mmsi,
                COUNT(*) AS port_call_count,
                MAX(observed_port_duration_minutes) AS max_port_duration_minutes,
                AVG(observed_port_duration_minutes) AS mean_port_duration_minutes,
                COUNT(*) FILTER (
                    WHERE has_observed_anchorage
                ) AS port_calls_with_anchorage,
                COUNT(*) FILTER (
                    WHERE port_call_quality LIKE 'partial%'
                ) AS partial_port_calls
            FROM read_parquet('{PORT_CALLS}')
            GROUP BY mmsi
        ),
        dwell AS (
            SELECT
                mmsi,
                COUNT(*) FILTER (
                    WHERE eligible_for_persistent_metrics
                ) AS persistent_anchorage_episode_count,
                MAX(observed_dwell_minutes) FILTER (
                    WHERE eligible_for_persistent_metrics
                ) AS max_persistent_anchorage_dwell_minutes,
                AVG(observed_dwell_minutes) FILTER (
                    WHERE eligible_for_persistent_metrics
                ) AS mean_persistent_anchorage_dwell_minutes,
                MAX(max_gap_minutes) AS max_observation_gap_minutes
            FROM read_parquet('{DWELL}')
            GROUP BY mmsi
        )
        SELECT
            COALESCE(p.mmsi, d.mmsi) AS mmsi,
            COALESCE(port_call_count, 0) AS port_call_count,
            COALESCE(port_calls_with_anchorage, 0) AS port_calls_with_anchorage,
            COALESCE(partial_port_calls, 0) AS partial_port_calls,
            COALESCE(persistent_anchorage_episode_count, 0)
                AS persistent_anchorage_episode_count,
            max_port_duration_minutes,
            mean_port_duration_minutes,
            max_persistent_anchorage_dwell_minutes,
            mean_persistent_anchorage_dwell_minutes,
            max_observation_gap_minutes,
            CASE
                WHEN COALESCE(persistent_anchorage_episode_count, 0) > 0
                 AND COALESCE(max_persistent_anchorage_dwell_minutes, 0) >= 240
                    THEN 'high_observed_anchorage_dwell'
                WHEN COALESCE(persistent_anchorage_episode_count, 0) > 0
                    THEN 'observed_anchorage_dwell'
                WHEN COALESCE(port_call_count, 0) > 0
                    THEN 'port_area_observed'
                ELSE 'insufficient_observation'
            END AS operational_flag
        FROM port_calls p
        FULL OUTER JOIN dwell d USING (mmsi)
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(con.execute(f"""
    SELECT operational_flag, COUNT(*) AS vessels
    FROM read_parquet('{OUTPUT}')
    GROUP BY operational_flag
    ORDER BY operational_flag
""").fetchdf())

print(f"Wrote {OUTPUT}")
