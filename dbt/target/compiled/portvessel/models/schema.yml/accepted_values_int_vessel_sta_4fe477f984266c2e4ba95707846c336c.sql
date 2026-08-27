
    
    

with all_values as (

    select
        vessel_state as value_field,
        count(*) as n_records

    from `cloudprojects-506123`.`portvessel_dev_silver`.`int_vessel_state_intervals`
    group by vessel_state

)

select *
from all_values
where value_field not in (
    'outside','port_area','anchorage','berth'
)


