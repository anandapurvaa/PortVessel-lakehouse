from pathlib import Path
import csv
import json
import polars as pl

root = Path("data/extracted/2024-12-28")
csv_files = list(root.rglob("*.csv"))

if not csv_files:
    raise FileNotFoundError(f"No CSV files found under {root}")

for path in csv_files:
    print(f"- {path} ({path.stat().st_size:,} bytes)")

csv_path = csv_files[0]
print(f"\nInspecting: {csv_path}")

with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
    reader = csv.reader(file)
    header = next(reader)
    print(f"\nColumn count: {len(header)}")
    print("Columns:")
    print(header)
    first_rows = [next(reader) for _ in range(5)]

print("\nFirst rows:")
for row in first_rows:
    print(row)

sample = pl.read_csv(
    csv_path,
    n_rows=100_000,
    has_header=True,
    infer_schema=False,
    encoding="utf8-lossy",
    truncate_ragged_lines=True,
    ignore_errors=True,
    quote_char='"',
)

print("\nSchema:")
print(sample.schema)
print("\nShape:")
print(sample.shape)
print("\nNull counts:")
print(sample.null_count())
print("\nSample rows:")
print(sample.head(5))

report = {
    "source_file": str(csv_path),
    "file_size_bytes": csv_path.stat().st_size,
    "sample_rows": sample.height,
    "header_columns": header,
    "polars_columns": sample.columns,
    "polars_column_count": len(sample.columns),
    "schema": {name: str(dtype) for name, dtype in sample.schema.items()},
    "null_counts": {
        name: int(value)
        for name, value in zip(sample.columns, sample.null_count().row(0))
    },
    "read_options": {
        "infer_schema": False,
        "encoding": "utf8-lossy",
        "truncate_ragged_lines": True,
        "ignore_errors": True,
    },
}

Path("reports").mkdir(exist_ok=True)
with open("reports/ais_2024_12_28_sample_profile.json", "w", encoding="utf-8") as file:
    json.dump(report, file, indent=2)

print("\nWrote reports/ais_2024_12_28_sample_profile.json")
