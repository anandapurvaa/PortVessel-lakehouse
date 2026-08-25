
  
    

    create or replace table `cloudprojects-506123`.`portvessel_dev_marts`.`mart_vessel_risk`
      
    
    cluster by mmsi, operational_flag

    
    OPTIONS(
      description="""Vessel operational risk mart."""
    )
    as (
      

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
        loaded_at_utc,
        ingestion_run_id
    from `cloudprojects-506123`.`portvessel_dev_gold`.`vessel_operational_risk_flags`
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
        loaded_at_utc,
        ingestion_run_id
    from risk_data
)

select * from final
    );
  