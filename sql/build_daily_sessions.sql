CREATE OR REPLACE TABLE vessel_state_episodes AS
WITH ordered AS (
    SELECT
        *,
        CAST(nav_status AS VARCHAR) AS vessel_state,
        LAG(observed_at_utc) OVER w AS previous_time,
        LAG(nav_status) OVER w AS previous_nav_status
    FROM enriched_pings
    WINDOW w AS (PARTITION BY mmsi ORDER BY observed_at_utc)
), flagged AS (
    SELECT
        *,
        CASE
            WHEN previous_time IS NULL THEN 1
            WHEN observed_at_utc - previous_time > INTERVAL '30 minutes' THEN 1
            WHEN nav_status IS DISTINCT FROM previous_nav_status THEN 1
            ELSE 0
        END AS new_episode
    FROM ordered
), numbered AS (
    SELECT
        *,
        SUM(new_episode) OVER (
            PARTITION BY mmsi
            ORDER BY observed_at_utc
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS episode_number
    FROM flagged
)
SELECT
    mmsi,
    vessel_state,
    MIN(observed_at_utc) AS episode_start,
    MAX(observed_at_utc) AS episode_end,
    COUNT(*) AS ping_count,
    EXTRACT(EPOCH FROM (MAX(observed_at_utc) - MIN(observed_at_utc))) AS duration_seconds,
    MIN(latitude) AS first_latitude,
    MIN(longitude) AS first_longitude,
    MAX(latitude) AS last_latitude,
    MAX(longitude) AS last_longitude,
    ANY_VALUE(port_id) AS port_id,
    ANY_VALUE(zone_type) AS zone_type,
    episode_number
FROM numbered
GROUP BY mmsi, vessel_state, episode_number;

SELECT COUNT(*) AS state_episodes FROM vessel_state_episodes;
