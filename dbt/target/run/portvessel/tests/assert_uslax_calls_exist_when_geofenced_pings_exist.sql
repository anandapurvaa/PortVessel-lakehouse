
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  with geofenced_ping_dates as (

  select distinct observed_date as metric_date
  from `cloudprojects-506123`.`portvessel_dev_silver`.`int_ais_pings_geofenced`
  where port_id = 'USLAX'

),

port_call_dates as (

  select
    arrival_date as metric_date,
    count(*) as port_call_count
  from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_port_calls`
  where port_id = 'USLAX'
  group by arrival_date

)

select
  p.metric_date,
  coalesce(c.port_call_count, 0) as port_call_count
from geofenced_ping_dates p
left join port_call_dates c
  using (metric_date)
where coalesce(c.port_call_count, 0) = 0
  
  
      
    ) dbt_internal_test