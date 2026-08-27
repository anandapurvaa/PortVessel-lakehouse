{{ config(
    materialized='table',
    dataset='portvessel_dev_gold',
    partition_by={
        "field": "metric_date",
        "data_type": "date",
        "granularity": "day"
    },
    cluster_by=['port_id']
) }}

with port_calls as (

    select *
    from {{ ref('fct_port_calls') }}
    where port_id = 'USLAX'

),

daily as (

    select
        arrival_date as metric_date,
        port_id,
        any_value(port_name) as port_name,

        -- All detected in-port sequences, including incomplete boundary calls.
        count(*) as detected_port_calls,
        count(distinct mmsi) as detected_vessels,

        -- Fully observed call sample eligible for arrival-to-departure duration KPIs.
        countif(port_duration_minutes is not null) as complete_port_calls,
        countif(port_call_quality_status = 'observed') as observed_port_calls,
        countif(port_call_quality_status = 'partial') as partial_calls,
        countif(port_call_quality_status = 'left_censored') as left_censored_calls,
        countif(port_call_quality_status = 'right_censored') as right_censored_calls,
        countif(port_call_quality_status = 'both_censored') as both_censored_calls,
        countif(port_call_quality_status = 'invalid') as invalid_calls,

        -- Zone dwell samples can remain valid even if the entire port call is censored.
        countif(anchorage_wait_minutes is not null)
            as port_calls_with_observed_anchorage_wait,
        countif(berth_dwell_minutes is not null)
            as port_calls_with_observed_berth_proximity_dwell,

        approx_quantiles(port_duration_minutes, 100)[safe_offset(50)]
            as median_port_duration_minutes,
        approx_quantiles(port_duration_minutes, 100)[safe_offset(90)]
            as p90_port_duration_minutes,
        round(avg(port_duration_minutes), 1)
            as mean_port_duration_minutes,

        approx_quantiles(anchorage_wait_minutes, 100)[safe_offset(50)]
            as median_anchorage_wait_minutes,
        approx_quantiles(anchorage_wait_minutes, 100)[safe_offset(90)]
            as p90_anchorage_wait_minutes,
        round(avg(anchorage_wait_minutes), 1)
            as mean_anchorage_wait_minutes,

        approx_quantiles(berth_dwell_minutes, 100)[safe_offset(50)]
            as median_berth_proximity_dwell_minutes,
        approx_quantiles(berth_dwell_minutes, 100)[safe_offset(90)]
            as p90_berth_proximity_dwell_minutes,
        round(avg(berth_dwell_minutes), 1)
            as mean_berth_proximity_dwell_minutes,

        max(latest_ingestion_run_id) as ingestion_run_id
    from port_calls
    group by metric_date, port_id

),

final as (

    select
        *,
        current_timestamp() as loaded_at_utc
    from daily

)

select * from final
