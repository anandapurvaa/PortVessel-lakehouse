
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select state_started_at_utc
from `cloudprojects-506123`.`portvessel_dev_silver`.`int_vessel_state_intervals`
where state_started_at_utc is null



  
  
      
    ) dbt_internal_test