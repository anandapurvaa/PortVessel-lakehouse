{{ config(
    materialized='table',
    dataset='portvessel_dev_gold',
    partition_by={
        "field": "arrival_date",
        "data_type": "date",
        "granularity": "day"
    },
    cluster_by=['port_id', 'mmsi']
) }}

with intervals as (

    select
        vessel_state_interval_id,
        mmsi,
        imo,
        vessel_name,
        port_id,
        port_name,
        zone_id,
        zone_name,
        vessel_state,
        state_started_at_utc,
        state_ended_at_utc,
        ping_count,
        observed_duration_minutes,
        has_multiple_pings,
        is_duration_observed,
        is_left_censored,
        is_right_censored,
        duration_observability_status,
        latest_ingestion_run_id
    from {{ ref('int_vessel_state_intervals') }}
    where port_id = 'USLAX'
      and vessel_state in ('port_area', 'anchorage', 'berth')

),

ordered_intervals as (

    select
        *,
        lag(state_ended_at_utc) over (
            partition by mmsi, port_id
            order by state_started_at_utc, vessel_state_interval_id
        ) as previous_state_ended_at_utc
    from intervals

),

visit_breaks as (

    select
        *,
        case
            when previous_state_ended_at_utc is null then 1
            when timestamp_diff(state_started_at_utc, previous_state_ended_at_utc, hour) > 6 then 1
            else 0
        end as starts_new_port_call
    from ordered_intervals

),

visit_groups as (

    select
        *,
        sum(starts_new_port_call) over (
            partition by mmsi, port_id
            order by state_started_at_utc, vessel_state_interval_id
            rows between unbounded preceding and current row
        ) as port_call_sequence
    from visit_breaks

),

port_calls as (

    select
        mmsi,
        any_value(imo) as imo,
        any_value(vessel_name) as vessel_name,
        port_id,
        any_value(port_name) as port_name,
        port_call_sequence,
        min(state_started_at_utc) as arrival_observed_at_utc,
        max(state_ended_at_utc) as departure_observed_at_utc,
        date(min(state_started_at_utc)) as arrival_date,
        min(if(vessel_state = 'anchorage', state_started_at_utc, null)) as anchorage_entered_at_utc,
        max(if(vessel_state = 'anchorage', state_ended_at_utc, null)) as anchorage_exited_at_utc,
        min(if(vessel_state = 'berth', state_started_at_utc, null)) as berth_entered_at_utc,
        max(if(vessel_state = 'berth', state_ended_at_utc, null)) as berth_exited_at_utc,
        count(*) as state_interval_count,
        sum(ping_count) as ping_count,
        countif(vessel_state = 'anchorage') as anchorage_interval_count,
        countif(vessel_state = 'berth') as berth_interval_count,
        sum(observed_duration_minutes) as observed_duration_minutes,
        logical_and(has_multiple_pings) as all_intervals_have_multiple_pings,
        logical_and(is_duration_observed) as all_intervals_duration_observed,
        logical_or(is_left_censored) as has_left_censored_interval,
        logical_or(is_right_censored) as has_right_censored_interval,
        logical_or(duration_observability_status = 'partial') as has_partial_interval,
        logical_or(
            vessel_state = 'anchorage'
            and duration_observability_status in ('left_censored', 'right_censored', 'both_censored', 'partial')
        ) as has_unobserved_anchorage_duration,
        logical_or(
            vessel_state = 'berth'
            and duration_observability_status in ('left_censored', 'right_censored', 'both_censored', 'partial')
        ) as has_unobserved_berth_duration,
        max(latest_ingestion_run_id) as latest_ingestion_run_id
    from visit_groups
    group by mmsi, port_id, port_call_sequence

),

final as (

    select
        to_hex(sha256(concat(
            cast(mmsi as string), '|',
            port_id, '|',
            cast(arrival_observed_at_utc as string)
        ))) as port_call_id,
        mmsi,
        imo,
        vessel_name,
        port_id,
        port_name,
        arrival_observed_at_utc,
        departure_observed_at_utc,
        arrival_date,
        anchorage_entered_at_utc,
        anchorage_exited_at_utc,
        berth_entered_at_utc,
        berth_exited_at_utc,
        case
            when anchorage_entered_at_utc is not null
             and anchorage_exited_at_utc is not null
             and not has_unobserved_anchorage_duration
                then timestamp_diff(anchorage_exited_at_utc, anchorage_entered_at_utc, minute)
        end as anchorage_wait_minutes,
        case
            when berth_entered_at_utc is not null
             and berth_exited_at_utc is not null
             and not has_unobserved_berth_duration
                then timestamp_diff(berth_exited_at_utc, berth_entered_at_utc, minute)
        end as berth_dwell_minutes,
        case
            when not has_left_censored_interval
             and not has_right_censored_interval
             and not has_partial_interval
                then timestamp_diff(departure_observed_at_utc, arrival_observed_at_utc, minute)
        end as port_duration_minutes,
        state_interval_count,
        ping_count,
        anchorage_interval_count,
        berth_interval_count,
        observed_duration_minutes,
        all_intervals_have_multiple_pings,
        all_intervals_duration_observed,
        has_left_censored_interval,
        has_right_censored_interval,
        has_partial_interval,
        has_unobserved_anchorage_duration,
        has_unobserved_berth_duration,
        case
            when arrival_observed_at_utc is null or departure_observed_at_utc is null then 'invalid'
            when has_left_censored_interval and has_right_censored_interval then 'both_censored'
            when has_left_censored_interval then 'left_censored'
            when has_right_censored_interval then 'right_censored'
            when has_partial_interval
              or not all_intervals_have_multiple_pings
              or not all_intervals_duration_observed then 'partial'
            else 'observed'
        end as port_call_quality_status,
        latest_ingestion_run_id,
        current_timestamp() as loaded_at_utc
    from port_calls

)

select * from final
