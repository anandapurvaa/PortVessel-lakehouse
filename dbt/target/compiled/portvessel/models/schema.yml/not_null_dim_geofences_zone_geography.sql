
    
    



select zone_geography
from (select * from `cloudprojects-506123`.`portvessel_dev_silver`.`dim_geofences` where zone_type in ('port_area', 'anchorage')) dbt_subquery
where zone_geography is null


