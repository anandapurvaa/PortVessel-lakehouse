
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  



select
    1
from `cloudprojects-506123`.`portvessel_dev_marts`.`mart_vessel_risk`

where not(anchorage_call_rate between 0 and 1)


  
  
      
    ) dbt_internal_test