from pathlib import Path
import duckdb

INPUT = "data/processed/ais_scope/anchorage_transition_events_2024-12-27_2024-12-29.parquet"
OUTPUT = "data/processed/ais_scope/fct_anchorage_dwell_2024-12-27_2024-12-29.parquet"

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        WITH entries AS (
            SELECT
                mmsi,
                transition_observed_at_utc AS entry_observed_at_utc,
                geofence_id AS anchorage_object_id,
                geofence_name AS anchorage_name,
                latitude AS entry_latitude,
                longitude AS entry_longitude,
                sog_knots AS entry_sog_knots,
                source_file AS entry_source_file,
                record_hash AS entry_record_hash
            FROM read_parquet('{INPUT}')
            WHERE transition_type = 'anchorage_entry'
        ),
        exits AS (
            SELECT
                mmsi,
                transition_observed_at_utc AS exit_observed_at_utc,
                previous_geofence_id AS anchorage_object_id,
                latitude AS exit_latitude,
                longitude AS exit_longitude,
                sog_knots AS exit_sog_knots,
                source_file AS exit_source_file,
                record_hash AS exit_record_hash
            FROM read_parquet('{INPUT}')
            WHERE transition_type = 'anchorage_exit'
        ),
        matched AS (
            SELECT
                e.*,
                x.exit_observed_at_utc,
                x.exit_latitude,
                x.exit_longitude,
                x.exit_sog_knots,
                x.exit_source_file,
                x.exit_record_hash,
                ROW_NUMBER() OVER (
                    PARTITION BY e.mmsi, e.entry_observed_at_utc
                    ORDER BY x.exit_observed_at_utc
                ) AS exit_rank
            FROM entries e
            LEFT JOIN exits x
              ON x.mmsi = e.mmsi
             AND x.anchorage_object_id = e.anchorage_object_id
             AND x.exit_observed_at_utc > e.entry_observed_at_utc
        )
        SELECT
            md5(
                CAST(mmsi AS VARCHAR) || '|' ||
                anchorage_object_id || '|' ||
                CAST(entry_observed_at_utc AS VARCHAR)
            ) AS anchorage_dwell_id,
            mmsi,
            anchorage_object_id,
            anchorage_name,
            entry_observed_at_utc,
            exit_observed_at_utc,
            DATE_DIFF('minute', entry_observed_at_utc, exit_observed_at_utc)
                AS observed_dwell_minutes,
            entry_latitude,
            entry_longitude,
            exit_latitude,
            exit_longitude,
            entry_sog_knots,
            exit_sog_knots,
            exit_observed_at_utc IS NULL AS is_open_episode,
            CASE
                WHEN exit_observed_at_utc IS NULL THEN 'open'
                ELSE 'closed'
            END AS dwell_status,
            entry_source_file,
            exit_source_file,
            entry_record_hash,
            exit_record_hash
        FROM matched
        WHERE exit_rank = 1 OR exit_rank IS NULL
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(con.execute(f"""
    SELECT
        dwell_status,
        COUNT(*) AS episodes,
        COUNT(DISTINCT mmsi) AS vessels,
        AVG(observed_dwell_minutes) AS mean_dwell_minutes
    FROM read_parquet('{OUTPUT}')
    GROUP BY dwell_status
    ORDER BY dwell_status
""").fetchdf())

print(f"Wrote {OUTPUT}")
