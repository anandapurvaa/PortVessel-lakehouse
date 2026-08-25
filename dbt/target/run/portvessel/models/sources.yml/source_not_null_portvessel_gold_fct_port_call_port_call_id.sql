
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select port_call_id
from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_port_call`
where port_call_id is null



  
  
      
    ) dbt_internal_test