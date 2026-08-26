INSTALL spatial;
LOAD spatial;

DROP TABLE IF EXISTS port_calls;

CREATE TABLE port_calls AS
WITH zone_hits AS (
    SELECT
        mmsi,
        observed_at_utc,
        port_id,
        zone_type,
        zone_id
    FROM enriched_pings
    WHERE zone_id IS NOT NULL
      AND zone_type IN ('anchorage', 'restricted_area', 'berth')
), ordered AS (
    SELECT
        *,
        LAG(observed_at_utc) OVER w AS previous_time,
        LAG(port_id) OVER w AS previous_port
    FROM zone_hits
    WINDOW w AS (PARTITION BY mmsi, port_id ORDER BY observed_at_utc)
), flagged AS (
    SELECT
        *,
        CASE
            WHEN previous_time IS NULL THEN 1
            WHEN previous_port IS DISTINCT FROM port_id THEN 1
            WHEN observed_at_utc - previous_time > INTERVAL '30 minutes' THEN 1
            ELSE 0
        END AS new_call
    FROM ordered
), numbered AS (
    SELECT
        *,
        SUM(new_call) OVER (
            PARTITION BY mmsi, port_id
            ORDER BY observed_at_utc
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS call_number
    FROM flagged
)
SELECT
    mmsi,
    port_id,
    MIN(observed_at_utc) AS arrival_time,
    MAX(observed_at_utc) AS departure_time,
    EXTRACT(EPOCH FROM (MAX(observed_at_utc) - MIN(observed_at_utc))) AS visit_duration_seconds,
    COUNT(*) AS zone_ping_count,
    COUNT(DISTINCT zone_id) AS zones_used,
    COUNT(*) FILTER (WHERE zone_type = 'anchorage') AS anchorage_pings,
    COUNT(*) FILTER (WHERE zone_type = 'restricted_area') AS restricted_area_pings,
    COUNT(*) FILTER (WHERE zone_type = 'berth') AS berth_pings,
    CASE
        WHEN COUNT(*) FILTER (WHERE zone_type = 'berth') > 0 THEN 'berth_candidate'
        WHEN COUNT(*) FILTER (WHERE zone_type = 'anchorage') > 0 THEN 'anchorage_only'
        ELSE 'restricted_area_only'
    END AS call_status
FROM numbered
GROUP BY mmsi, port_id, call_number;

SELECT COUNT(*) AS port_calls FROM port_calls;
SELECT call_status, COUNT(*) AS calls FROM port_calls GROUP BY call_status ORDER BY call_status;
