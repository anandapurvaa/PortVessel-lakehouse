from pathlib import Path
import duckdb

DATES = ["2024-12-27", "2024-12-28", "2024-12-29"]
ANCHORAGE_INPUT = "data/reference/raw/la_lb_anchorage_areas.geojson"

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

for source_date in DATES:
    year, month, day = source_date.split("-")
    input_path = (
        f"data/processed/ais/year={year}/month={month}/day={day}/"
        "ais_ping.parquet"
    )
    output_path = (
        f"data/processed/ais_scope/year={year}/month={month}/day={day}/"
        "ais_anchorage_events.parquet"
    )

    if not Path(input_path).exists():
        raise FileNotFoundError(input_path)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

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
                FROM read_parquet('{input_path}') AS p
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
        TO '{output_path}'
        (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    print(f"\n{source_date}")
    print(con.execute(f"""
        SELECT
            COUNT(*) AS matched_pings,
            COUNT(DISTINCT mmsi) AS matched_vessels,
            COUNT(DISTINCT anchorage_object_id) AS matched_anchorages,
            MIN(observed_at_utc) AS first_observation,
            MAX(observed_at_utc) AS last_observation
        FROM read_parquet('{output_path}')
    """).fetchdf())
