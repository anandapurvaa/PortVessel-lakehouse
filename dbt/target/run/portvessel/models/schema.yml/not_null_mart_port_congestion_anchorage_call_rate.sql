
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select anchorage_call_rate
from `cloudprojects-506123`.`portvessel_dev_marts`.`mart_port_congestion`
where anchorage_call_rate is null



  
  
      
    ) dbt_internal_test