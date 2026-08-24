from pathlib import Path
import duckdb

INPUT = (
    "data/processed/ais_scope/"
    "fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet"
)
OUTPUT = Path("reports/persistent_anchorage_metrics.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

result = con.execute(f"""
    SELECT
        anchorage_object_id,
        COALESCE(anchorage_name, '[unnamed feature]') AS anchorage_name,
        COUNT(*) FILTER (
            WHERE eligible_for_persistent_metrics
        ) AS persistent_episode_count,
        COUNT(DISTINCT mmsi) FILTER (
            WHERE eligible_for_persistent_metrics
        ) AS persistent_vessel_count,
        MEDIAN(observed_dwell_minutes) FILTER (
            WHERE eligible_for_persistent_metrics
        ) AS median_persistent_dwell_minutes,
        QUANTILE_CONT(observed_dwell_minutes, 0.90) FILTER (
            WHERE eligible_for_persistent_metrics
        ) AS p90_persistent_dwell_minutes,
        AVG(observed_dwell_minutes) FILTER (
            WHERE eligible_for_persistent_metrics
        ) AS mean_persistent_dwell_minutes,
        MAX(observed_dwell_minutes) FILTER (
            WHERE eligible_for_persistent_metrics
        ) AS max_persistent_dwell_minutes,
        SUM(ping_count) FILTER (
            WHERE eligible_for_persistent_metrics
        ) AS persistent_pings
    FROM read_parquet('{INPUT}')
    GROUP BY 1, 2
    HAVING persistent_episode_count > 0
    ORDER BY persistent_episode_count DESC
""").fetchdf()

result.to_csv(OUTPUT, index=False)
print(result.to_string(index=False))
print(f"\nWrote {OUTPUT}")
