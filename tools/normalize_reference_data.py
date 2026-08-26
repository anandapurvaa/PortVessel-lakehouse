from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REQUIRED = {
    "zone_id", "zone_name", "zone_type", "port_id",
    "effective_from", "effective_to", "source_name",
    "source_url", "license"
}


def load_json_features(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") == "FeatureCollection":
        return data.get("features", [])
    if isinstance(data, list):
        return [{
            "type": "Feature",
            "geometry": row.get("the_geom"),
            "properties": {k: v for k, v in row.items() if k != "the_geom"},
        } for row in data]
    raise ValueError(f"Unsupported JSON format: {path}")


def load_shapefile(path: Path):
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise SystemExit("Install GeoPandas first: python -m pip install geopandas") from exc
    frame = gpd.read_file(path)
    if frame.crs and frame.crs.to_epsg() != 4326:
        frame = frame.to_crs(4326)
    return json.loads(frame.to_json()).get("features", [])


def stable_id(feature, source_key: str, port_id: str, zone_type: str, index: int) -> str:
    props = feature.get("properties") or {}
    raw = props.get("OBJECTID") or props.get(":id") or feature.get("id")
    if raw in (None, ""):
        raw = index
    identity = f"{source_key}|{port_id}|{zone_type}|{raw}|{index}"
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:12]
    return f"{source_key}_{port_id}_{zone_type}_{digest}"


def normalize(features, source_key, port_id, zone_type, source_name, source_url):
    rows = []
    for index, feature in enumerate(features, start=1):
        props = dict(feature.get("properties") or {})
        name = props.get("OBJNAM") or props.get("berth_num") or f"{zone_type}_{index}"
        rows.append({
            "zone_id": stable_id(feature, source_key, port_id, zone_type, index),
            "zone_name": name,
            "zone_type": zone_type,
            "port_id": port_id,
            "geometry": feature.get("geometry"),
            "effective_from": "2024-01-01",
            "effective_to": None,
            "source_name": source_name,
            "source_url": source_url,
            "license": "Verify source terms before publication",
            "source_properties": props,
        })
    return rows


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python normalize_reference_data.py PROJECT_ROOT")
    root = Path(sys.argv[1]).resolve()
    rows = []

    json_specs = [
        (root / "data/reference/los_angeles/berths.geojson", "la", "los_angeles", "berth", "Port of Los Angeles Berth Lines", "https://data.lacity.org/d/9r7y-tdse"),
        (root / "data/reference/anchorage/zones.geojson", "anchorage", "los_angeles_long_beach", "anchorage", "Anchorage reference", "https://encdirect.noaa.gov/"),
    ]
    for path, source_key, port, kind, name, url in json_specs:
        if path.exists():
            rows.extend(normalize(load_json_features(path), source_key, port, kind, name, url))
        else:
            print(f"SKIP missing: {path}")

    harbour = root / "data/reference/noaa_harbour"
    harbour_specs = [
        ("Harbour_Harbour_Area_Administrative_area.shp", "port_boundary"),
        ("Harbour_Anchorage_Area.shp", "anchorage"),
        ("Harbour_Restricted_Area_area.shp", "restricted_area"),
        ("Harbour_Berth_area.shp", "berth"),
        ("Harbour_Berth_line.shp", "berth"),
        ("Harbour_Berth_point.shp", "berth"),
    ]
    for filename, kind in harbour_specs:
        path = harbour / filename
        if not path.exists():
            print(f"SKIP missing: {path}")
            continue
        features = load_shapefile(path)
        print(f"READ {filename}: {len(features)} features")
        rows.extend(normalize(features, "noaa", "los_angeles_long_beach", kind, f"NOAA ENC Harbour {kind}", "https://encdirect.noaa.gov/"))

    if not rows:
        raise RuntimeError("No reference features found")
    missing = REQUIRED - set(rows[0])
    if missing:
        raise RuntimeError(f"Missing normalized fields: {sorted(missing)}")
    if len({row["zone_id"] for row in rows}) != len(rows):
        raise RuntimeError("Normalization generated duplicate zone_id values")

    output = root / "data/reference/normalized/reference_features.ndjson"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    print(f"Wrote {len(rows)} features to {output}")


if __name__ == "__main__":
    main()
