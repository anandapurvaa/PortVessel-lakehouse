INSTALL spatial;
LOAD spatial;

CREATE OR REPLACE TABLE reference_features AS
SELECT
    zone_id, zone_name, zone_type, port_id,
    effective_from, effective_to, source_name, source_url, license,
    ST_GeomFromGeoJSON(json_extract(geometry, '$')) AS geometry,
    source_properties
FROM read_json_auto('data/reference/normalized/reference_features.ndjson');

CREATE OR REPLACE TABLE ais_pings AS
SELECT *
FROM read_parquet('data/fixtures/ais_2024-01-04_sample.parquet');

CREATE OR REPLACE TABLE vessel_state_sessions AS
SELECT
    *,
    mmsi AS vessel_state
FROM ais_pings;

SELECT zone_type, port_id, COUNT(*) AS feature_count
FROM reference_features
GROUP BY zone_type, port_id
ORDER BY zone_type, port_id;

SELECT zone_type, COUNT(*) AS features,
       COUNT(*) FILTER (WHERE geometry IS NULL) AS missing_geometry
FROM reference_features
GROUP BY zone_type
ORDER BY zone_type;

SELECT COUNT(*) AS ais_rows FROM ais_pings;
SELECT COUNT(*) AS session_rows FROM vessel_state_sessions;
