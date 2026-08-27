

with polygon_geofences as (

    select
        geofence_id,
        port_id,
        port_name,
        zone_id,
        zone_name,
        zone_type,
        cast(null as string) as berth_number,
        safe.st_geogfromtext(geometry_wkt) as zone_geography,
        cast(null as geography) as berth_line_geography,
        geometry_source,
        cast(null as string) as geometry_source_url,
        geometry_version,
        cast(null as string) as source_feature_id,
        cast(null as string) as source_sha256,
        cast(null as timestamp) as source_retrieved_at_utc,
        effective_from,
        effective_to,
        is_active,
        cast(null as int64) as proximity_threshold_m
    from `cloudprojects-506123`.`portvessel_dev`.`geofences`
    where is_active = true

),

berth_lines as (

    select
        geofence_id,
        port_id,
        port_name,
        zone_id,
        zone_name,
        'berth' as zone_type,
        berth_number,
        cast(null as geography) as zone_geography,
        safe.st_geogfromtext(geometry_wkt) as berth_line_geography,
        geometry_source,
        geometry_source_url,
        geometry_version,
        source_feature_id,
        source_sha256,
        source_retrieved_at_utc,
        effective_from,
        effective_to,
        is_active,
        75 as proximity_threshold_m
    from `cloudprojects-506123`.`portvessel_dev`.`uslax_berth_lines`
    where is_active = true

),

combined as (

    select * from polygon_geofences
    union all
    select * from berth_lines

),

final as (

    select
        *,
        case
            when zone_geography is not null then st_boundingbox(zone_geography).xmin
        end as min_longitude,
        case
            when zone_geography is not null then st_boundingbox(zone_geography).xmax
        end as max_longitude,
        case
            when zone_geography is not null then st_boundingbox(zone_geography).ymin
        end as min_latitude,
        case
            when zone_geography is not null then st_boundingbox(zone_geography).ymax
        end as max_latitude
    from combined
    where zone_geography is not null
       or berth_line_geography is not null

)

select * from final