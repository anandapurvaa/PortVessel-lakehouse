
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select anchorage_entered_at_utc
from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_anchorage_dwell`
where anchorage_entered_at_utc is null



  
  
      
    ) dbt_internal_test