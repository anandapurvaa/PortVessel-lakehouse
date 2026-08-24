from pathlib import Path
import csv
import json

input_path = Path(
    "data/extracted/2024-12-28/AIS_2024_12_28.csv"
)
report_path = Path(
    "reports/ais_2024_12_28_csv_shape_audit.json"
)

expected_fields = 17
rows_checked = 0
valid_width = 0
invalid_width = 0
width_counts = {}
examples = []

with input_path.open("r", encoding="utf-8-sig", newline="") as file:
    reader = csv.reader(file)
    header = next(reader)

    for line_number, row in enumerate(reader, start=2):
        rows_checked += 1
        width = len(row)
        width_counts[str(width)] = width_counts.get(str(width), 0) + 1

        if width == expected_fields:
            valid_width += 1
        else:
            invalid_width += 1
            if len(examples) < 10:
                examples.append({
                    "line_number": line_number,
                    "field_count": width,
                    "row_prefix": row[:5],
                })

report = {
    "input": str(input_path),
    "expected_fields": expected_fields,
    "header": header,
    "rows_checked": rows_checked,
    "valid_width_rows": valid_width,
    "invalid_width_rows": invalid_width,
    "field_count_distribution": width_counts,
    "examples": examples,
}

report_path.parent.mkdir(exist_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))