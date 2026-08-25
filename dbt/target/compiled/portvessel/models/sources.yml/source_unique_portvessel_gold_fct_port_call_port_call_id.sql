
    
    

with dbt_test__target as (

  select port_call_id as unique_field
  from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_port_call`
  where port_call_id is not null

)

select
    unique_field,
    count(*) as n_records

from dbt_test__target
group by unique_field
having count(*) > 1


