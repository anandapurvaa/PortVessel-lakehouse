select
  anchorage_dwell_id,
  mmsi,
  port_id,
  anchorage_entered_at_utc,
  anchorage_exited_at_utc
from {{ ref('fct_anchorage_dwell') }}
where anchorage_exited_at_utc < anchorage_entered_at_utc
