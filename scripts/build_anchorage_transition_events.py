from pathlib import Path
import duckdb

INPUT = "data/processed/ais_scope/port_state_events_2024-12-27_2024-12-29.parquet"
OUTPUT = "data/processed/ais_scope/anchorage_transition_events_2024-12-27_2024-12-29.parquet"

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        WITH ordered AS (
            SELECT
                *,
                LAG(vessel_state) OVER (
                    PARTITION BY mmsi
                    ORDER BY observed_at_utc
                ) AS previous_state,
                LAG(observed_at_utc) OVER (
                    PARTITION BY mmsi
                    ORDER BY observed_at_utc
                ) AS previous_observed_at_utc,
                LAG(geofence_id) OVER (
                    PARTITION BY mmsi
                    ORDER BY observed_at_utc
                ) AS previous_geofence_id
            FROM read_parquet('{INPUT}')
        ),
        transitions AS (
            SELECT
                *,
                CASE
                    WHEN previous_state IS NULL THEN 'initial_observation'
                    WHEN previous_state <> vessel_state
                        AND vessel_state = 'anchorage'
                        THEN 'anchorage_entry'
                    WHEN previous_state = 'anchorage'
                        AND vessel_state <> 'anchorage'
                        THEN 'anchorage_exit'
                    WHEN previous_state = 'anchorage'
                        AND vessel_state = 'anchorage'
                        AND previous_geofence_id <> geofence_id
                        THEN 'anchorage_change'
                    ELSE NULL
                END AS transition_type
            FROM ordered
        )
        SELECT
            mmsi,
            observed_at_utc AS transition_observed_at_utc,
            transition_type,
            previous_state,
            vessel_state,
            previous_geofence_id,
            geofence_id,
            geofence_name,
            latitude,
            longitude,
            sog_knots,
            source_file,
            record_hash,
            ingestion_run_id
        FROM transitions
        WHERE transition_type IS NOT NULL
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(con.execute(f"""
    SELECT transition_type, COUNT(*) AS events, COUNT(DISTINCT mmsi) AS vessels
    FROM read_parquet('{OUTPUT}')
    GROUP BY transition_type
    ORDER BY transition_type
""").fetchdf())

print(f"Wrote {OUTPUT}")
