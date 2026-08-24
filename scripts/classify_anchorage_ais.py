from pathlib import Path
import duckdb

AIS_INPUT = "data/processed/ais/year=2024/month=12/day=28/ais_ping.parquet"
ANCHORAGE_INPUT = "data/reference/raw/la_lb_anchorage_areas.geojson"
OUTPUT = "data/processed/ais_scope/year=2024/month=12/day=28/ais_anchorage_events.parquet"

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")
con.execute("INSTALL spatial")
con.execute("LOAD spatial")

con.execute(f"""
    CREATE OR REPLACE TABLE anchorage AS
    SELECT
        OBJECTID::VARCHAR AS anchorage_object_id,
        NULLIF(TRIM(OBJNAM), '')::VARCHAR AS anchorage_name,
        NULLIF(TRIM(INFORM), '')::VARCHAR AS anchorage_information,
        geom AS geometry
    FROM ST_Read('{ANCHORAGE_INPUT}')
""")

con.execute(f"""
    COPY (
        WITH matches AS (
            SELECT
                p.mmsi,
                p.observed_at_utc,
                p.latitude,
                p.longitude,
                p.sog_knots,
                p.cog_degrees,
                p.heading_degrees,
                p.vessel_name,
                p.imo,
                p.call_sign,
                p.vessel_type,
                p.source_file,
                p.ingestion_run_id,
                p.record_hash,
                a.anchorage_object_id,
                a.anchorage_name,
                a.anchorage_information,
                'noaa_enc_anchorage_areas' AS geofence_source,
                '2026-08-24' AS geofence_reference_version,
                ROW_NUMBER() OVER (
                    PARTITION BY p.record_hash
                    ORDER BY ST_Area(a.geometry) ASC, a.anchorage_object_id
                ) AS match_rank
            FROM read_parquet('{AIS_INPUT}') AS p
            JOIN anchorage AS a
              ON ST_COVEREDBY(
                  ST_Point(p.longitude, p.latitude),
                  a.geometry
              )
            WHERE p.longitude BETWEEN -118.35 AND -118.05
              AND p.latitude BETWEEN 33.60 AND 33.90
        )
        SELECT * EXCLUDE (match_rank)
        FROM matches
        WHERE match_rank = 1
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print("Summary:")
print(con.execute(f"""
    SELECT
        COUNT(*) AS matched_pings,
        COUNT(DISTINCT mmsi) AS matched_vessels,
        COUNT(DISTINCT anchorage_object_id) AS matched_anchorages,
        MIN(observed_at_utc) AS first_observation,
        MAX(observed_at_utc) AS last_observation
    FROM read_parquet('{OUTPUT}')
""").fetchdf())

print("\nPings by anchorage:")
print(con.execute(f"""
    SELECT
        COALESCE(anchorage_name, '[unnamed feature]') AS anchorage_name,
        COUNT(*) AS ping_count,
        COUNT(DISTINCT mmsi) AS vessel_count
    FROM read_parquet('{OUTPUT}')
    GROUP BY 1
    ORDER BY ping_count DESC
""").fetchdf())
