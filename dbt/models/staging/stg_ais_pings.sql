{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='record_hash',
    dataset='portvessel_dev_silver',
    partition_by={
        "field": "observed_date",
        "data_type": "date",
        "granularity": "day"
    },
    cluster_by=['mmsi']
) }}

with raw as (

    select *
    from {{ source('portvessel_staging', 'ais_pings') }}

    {% if is_incremental() %}
      where ingested_at_utc >= (
        select coalesce(
          timestamp_sub(max(ingested_at_utc), interval 2 day),
          timestamp('1970-01-01')
        )
        from {{ this }}
      )
    {% endif %}

),

validated as (

    select
        cast(mmsi as int64) as mmsi,
        nullif(trim(imo), '') as imo,
        nullif(trim(call_sign), '') as call_sign,
        nullif(trim(vessel_name), '') as vessel_name,

        observed_at_utc,
        date(observed_at_utc) as observed_date,

        latitude,
        longitude,

        sog_knots,
        cog_degrees,
        heading_degrees,
        nav_status,
        vessel_type,
        draft_m,
        length_m,
        width_m,
        cargo_type,
        transceiver_class,

        source_file,
        source_uri,
        source_sha256,
        ingestion_run_id,
        ingested_at_utc,
        record_hash,
        quality_flag as raw_quality_flag,
        is_quarantined,

        mmsi between 100000000 and 999999999 as is_valid_mmsi,
        observed_at_utc is not null as is_valid_timestamp,
        latitude between -90 and 90
          and longitude between -180 and 180 as is_valid_coordinate,
        sog_knots is null or sog_knots between 0 and 70 as is_valid_sog,
        cog_degrees is null or cog_degrees between 0 and 360 as is_valid_cog,
        heading_degrees is null or heading_degrees between 0 and 511 as is_valid_heading

    from raw

),

deduplicated as (

    select *
    from validated
    qualify row_number() over (
        partition by record_hash
        order by ingested_at_utc desc, source_file desc
    ) = 1

),

final as (

    select
        mmsi,
        imo,
        call_sign,
        vessel_name,
        observed_at_utc,
        observed_date,
        latitude,
        longitude,

        case
            when is_valid_coordinate then st_geogpoint(longitude, latitude)
            else null
        end as ping_geography,

        sog_knots,
        cog_degrees,
        heading_degrees,
        nav_status,
        vessel_type,
        draft_m,
        length_m,
        width_m,
        cargo_type,
        transceiver_class,

        source_file,
        source_uri,
        source_sha256,
        ingestion_run_id,
        ingested_at_utc,
        record_hash,
        raw_quality_flag,
        is_quarantined,

        is_valid_mmsi,
        is_valid_timestamp,
        is_valid_coordinate,
        is_valid_sog,
        is_valid_cog,
        is_valid_heading,

        array_to_string(
            array(
                select flag
                from unnest([
                    if(is_quarantined, 'raw_quarantined', null),
                    if(not is_valid_mmsi, 'invalid_mmsi', null),
                    if(not is_valid_timestamp, 'missing_timestamp', null),
                    if(not is_valid_coordinate, 'invalid_coordinate', null),
                    if(not is_valid_sog, 'invalid_sog', null),
                    if(not is_valid_cog, 'invalid_cog', null),
                    if(not is_valid_heading, 'invalid_heading', null)
                ]) as flag
                where flag is not null
            ),
            '|'
        ) as quality_flags,

        not is_quarantined
          and is_valid_mmsi
          and is_valid_timestamp
          and is_valid_coordinate as is_analytics_eligible

    from deduplicated

)

select * from final