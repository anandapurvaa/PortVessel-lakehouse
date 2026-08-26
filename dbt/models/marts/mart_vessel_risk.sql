{{ config(
    materialized='table',
    dataset='portvessel_dev_marts',
    cluster_by=['mmsi', 'operational_flag']
) }}

with risk_data as (
    select
        mmsi,
        port_call_count,
        port_calls_with_anchorage,
        partial_port_calls,
        persistent_anchorage_episode_count,
        max_port_duration_minutes,
        mean_port_duration_minutes,
        max_persistent_anchorage_dwell_minutes,
        mean_persistent_anchorage_dwell_minutes,
        max_observation_gap_minutes,
        operational_flag,
        source_object,
        source_sha256,
        source_retrieved_at_utc,
        loaded_at_utc,
        ingestion_run_id,
        row_number() over (
            partition by mmsi
            order by loaded_at_utc desc, source_object desc, ingestion_run_id desc
        ) as row_number
    from {{ source('portvessel_gold', 'vessel_operational_risk_flags') }}
),

final as (
    select
        mmsi,
        port_call_count,
        port_calls_with_anchorage,
        safe_divide(
            port_calls_with_anchorage,
            nullif(port_call_count, 0)
        ) as anchorage_call_rate,
        partial_port_calls,
        persistent_anchorage_episode_count,
        max_port_duration_minutes,
        mean_port_duration_minutes,
        max_persistent_anchorage_dwell_minutes,
        mean_persistent_anchorage_dwell_minutes,
        max_observation_gap_minutes,
        operational_flag,
        source_object,
        source_sha256,
        source_retrieved_at_utc,
        loaded_at_utc,
        ingestion_run_id
    from risk_data
    where row_number = 1
)

select * from final
