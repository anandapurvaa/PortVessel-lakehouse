
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ping_geography
from (select * from `cloudprojects-506123`.`portvessel_dev_silver`.`stg_ais_pings` where is_analytics_eligible) dbt_subquery
where ping_geography is null



  
  
      
    ) dbt_internal_test