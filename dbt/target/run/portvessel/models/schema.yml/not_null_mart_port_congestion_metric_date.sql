
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select metric_date
from `cloudprojects-506123`.`portvessel_dev_marts`.`mart_port_congestion`
where metric_date is null



  
  
      
    ) dbt_internal_test