from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd


def parse_date(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    return None if not text else date.fromisoformat(text)


def validate_ndjson(path: Path, contract: dict) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise RuntimeError(f"Geometry file is empty: {path}")
    required = set(contract["required_properties"]) | {"geometry"}
    missing = required - set(rows[0])
    if missing:
        raise RuntimeError(f"Missing properties: {sorted(missing)}")

    seen = {}
    for line_number, row in enumerate(rows, start=1):
        zone_id = row.get("zone_id")
        if zone_id in (None, ""):
            raise RuntimeError(f"Missing zone_id at NDJSON line {line_number}")
        if zone_id in seen:
            raise RuntimeError(f"Duplicate zone_id {zone_id!r} at lines {seen[zone_id]} and {line_number}")
        seen[zone_id] = line_number
        if row["zone_type"] not in contract["allowed_zone_types"]:
            raise RuntimeError(f"Unsupported zone_type: {row['zone_type']}")
        if not row["geometry"]:
            raise RuntimeError(f"Missing geometry: {zone_id}")
        parse_date(row.get("effective_from"))
        parse_date(row.get("effective_to"))

    print({"status": "PASS", "zones": len(rows), "format": "NDJSON", "file": str(path)})


def validate_vector(path: Path, contract: dict) -> None:
    zones = gpd.read_file(path)
    if zones.crs is None or zones.crs.to_epsg() != 4326:
        raise RuntimeError(f"Expected EPSG:4326, got {zones.crs}")
    if zones.empty:
        raise RuntimeError(f"Geometry file is empty: {path}")
    if not zones.geometry.geom_type.isin(contract["geometry_types"]).all():
        raise RuntimeError("Unsupported geometry type present")
    if not zones.geometry.is_valid.all() or zones.geometry.is_empty.any():
        raise RuntimeError("Invalid or empty geometries present")
    missing = set(contract["required_properties"]) - set(zones.columns)
    if missing:
        raise RuntimeError(f"Missing properties: {sorted(missing)}")
    if zones["zone_id"].isna().any() or zones["zone_id"].duplicated().any():
        raise RuntimeError("zone_id must be non-null and unique")
    if not zones["zone_type"].isin(contract["allowed_zone_types"]).all():
        raise RuntimeError("Unsupported zone_type present")
    print({"status": "PASS", "zones": len(zones), "crs": "EPSG:4326", "file": str(path)})


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python validate_geometry.py CONTRACT GEOJSON_OR_NDJSON")
    contract = json.loads(Path(sys.argv[1]).resolve().read_text(encoding="utf-8"))
    path = Path(sys.argv[2]).resolve()
    if path.suffix.lower() in {".ndjson", ".jsonl"}:
        validate_ndjson(path, contract)
    else:
        validate_vector(path, contract)


if __name__ == "__main__":
    main()
