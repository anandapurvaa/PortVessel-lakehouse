
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select record_hash
from `cloudprojects-506123`.`portvessel_dev_silver`.`int_ais_pings_geofenced`
where record_hash is null



  
  
      
    ) dbt_internal_test