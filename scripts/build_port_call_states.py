from pathlib import Path
import duckdb

INPUT = "data/processed/ais_scope/port_state_events_2024-12-27_2024-12-29.parquet"
OUTPUT = "data/processed/ais_scope/port_call_state_events_2024-12-27_2024-12-29.parquet"

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
                LEAD(vessel_state) OVER (
                    PARTITION BY mmsi
                    ORDER BY observed_at_utc
                ) AS next_state,
                LEAD(observed_at_utc) OVER (
                    PARTITION BY mmsi
                    ORDER BY observed_at_utc
                ) AS next_observed_at_utc
            FROM read_parquet('{INPUT}')
        ),
        classified AS (
            SELECT
                *,
                CASE
                    WHEN vessel_state = 'anchorage'
                     AND (previous_state IS NULL OR previous_state <> 'anchorage')
                        THEN 'anchorage_entry'
                    WHEN vessel_state <> 'anchorage'
                     AND previous_state = 'anchorage'
                        THEN 'anchorage_exit'
                    WHEN vessel_state = 'port_area_unclassified'
                     AND (previous_state IS NULL OR previous_state = 'anchorage')
                        THEN 'port_area_observation'
                    ELSE NULL
                END AS state_event_type
            FROM ordered
        )
        SELECT
            md5(
                CAST(mmsi AS VARCHAR) || '|' ||
                CAST(observed_at_utc AS VARCHAR) || '|' ||
                COALESCE(state_event_type, '')
            ) AS state_event_id,
            mmsi,
            observed_at_utc AS event_observed_at_utc,
            state_event_type,
            previous_state,
            vessel_state,
            next_state,
            previous_observed_at_utc,
            next_observed_at_utc,
            latitude,
            longitude,
            sog_knots,
            geofence_id,
            geofence_name,
            source_file,
            record_hash,
            ingestion_run_id
        FROM classified
        WHERE state_event_type IS NOT NULL
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(con.execute(f"""
    SELECT state_event_type, COUNT(*) AS events, COUNT(DISTINCT mmsi) AS vessels
    FROM read_parquet('{OUTPUT}')
    GROUP BY state_event_type
    ORDER BY state_event_type
""").fetchdf())

print(f"Wrote {OUTPUT}")
