
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select
  port_call_id,
  mmsi,
  port_id,
  port_duration_minutes,
  anchorage_wait_minutes,
  berth_dwell_minutes
from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_port_calls`
where port_duration_minutes < 0
   or anchorage_wait_minutes < 0
   or berth_dwell_minutes < 0
  
  
      
    ) dbt_internal_test