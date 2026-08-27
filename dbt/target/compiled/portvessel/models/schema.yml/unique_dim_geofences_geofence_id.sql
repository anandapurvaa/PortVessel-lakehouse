
    
    

with dbt_test__target as (

  select geofence_id as unique_field
  from `cloudprojects-506123`.`portvessel_dev_silver`.`dim_geofences`
  where geofence_id is not null

)

select
    unique_field,
    count(*) as n_records

from dbt_test__target
group by unique_field
having count(*) > 1


