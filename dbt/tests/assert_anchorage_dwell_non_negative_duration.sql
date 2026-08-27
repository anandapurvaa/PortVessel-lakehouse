select
  anchorage_dwell_id,
  mmsi,
  port_id,
  anchorage_dwell_minutes
from {{ ref('fct_anchorage_dwell') }}
where anchorage_dwell_minutes < 0
