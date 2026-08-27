
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select zone_type
from `cloudprojects-506123`.`portvessel_dev_silver`.`int_ais_pings_geofenced`
where zone_type is null



  
  
      
    ) dbt_internal_test