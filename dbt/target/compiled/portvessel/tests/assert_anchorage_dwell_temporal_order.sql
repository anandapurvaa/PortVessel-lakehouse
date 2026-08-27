select
  anchorage_dwell_id,
  mmsi,
  port_id,
  anchorage_entered_at_utc,
  anchorage_exited_at_utc
from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_anchorage_dwell`
where anchorage_exited_at_utc < anchorage_entered_at_utc