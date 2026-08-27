
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select port_id
from `cloudprojects-506123`.`portvessel_dev_silver`.`dim_geofences`
where port_id is null



  
  
      
    ) dbt_internal_test