
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select observed_date
from `cloudprojects-506123`.`portvessel_dev_silver`.`int_ais_pings_geofenced`
where observed_date is null



  
  
      
    ) dbt_internal_test