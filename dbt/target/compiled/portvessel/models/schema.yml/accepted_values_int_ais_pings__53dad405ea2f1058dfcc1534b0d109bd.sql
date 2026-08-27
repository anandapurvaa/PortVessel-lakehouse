
    
    

with all_values as (

    select
        zone_type as value_field,
        count(*) as n_records

    from `cloudprojects-506123`.`portvessel_dev_silver`.`int_ais_pings_geofenced`
    group by zone_type

)

select *
from all_values
where value_field not in (
    'port_area','anchorage','berth','outside'
)


