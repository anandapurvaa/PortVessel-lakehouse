

with ordered_pings as (

    select
        record_hash,
        mmsi,
        imo,
        vessel_name,
        observed_at_utc,
        observed_date,
        latitude,
        longitude,
        sog_knots,
        nav_status,
        port_id,
        port_name,
        zone_id,
        zone_name,
        zone_type,
        ingestion_run_id,

        case
            when zone_type = 'anchorage' then 'anchorage'
            when zone_type = 'berth' then 'berth'
            when zone_type = 'port_area' then 'port_area'
            else 'outside'
        end as vessel_state,

        lag(observed_at_utc) over (
            partition by mmsi
            order by observed_at_utc, record_hash
        ) as previous_observed_at_utc,

        lag(
            case
                when zone_type = 'anchorage' then 'anchorage'
                when zone_type = 'berth' then 'berth'
                when zone_type = 'port_area' then 'port_area'
                else 'outside'
            end
        ) over (
            partition by mmsi
            order by observed_at_utc, record_hash
        ) as previous_vessel_state,

        lag(port_id) over (
            partition by mmsi
            order by observed_at_utc, record_hash
        ) as previous_port_id

    from `cloudprojects-506123`.`portvessel_dev_silver`.`int_ais_pings_geofenced`

),

state_breaks as (

    select
        *,

        case
            when previous_observed_at_utc is null then 1
            when timestamp_diff(
                observed_at_utc,
                previous_observed_at_utc,
                minute
            ) > 180 then 1
            when vessel_state != previous_vessel_state then 1
            when port_id != previous_port_id then 1
            else 0
        end as starts_new_state_interval

    from ordered_pings

),

state_groups as (

    select
        *,

        sum(starts_new_state_interval) over (
            partition by mmsi
            order by observed_at_utc, record_hash
            rows between unbounded preceding and current row
        ) as state_group_number

    from state_breaks

),

intervals as (

    select
        mmsi,
        any_value(imo) as imo,
        any_value(vessel_name) as vessel_name,

        any_value(port_id) as port_id,
        any_value(port_name) as port_name,
        any_value(zone_id) as zone_id,
        any_value(zone_name) as zone_name,
        any_value(vessel_state) as vessel_state,

        min(observed_at_utc) as state_started_at_utc,
        max(observed_at_utc) as state_ended_at_utc,
        date(min(observed_at_utc)) as state_start_date,

        count(*) as ping_count,

        round(avg(sog_knots), 2) as average_sog_knots,
        round(max(sog_knots), 2) as maximum_sog_knots,

        timestamp_diff(
            max(observed_at_utc),
            min(observed_at_utc),
            minute
        ) as observed_duration_minutes,

        max(ingestion_run_id) as latest_ingestion_run_id

    from state_groups
    group by
        mmsi,
        state_group_number

),

final as (

    select
        to_hex(sha256(concat(
            cast(mmsi as string), '|',
            cast(state_started_at_utc as string), '|',
            vessel_state, '|',
            coalesce(zone_id, 'OUTSIDE')
        ))) as vessel_state_interval_id,

        *,
        ping_count >= 2 as has_multiple_pings,
        observed_duration_minutes >= 10 as is_duration_observed

    from intervals

)

select * from final