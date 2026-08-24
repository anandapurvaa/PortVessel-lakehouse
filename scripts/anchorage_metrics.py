from pathlib import Path
import duckdb

INPUT = "data/processed/ais_scope/anchorage_episodes_2024-12-27_2024-12-29_v2.parquet"
OUTPUT = Path("reports/anchorage_metrics_2024-12-27_2024-12-29.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

query = f"""
    SELECT
        anchorage_object_id,
        COALESCE(anchorage_name, '[unnamed feature]') AS anchorage_name,
        COUNT(*) AS episode_count,
        COUNT(DISTINCT mmsi) AS vessel_count,
        SUM(CASE WHEN episode_quality = 'observed_continuous' THEN 1 ELSE 0 END)
            AS complete_episode_count,
        MEDIAN(observed_duration_minutes)
            FILTER (WHERE episode_quality = 'observed_continuous')
            AS median_complete_duration_minutes,
        QUANTILE_CONT(observed_duration_minutes, 0.90)
            FILTER (WHERE episode_quality = 'observed_continuous')
            AS p90_complete_duration_minutes,
        MAX(observed_duration_minutes)
            FILTER (WHERE episode_quality = 'observed_continuous')
            AS max_complete_duration_minutes,
        SUM(ping_count) AS total_pings
    FROM read_parquet('{INPUT}')
    GROUP BY 1, 2
    ORDER BY complete_episode_count DESC, episode_count DESC
"""

result = con.execute(query).fetchdf()
result.to_csv(OUTPUT, index=False)
print(result.to_string(index=False))
print(f"\nWrote {OUTPUT}")
