
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select observed_vessels
from `cloudprojects-506123`.`portvessel_dev_gold`.`agg_port_congestion_daily`
where observed_vessels is null



  
  
      
    ) dbt_internal_test