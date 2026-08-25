
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select metric_date
from `cloudprojects-506123`.`portvessel_dev_gold`.`agg_port_congestion_daily`
where metric_date is null



  
  
      
    ) dbt_internal_test