
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select zone_geography
from (select * from `cloudprojects-506123`.`portvessel_dev_silver`.`dim_geofences` where zone_type in ('port_area', 'anchorage')) dbt_subquery
where zone_geography is null



  
  
      
    ) dbt_internal_test