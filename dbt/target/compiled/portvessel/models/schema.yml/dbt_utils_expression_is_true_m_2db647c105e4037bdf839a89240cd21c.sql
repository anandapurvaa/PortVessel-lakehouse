



select
    1
from `cloudprojects-506123`.`portvessel_dev_marts`.`mart_port_congestion`

where not(anchorage_call_rate between 0 and 1)

