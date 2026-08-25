{{ config(
    materialized='table',
    dataset='portvessel_dev_marts',
    partition_by={
        "field": "metric_date",
        "data_type": "date",
        "granularity": "day"
    },
    cluster_by=['port_id']
) }}

with source_data as (
    select
        metric_date,
        port_id,
        port_name,
        observed_port_calls,
        observed_vessels,
        port_calls_with_anchorage,
        median_port_duration_minutes,
        p90_port_duration_minutes,
        mean_port_duration_minutes,
        observed_with_anchorage_calls,
        partial_calls,
        source_object,
        source_sha256,
        loaded_at_utc,
        ingestion_run_id
    from {{ source('portvessel_gold', 'agg_port_congestion_daily') }}
),

final as (
    select
        metric_date,
        port_id,
        port_name,
        observed_port_calls,
        observed_vessels,
        port_calls_with_anchorage,
        safe_divide(port_calls_with_anchorage, nullif(observed_port_calls, 0))
            as anchorage_call_rate,
        median_port_duration_minutes,
        p90_port_duration_minutes,
        mean_port_duration_minutes,
        observed_with_anchorage_calls,
        partial_calls,
        source_object,
        source_sha256,
        loaded_at_utc,
        ingestion_run_id
    from source_data
)

select * from final
