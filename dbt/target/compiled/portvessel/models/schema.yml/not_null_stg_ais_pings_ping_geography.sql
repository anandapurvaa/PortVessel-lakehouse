
    
    



select ping_geography
from (select * from `cloudprojects-506123`.`portvessel_dev_silver`.`stg_ais_pings` where is_analytics_eligible) dbt_subquery
where ping_geography is null


