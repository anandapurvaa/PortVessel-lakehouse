from pathlib import Path
import duckdb

INPUT = "data/processed/ais_scope/ais_anchorage_events_2024-12-27_2024-12-29.parquet"
OUTPUT = Path("reports/manual_track_samples")
OUTPUT.mkdir(parents=True, exist_ok=True)

vessels = [
    356696000,
    538010361,
    636022984,
    477131300,
    369042000,
]

con = duckdb.connect("data/warehouse/portvessel.duckdb")

for mmsi in vessels:
    result = con.execute(f"""
        SELECT
            mmsi,
            observed_at_utc,
            latitude,
            longitude,
            sog_knots,
            cog_degrees,
            heading_degrees,
            anchorage_object_id,
            anchorage_name,
            record_hash
        FROM read_parquet('{INPUT}')
        WHERE mmsi = {mmsi}
        ORDER BY observed_at_utc
    """).fetchdf()

    path = OUTPUT / f"mmsi_{mmsi}.csv"
    result.to_csv(path, index=False)
    print(f"{mmsi}: {len(result)} rows -> {path}")
