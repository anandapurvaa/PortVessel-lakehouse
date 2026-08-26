INSTALL spatial;
LOAD spatial;

DROP TABLE IF EXISTS daily_quality_report;

CREATE TABLE daily_quality_report AS
WITH input AS (
    SELECT
        DATE(observed_at_utc) AS observed_date,
        COUNT(*) AS input_rows,
        COUNT(DISTINCT mmsi) AS distinct_vessels,
        COUNT(*) FILTER (WHERE mmsi IS NULL) AS null_mmsi_rows,
        COUNT(*) FILTER (WHERE observed_at_utc IS NULL) AS null_timestamp_rows,
        COUNT(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) AS null_coordinate_rows,
        COUNT(*) FILTER (WHERE latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180) AS invalid_coordinate_rows,
        COUNT(*) FILTER (WHERE nav_status IS NULL) AS null_nav_status_rows
    FROM ais_pings
    GROUP BY DATE(observed_at_utc)
), matched AS (
    SELECT
        DATE(observed_at_utc) AS observed_date,
        COUNT(*) AS enriched_rows,
        COUNT(*) FILTER (WHERE zone_id IS NOT NULL) AS matched_zone_rows,
        COUNT(*) FILTER (WHERE zone_id IS NULL) AS unmatched_zone_rows
    FROM enriched_pings
    GROUP BY DATE(observed_at_utc)
), outputs AS (
    SELECT
        DATE(arrival_time) AS observed_date,
        COUNT(*) AS port_call_candidates
    FROM port_calls
    GROUP BY DATE(arrival_time)
)
SELECT
    i.observed_date,
    i.input_rows,
    i.distinct_vessels,
    i.null_mmsi_rows,
    i.null_timestamp_rows,
    i.null_coordinate_rows,
    i.invalid_coordinate_rows,
    i.null_nav_status_rows,
    m.enriched_rows,
    m.matched_zone_rows,
    m.unmatched_zone_rows,
    COALESCE(o.port_call_candidates, 0) AS port_call_candidates,
    current_timestamp AS report_created_at
FROM input i
LEFT JOIN matched m USING (observed_date)
LEFT JOIN outputs o USING (observed_date);

SELECT * FROM daily_quality_report ORDER BY observed_date;
