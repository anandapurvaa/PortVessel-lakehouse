
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        port_call_quality_status as value_field,
        count(*) as n_records

    from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_port_calls`
    group by port_call_quality_status

)

select *
from all_values
where value_field not in (
    'observed','partial','invalid'
)



  
  
      
    ) dbt_internal_test