
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select vessel_state
from `cloudprojects-506123`.`portvessel_dev_silver`.`int_vessel_state_intervals`
where vessel_state is null



  
  
      
    ) dbt_internal_test