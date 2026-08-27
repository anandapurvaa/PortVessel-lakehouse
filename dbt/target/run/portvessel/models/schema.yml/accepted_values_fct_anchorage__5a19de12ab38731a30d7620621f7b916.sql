
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        anchorage_dwell_quality_status as value_field,
        count(*) as n_records

    from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_anchorage_dwell`
    group by anchorage_dwell_quality_status

)

select *
from all_values
where value_field not in (
    'observed','partial'
)



  
  
      
    ) dbt_internal_test