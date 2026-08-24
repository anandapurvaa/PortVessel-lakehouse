import duckdb

INPUT = (
    "data/processed/ais_scope/"
    "anchorage_transition_events_2024-12-27_2024-12-29.parquet"
)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

print("Transition counts:")
print(con.execute(f"""
    SELECT
        transition_type,
        COUNT(*) AS events,
        COUNT(DISTINCT mmsi) AS vessels
    FROM read_parquet('{INPUT}')
    GROUP BY transition_type
    ORDER BY transition_type
""").fetchdf())

print("\nEntries without a later exit:")
print(con.execute(f"""
    WITH entries AS (
        SELECT mmsi, transition_observed_at_utc, geofence_id
        FROM read_parquet('{INPUT}')
        WHERE transition_type = 'anchorage_entry'
    ),
    exits AS (
        SELECT mmsi, transition_observed_at_utc, previous_geofence_id AS geofence_id
        FROM read_parquet('{INPUT}')
        WHERE transition_type = 'anchorage_exit'
    )
    SELECT COUNT(*) AS unmatched_entries
    FROM entries e
    LEFT JOIN exits x
      ON x.mmsi = e.mmsi
     AND x.geofence_id = e.geofence_id
     AND x.transition_observed_at_utc > e.transition_observed_at_utc
    WHERE x.transition_observed_at_utc IS NULL
""").fetchdf())

print("\nOpen dwell records:")
print(con.execute(f"""
    SELECT
        mmsi,
        anchorage_name,
        entry_observed_at_utc,
        observed_dwell_minutes,
        dwell_status
    FROM read_parquet(
        'data/processed/ais_scope/'
        'fct_anchorage_dwell_2024-12-27_2024-12-29.parquet'
    )
    WHERE dwell_status = 'open'
    ORDER BY entry_observed_at_utc
    LIMIT 20
""").fetchdf())