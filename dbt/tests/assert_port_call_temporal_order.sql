select
  port_call_id,
  mmsi,
  port_id,
  arrival_observed_at_utc,
  departure_observed_at_utc
from {{ ref('fct_port_calls') }}
where departure_observed_at_utc < arrival_observed_at_utc
