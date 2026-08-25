from pathlib import Path
from datetime import datetime, timezone
import duckdb

INPUT = (
    "data/processed/ais_scope/"
    "fct_anchorage_dwell_2024-12-27_2024-12-29_v3.parquet"
)

OUTPUT = (
    "data/processed/ais_scope/"
    "cloud/fct_anchorage_dwell_test.parquet"
)

SOURCE_OBJECT = "test/fct_anchorage_dwell_test.parquet"
RETRIEVED_AT = datetime.now(timezone.utc).isoformat()

Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/warehouse/portvessel.duckdb")

con.execute(f"""
    COPY (
        SELECT
            *,
            '{SOURCE_OBJECT}' AS source_object,
            '{RETRIEVED_AT}' AS source_retrieved_at_utc
        FROM read_parquet('{INPUT}')
    )
    TO '{OUTPUT}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print(f"Wrote {OUTPUT}")