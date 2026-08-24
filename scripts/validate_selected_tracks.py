from pathlib import Path
import duckdb

AIS_INPUT = (
    "data/processed/ais_scope/"
    "port_state_events_2024-12-27_2024-12-29.parquet"
)
EPISODE_INPUT = (
    "data/processed/ais_scope/"
    "fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet"
)
OUTPUT_DIR = Path("reports/track_validation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

vessels = [
    356696000,
    538010361,
    636022984,
    477131300,
    369042000,
]

for mmsi in vessels:
    query = f"""
        SELECT
            mmsi,
            observed_at_utc,
            latitude,
            longitude,
            sog_knots,
            cog_degrees,
            heading_degrees,
            vessel_state,
            geofence_id,
            geofence_name,
            record_hash,
            source_file
        FROM read_parquet('{AIS_INPUT}')
        WHERE mmsi = {mmsi}
        ORDER BY observed_at_utc
    """
    df = con.execute(query).fetchdf()
    path = OUTPUT_DIR / f"track_mmsi_{mmsi}.csv"
    df.to_csv(path, index=False)
    print(f"{mmsi}: {len(df)} rows -> {path}")

print("\nSelected episode summary:")
print(con.execute(f"""
    SELECT
        mmsi,
        anchorage_name,
        entry_observed_at_utc,
        exit_observed_at_utc,
        observed_dwell_minutes,
        ping_count,
        max_gap_minutes,
        episode_quality,
        eligible_for_persistent_metrics
    FROM read_parquet('{EPISODE_INPUT}')
    WHERE mmsi IN ({','.join(str(v) for v in vessels)})
    ORDER BY mmsi, entry_observed_at_utc
""").fetchdf().to_string(index=False))
