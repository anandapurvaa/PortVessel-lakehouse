
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select port_call_quality_status
from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_port_calls`
where port_call_quality_status is null



  
  
      
    ) dbt_internal_test