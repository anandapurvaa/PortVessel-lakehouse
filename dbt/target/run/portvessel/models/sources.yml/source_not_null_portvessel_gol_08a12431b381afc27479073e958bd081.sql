
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select arrival_observed_at_utc
from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_port_call`
where arrival_observed_at_utc is null



  
  
      
    ) dbt_internal_test