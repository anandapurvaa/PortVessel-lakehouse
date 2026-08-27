
  
    

    create or replace table `cloudprojects-506123`.`portvessel_dev_gold`.`agg_port_congestion_daily`
      
    partition by metric_date
    cluster by port_id

    
    OPTIONS(
      description="""Daily observed operational congestion metrics for USLAX."""
    )
    as (
      

with port_calls as (

    select *
    from `cloudprojects-506123`.`portvessel_dev_gold`.`fct_port_calls`
    where port_id = 'USLAX'

),

daily as (

    select
        arrival_date as metric_date,
        port_id,
        any_value(port_name) as port_name,

        count(*) as observed_port_calls,
        count(distinct mmsi) as observed_vessels,

        countif(anchorage_wait_minutes is not null) as port_calls_with_anchorage,

        approx_quantiles(port_duration_minutes, 100)[offset(50)]
            as median_port_duration_minutes,

        approx_quantiles(port_duration_minutes, 100)[offset(90)]
            as p90_port_duration_minutes,

        round(avg(port_duration_minutes), 1)
            as mean_port_duration_minutes,

        countif(
            port_call_quality_status = 'observed'
            and anchorage_wait_minutes is not null
        ) as observed_with_anchorage_calls,

        countif(port_call_quality_status = 'partial') as partial_calls,

        max(latest_ingestion_run_id) as ingestion_run_id

    from port_calls
    group by
        metric_date,
        port_id

),

final as (

    select
        *,
        current_timestamp() as loaded_at_utc
    from daily

)

select * from final
    );
  