
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select mmsi
from `cloudprojects-506123`.`portvessel_dev_gold`.`vessel_operational_risk_flags`
where mmsi is null



  
  
      
    ) dbt_internal_test