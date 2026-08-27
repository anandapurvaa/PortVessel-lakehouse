
    
    



select berth_line_geography
from (select * from `cloudprojects-506123`.`portvessel_dev_silver`.`dim_geofences` where zone_type = 'berth') dbt_subquery
where berth_line_geography is null


