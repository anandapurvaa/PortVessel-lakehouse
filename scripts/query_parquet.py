import duckdb

con = duckdb.connect("data/warehouse/portvessel.duckdb")

result = con.execute("""
    SELECT
        COUNT(*) AS row_count,
        COUNT(DISTINCT mmsi) AS vessel_count,
        MIN(observed_at_utc) AS min_observed_at,
        MAX(observed_at_utc) AS max_observed_at,
        MIN(latitude) AS min_latitude,
        MAX(latitude) AS max_latitude,
        MIN(longitude) AS min_longitude,
        MAX(longitude) AS max_longitude
    FROM read_parquet(
        'data/processed/ais/year=2024/month=12/day=28/ais_ping.parquet'
    )
""").fetchdf()

print(result)