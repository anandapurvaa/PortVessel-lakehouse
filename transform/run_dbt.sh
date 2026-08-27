#!/usr/bin/env sh
set -eu

cp /app/dbt/profiles.cloud.yml /app/dbt/profiles.yml

cd /app/dbt

dbt deps

dbt build --select \
  stg_ais_pings \
  dim_geofences \
  int_ais_pings_geofenced \
  int_vessel_state_intervals \
  fct_port_calls \
  fct_anchorage_dwell \
  agg_port_congestion_daily \
  path:tests