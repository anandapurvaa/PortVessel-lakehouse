
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        zone_type as value_field,
        count(*) as n_records

    from `cloudprojects-506123`.`portvessel_dev_silver`.`dim_geofences`
    group by zone_type

)

select *
from all_values
where value_field not in (
    'port_area','anchorage','berth'
)



  
  
      
    ) dbt_internal_test