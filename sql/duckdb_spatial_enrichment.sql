INSTALL spatial;
LOAD spatial;

CREATE OR REPLACE TABLE enriched_ais AS
SELECT
    a.*,
    z.zone_id,
    z.zone_name,
    z.zone_type,
    z.port_id,
    z.source_name AS zone_source_name,
    z.source_url AS zone_source_url
FROM ais_pings AS a
LEFT JOIN reference_features AS z
  ON ST_Intersects(
      z.geometry,
      ST_Point(CAST(a.longitude AS DOUBLE), CAST(a.latitude AS DOUBLE))
  );

CREATE OR REPLACE TABLE enriched_pings AS
SELECT * FROM enriched_ais;

SELECT zone_type, port_id, COUNT(*) AS ping_count
FROM enriched_pings
WHERE zone_id IS NOT NULL
GROUP BY zone_type, port_id
ORDER BY zone_type, port_id;
