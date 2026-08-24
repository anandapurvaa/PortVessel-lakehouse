from pathlib import Path
import duckdb

PORT_CALLS = "data/processed/ais_scope/fct_port_call_2024-12-27_2024-12-29.parquet"
DWELL = "data/processed/ais_scope/fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet"
REPORT = Path("reports/port_call_audit.txt")
REPORT.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")
lines = []

def section(title, query):
    lines.append(f"\n## {title}\n")
    lines.append(con.execute(query).fetchdf().to_string(index=False))

section("Port call quality", f"""
    SELECT port_call_quality, COUNT(*) AS port_calls,
           COUNT(DISTINCT mmsi) AS vessels
    FROM read_parquet('{PORT_CALLS}')
    GROUP BY 1 ORDER BY 1
""")

section("Duration distribution", f"""
    SELECT
        COUNT(*) AS port_calls,
        MIN(observed_port_duration_minutes) AS min_minutes,
        MEDIAN(observed_port_duration_minutes) AS median_minutes,
        QUANTILE_CONT(observed_port_duration_minutes, 0.90) AS p90_minutes,
        MAX(observed_port_duration_minutes) AS max_minutes
    FROM read_parquet('{PORT_CALLS}')
""")

section("Anchorage versus no anchorage", f"""
    SELECT
        has_observed_anchorage,
        COUNT(*) AS port_calls,
        AVG(observed_port_duration_minutes) AS mean_duration_minutes
    FROM read_parquet('{PORT_CALLS}')
    GROUP BY 1 ORDER BY 1
""")

section("Long port calls", f"""
    SELECT
        mmsi, port_call_quality, arrival_observed_at_utc,
        departure_observed_at_utc, observed_port_duration_minutes,
        anchorage_features_observed, ping_count
    FROM read_parquet('{PORT_CALLS}')
    ORDER BY observed_port_duration_minutes DESC
    LIMIT 25
""")

section("Potential invalid durations", f"""
    SELECT COUNT(*) AS invalid_duration_rows
    FROM read_parquet('{PORT_CALLS}')
    WHERE departure_observed_at_utc < arrival_observed_at_utc
       OR observed_port_duration_minutes < 0
""")

REPORT.write_text("\n".join(lines), encoding="utf-8")
print("Wrote", REPORT)
print("\n".join(lines))
