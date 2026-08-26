DROP TABLE IF EXISTS daily_congestion;

CREATE TABLE daily_congestion AS
WITH anchorage AS (
    SELECT
        DATE(entered_at) AS observed_date,
        COUNT(*) AS anchorage_events,
        COUNT(DISTINCT mmsi) AS vessels_in_anchorage,
        MEDIAN(duration_seconds) AS median_anchorage_duration_seconds,
        QUANTILE_CONT(duration_seconds, 0.90) AS p90_anchorage_duration_seconds
    FROM anchorage_events
    GROUP BY DATE(entered_at)
), calls AS (
    SELECT
        DATE(arrival_time) AS observed_date,
        COUNT(*) AS port_calls,
        COUNT(DISTINCT mmsi) AS vessels_seen,
        MEDIAN(visit_duration_seconds) AS median_visit_duration_seconds
    FROM port_calls
    GROUP BY DATE(arrival_time)
), berth AS (
    SELECT
        DATE(entered_at) AS observed_date,
        COUNT(*) AS berth_events,
        COUNT(DISTINCT mmsi) AS vessels_near_berth,
        MEDIAN(duration_seconds) AS median_berth_duration_seconds
    FROM berth_events
    GROUP BY DATE(entered_at)
)
SELECT
    COALESCE(c.observed_date, a.observed_date, b.observed_date) AS observed_date,
    COALESCE(c.port_calls, 0) AS port_calls,
    COALESCE(c.vessels_seen, 0) AS vessels_seen,
    COALESCE(c.median_visit_duration_seconds, 0) AS median_visit_duration_seconds,
    COALESCE(a.anchorage_events, 0) AS anchorage_events,
    COALESCE(a.vessels_in_anchorage, 0) AS vessels_in_anchorage,
    COALESCE(a.median_anchorage_duration_seconds, 0) AS median_anchorage_duration_seconds,
    COALESCE(a.p90_anchorage_duration_seconds, 0) AS p90_anchorage_duration_seconds,
    COALESCE(b.berth_events, 0) AS berth_events,
    COALESCE(b.vessels_near_berth, 0) AS vessels_near_berth,
    COALESCE(b.median_berth_duration_seconds, 0) AS median_berth_duration_seconds
FROM calls c
FULL OUTER JOIN anchorage a USING (observed_date)
FULL OUTER JOIN berth b USING (observed_date);

SELECT * FROM daily_congestion ORDER BY observed_date;
