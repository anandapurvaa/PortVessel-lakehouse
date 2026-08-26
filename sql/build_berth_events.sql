INSTALL spatial;
LOAD spatial;
SET geometry_always_xy = true;

DROP TABLE IF EXISTS berth_reference;
DROP TABLE IF EXISTS berth_candidate_pings;
DROP TABLE IF EXISTS berth_events;

CREATE TABLE berth_reference AS
SELECT
    zone_id AS berth_id,
    zone_name AS berth_name,
    port_id,
    geometry,
    ST_GeometryType(geometry) AS geometry_type
FROM reference_features
WHERE zone_type = 'berth'
  AND geometry IS NOT NULL
  AND ST_IsValid(geometry)
  AND ST_GeometryType(geometry) IN ('POINT', 'MULTILINESTRING');

CREATE TABLE berth_candidate_pings AS
WITH points AS (
    SELECT
        mmsi,
        observed_at_utc,
        latitude,
        longitude,
        ST_SetCRS(
            ST_Point(CAST(longitude AS DOUBLE), CAST(latitude AS DOUBLE)),
            'EPSG:4326'
        ) AS ping_point
    FROM ais_pings
    WHERE mmsi IS NOT NULL
      AND observed_at_utc IS NOT NULL
      AND latitude BETWEEN -90 AND 90
      AND longitude BETWEEN -180 AND 180
), projected AS (
    SELECT
        mmsi,
        observed_at_utc,
        latitude,
        longitude,
        ST_Transform(ping_point, 'EPSG:32611', true) AS ping_geom
    FROM points
), candidates AS (
    SELECT
        p.mmsi,
        p.observed_at_utc,
        p.latitude,
        p.longitude,
        b.berth_id,
        b.berth_name,
        b.port_id,
        b.geometry_type,
        ST_Distance(
            p.ping_geom,
            ST_Transform(ST_SetCRS(b.geometry, 'EPSG:4326'), 'EPSG:32611', true)
        ) AS distance_m
    FROM projected AS p
    CROSS JOIN berth_reference AS b
)
SELECT *
FROM candidates
WHERE distance_m <= 200.0;

CREATE TABLE berth_events AS
WITH nearest AS (
    SELECT *
    FROM berth_candidate_pings
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY mmsi, observed_at_utc
        ORDER BY distance_m, berth_id
    ) = 1
), ordered AS (
    SELECT
        *,
        LAG(observed_at_utc) OVER (
            PARTITION BY mmsi, berth_id
            ORDER BY observed_at_utc
        ) AS previous_time
    FROM nearest
), flagged AS (
    SELECT
        *,
        CASE
            WHEN previous_time IS NULL THEN 1
            WHEN observed_at_utc - previous_time > INTERVAL '30 minutes' THEN 1
            ELSE 0
        END AS new_event
    FROM ordered
), numbered AS (
    SELECT
        *,
        SUM(new_event) OVER (
            PARTITION BY mmsi, berth_id
            ORDER BY observed_at_utc
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS event_number
    FROM flagged
)
SELECT
    mmsi,
    berth_id,
    berth_name,
    port_id,
    MIN(observed_at_utc) AS entered_at,
    MAX(observed_at_utc) AS exited_at,
    EXTRACT(EPOCH FROM (MAX(observed_at_utc) - MIN(observed_at_utc))) AS duration_seconds,
    MIN(distance_m) AS minimum_distance_m,
    COUNT(*) AS ping_count
FROM numbered
GROUP BY mmsi, berth_id, berth_name, port_id, event_number;

SELECT COUNT(*) AS berth_reference_features FROM berth_reference;
SELECT COUNT(*) AS candidate_pings FROM berth_candidate_pings;
SELECT COUNT(*) AS berth_events FROM berth_events;
