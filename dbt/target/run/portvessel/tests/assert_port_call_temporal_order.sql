
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select
  port_call_id,
  mmsi,
  port_id,
  arrival_observed_at_utc,
  departure_observed_at_utc
from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_port_calls`
where departure_observed_at_utc < arrival_observed_at_utc
  
  
      
    ) dbt_internal_test