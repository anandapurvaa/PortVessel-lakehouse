CREATE OR REPLACE TABLE anchorage_events AS
WITH marked AS (
    SELECT
        *,
        LAG(zone_id) OVER (PARTITION BY mmsi, zone_id ORDER BY observed_at_utc) AS previous_zone_id,
        LAG(observed_at_utc) OVER (PARTITION BY mmsi, zone_id ORDER BY observed_at_utc) AS previous_time
    FROM enriched_pings
    WHERE zone_type = 'anchorage'
      AND zone_id IS NOT NULL
), flagged AS (
    SELECT
        *,
        CASE
            WHEN previous_time IS NULL THEN 1
            WHEN observed_at_utc - previous_time > INTERVAL '30 minutes' THEN 1
            ELSE 0
        END AS new_event
    FROM marked
), grouped AS (
    SELECT
        *,
        SUM(new_event) OVER (
            PARTITION BY mmsi, zone_id
            ORDER BY observed_at_utc
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS event_number
    FROM flagged
)
SELECT
    mmsi,
    zone_id,
    zone_name,
    MIN(observed_at_utc) AS entered_at,
    MAX(observed_at_utc) AS exited_at,
    EXTRACT(EPOCH FROM (MAX(observed_at_utc) - MIN(observed_at_utc))) AS duration_seconds,
    COUNT(*) AS ping_count
FROM grouped
GROUP BY mmsi, zone_id, zone_name, event_number;

CREATE OR REPLACE TABLE daily_port_metrics AS
SELECT
    DATE(observed_at_utc) AS observed_date,
    COUNT(DISTINCT mmsi) AS vessels_seen,
    COUNT(*) FILTER (WHERE zone_type = 'anchorage') AS anchorage_pings,
    COUNT(*) FILTER (WHERE zone_type = 'restricted_area') AS restricted_area_pings,
    COUNT(DISTINCT zone_id) FILTER (WHERE zone_type = 'anchorage') AS anchorages_used
FROM enriched_pings
GROUP BY DATE(observed_at_utc);

SELECT * FROM daily_port_metrics ORDER BY observed_date;
