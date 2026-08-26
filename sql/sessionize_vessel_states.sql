CREATE OR REPLACE TABLE vessel_state_sessions AS
WITH ordered AS (
    SELECT
        *,
        nav_status AS current_state,
        LAG(nav_status) OVER (
            PARTITION BY mmsi
            ORDER BY observed_at_utc
        ) AS previous_state
    FROM enriched_pings
), flagged AS (
    SELECT
        *,
        CASE
            WHEN previous_state IS NULL OR current_state IS DISTINCT FROM previous_state THEN 1
            ELSE 0
        END AS state_change
    FROM ordered
), grouped AS (
    SELECT
        *,
        SUM(state_change) OVER (
            PARTITION BY mmsi
            ORDER BY observed_at_utc
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS session_number
    FROM flagged
)
SELECT
    * EXCLUDE (current_state, previous_state, state_change, session_number),
    current_state AS vessel_state,
    session_number
FROM grouped;

SELECT vessel_state, COUNT(*) AS sessions
FROM vessel_state_sessions
GROUP BY vessel_state
ORDER BY vessel_state;
