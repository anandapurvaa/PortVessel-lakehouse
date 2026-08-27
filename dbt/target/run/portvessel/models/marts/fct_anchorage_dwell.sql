
  
    

    create or replace table `cloudprojects-506123`.`portvessel_dev_gold`.`fct_anchorage_dwell`
      
    partition by entry_date
    cluster by port_id, mmsi

    
    OPTIONS(
      description="""Observed anchorage intervals derived from USLAX geofenced AIS pings."""
    )
    as (
      

with anchorage_intervals as (

    select
        vessel_state_interval_id,
        mmsi,
        imo,
        vessel_name,
        port_id,
        port_name,
        zone_id,
        zone_name,
        state_started_at_utc as anchorage_entered_at_utc,
        state_ended_at_utc as anchorage_exited_at_utc,
        state_start_date as entry_date,
        ping_count,
        observed_duration_minutes,
        has_multiple_pings,
        is_duration_observed,
        latest_ingestion_run_id
    from `cloudprojects-506123`.`portvessel_dev_silver`.`int_vessel_state_intervals`
    where vessel_state = 'anchorage'
      and port_id = 'USLAX'

),

final as (

    select
        to_hex(sha256(concat(
            cast(mmsi as string), '|',
            port_id, '|',
            cast(anchorage_entered_at_utc as string), '|',
            coalesce(zone_id, 'UNKNOWN')
        ))) as anchorage_dwell_id,

        mmsi,
        imo,
        vessel_name,
        port_id,
        port_name,
        zone_id,
        zone_name,

        anchorage_entered_at_utc,
        anchorage_exited_at_utc,
        entry_date,

        timestamp_diff(
            anchorage_exited_at_utc,
            anchorage_entered_at_utc,
            minute
        ) as anchorage_dwell_minutes,

        ping_count,
        observed_duration_minutes,
        has_multiple_pings,
        is_duration_observed,

        case
            when not has_multiple_pings then 'partial'
            when not is_duration_observed then 'partial'
            else 'observed'
        end as anchorage_dwell_quality_status,

        latest_ingestion_run_id,
        current_timestamp() as loaded_at_utc

    from anchorage_intervals

)

select * from final
    );
  