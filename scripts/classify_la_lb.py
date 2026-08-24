import duckdb

input_path = (
    "data/processed/ais_scope/year=2024/month=12/day=28/"
    "ais_la_lb_candidate.parquet"
)
output_path = (
    "data/processed/ais_scope/year=2024/month=12/day=28/"
    "ais_la_lb_state.parquet"
)
geofence_path = "data/reference/geofences/la_lb_port_area.geojson"

con = duckdb.connect("data/warehouse/portvessel.duckdb")
con.execute("INSTALL spatial")
con.execute("LOAD spatial")

con.execute(f"""
    CREATE OR REPLACE TABLE geofence AS
    SELECT
        geofence_id,
        port_id,
        geofence_type,
        ST_GeomFromGeoJSON(geometry) AS geometry
    FROM read_json_auto('{geofence_path}')
""")