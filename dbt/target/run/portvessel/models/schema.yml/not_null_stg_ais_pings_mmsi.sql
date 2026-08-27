
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select mmsi
from (select * from `cloudprojects-506123`.`portvessel_dev_silver`.`stg_ais_pings` where is_analytics_eligible) dbt_subquery
where mmsi is null



  
  
      
    ) dbt_internal_test