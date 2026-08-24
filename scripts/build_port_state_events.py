from pathlib import Path
import duckdb

AIS_FILES = [
    "data/processed/ais/year=2024/month=12/day=27/ais_ping.parquet",
    "data/processed/ais/year=2024/month=12/day=28/ais_ping.parquet",
    "data/processed/ais/year=2024/month=12/day=29/ais_ping.parquet",
]
ANCHORAGE_INPUT = "data/reference/raw/la_lb_anchorage_areas.geojson"
OUTPUT = "data/processed/ais_scope/port_state_events_2024-12-27_2024-12-29.parquet"

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")
con.execute("INSTALL spatial")
con.execute("LOAD spatial")

files_sql = "[" + ",".join(f"'{path}'" for path in AIS_FILES) + "]"

con.execute(f"""
    CREATE OR REPLACE TABLE anchorage AS
    SELECT
        OBJECTID::VARCHAR AS geofence_id,
        NULLIF(TRIM(OBJNAM), '')::VARCHAR AS geofence_name,
        'anchorage'::VARCHAR AS geofence_type,
        geom AS geometry
    FROM ST_Read('{ANCHORAGE_INPUT}')
""")

con.execute(f"""
    COPY (
        WITH pings AS (
            SELECT *
            FROM read_parquet({files_sql})
            WHERE longitude BETWEEN -118.35 AND -118.05
              AND latitude BETWEEN 33.60 AND 33.90
        ),
        matched AS (
            SELECT
                p.*,
                g.geofence_id,
                g.geofence_name,
                g.geofence_type,
                ROW_NUMBER() OVER (
                    PARTITION BY p.record_hash
                    ORDER BY ST_Area(g.geometry), g.geofence_id
                ) AS match_rank
            FROM pings p
            LEFT JOIN anchorage g
              ON ST_COVEREDBY(
                  ST_Point(p.longitude, p.latitude),
                  g.geometry
              )
        )
        SELECT
            mmsi,
            observed_at_utc,
            latitude,
            longitude,
            sog_knots,
            cog_degrees,
            heading_degrees,
            vessel_name,
            imo,
            call_sign,
            vessel_type,
            source_file,
            ingestion_run_id,
            record_hash,
            CASE
                WHEN geofence_type = 'anchorage' THEN 'anchorage'
                ELSE 'port_area_unclassified'
            END AS vessel_state,
            geofence_id,
            geofence_name,
            geofence_type,
            'noaa_enc_anchorage_areas' AS geofence_source
        FROM matched
        WHERE match_rank = 1
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(con.execute(f"""
    SELECT
        vessel_state,
        COUNT(*) AS pings,
        COUNT(DISTINCT mmsi) AS vessels
    FROM read_parquet('{OUTPUT}')
    GROUP BY vessel_state
    ORDER BY vessel_state
""").fetchdf())

print(f"Wrote {OUTPUT}")
