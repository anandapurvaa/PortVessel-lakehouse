
  
    

    create or replace table `cloudprojects-506123`.`portvessel_dev_silver`.`int_ais_pings_geofenced`
      
    partition by observed_date
    cluster by port_id, zone_type, mmsi

    
    OPTIONS()
    as (
      

with pings as (

    select *
    from `cloudprojects-506123`.`portvessel_dev_silver`.`stg_ais_pings`
    where is_analytics_eligible = true

    

),

candidate_matches as (

    select
        p.record_hash,
        g.geofence_id,
        g.port_id,
        g.port_name,
        g.zone_id,
        g.zone_name,
        g.zone_type,
        g.berth_number,

        row_number() over (
            partition by p.record_hash
            order by
                case g.zone_type
                    when 'berth' then 1
                    when 'anchorage' then 2
                    when 'port_area' then 3
                    else 99
                end,
                g.geofence_id
        ) as zone_rank

    from pings p
    inner join `cloudprojects-506123`.`portvessel_dev_silver`.`dim_geofences` g
        on (
            g.zone_type = 'berth'
            and st_dwithin(
                g.berth_line_geography,
                p.ping_geography,
                g.proximity_threshold_m
            )
        )
        or (
            g.zone_type in ('anchorage', 'port_area')
            and p.longitude between g.min_longitude and g.max_longitude
            and p.latitude between g.min_latitude and g.max_latitude
            and st_contains(g.zone_geography, p.ping_geography)
        )

),

assigned_zone as (

    select
        record_hash,
        geofence_id,
        port_id,
        port_name,
        zone_id,
        zone_name,
        zone_type,
        berth_number
    from candidate_matches
    where zone_rank = 1

),

final as (

    select
        p.*,
        coalesce(z.port_id, 'OUTSIDE') as port_id,
        z.port_name,
        coalesce(z.zone_id, 'OUTSIDE') as zone_id,
        coalesce(z.zone_name, 'Outside configured geofences') as zone_name,
        coalesce(z.zone_type, 'outside') as zone_type,
        z.berth_number,
        z.geofence_id,
        z.geofence_id is not null as is_in_configured_geofence
    from pings p
    left join assigned_zone z
        using (record_hash)

)

select * from final
    );
  