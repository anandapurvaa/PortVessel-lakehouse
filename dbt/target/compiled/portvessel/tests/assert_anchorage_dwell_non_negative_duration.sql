select
  anchorage_dwell_id,
  mmsi,
  port_id,
  anchorage_dwell_minutes
from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_anchorage_dwell`
where anchorage_dwell_minutes < 0