
    
    

with dbt_test__target as (

  select mmsi as unique_field
  from `cloudprojects-506123`.`portvessel_dev_marts`.`mart_vessel_risk`
  where mmsi is not null

)

select
    unique_field,
    count(*) as n_records

from dbt_test__target
group by unique_field
having count(*) > 1


