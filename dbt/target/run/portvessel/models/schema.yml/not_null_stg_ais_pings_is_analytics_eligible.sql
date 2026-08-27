
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select is_analytics_eligible
from `cloudprojects-506123`.`portvessel_dev_silver`.`stg_ais_pings`
where is_analytics_eligible is null



  
  
      
    ) dbt_internal_test