from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "reference" / "los_angeles" / "berths.geojson"
OUTPUT = ROOT / "dbt" / "seeds" / "uslax_berth_lines.csv"
SOURCE_URL = "https://data.lacity.org/City-Infrastructure-Service-Requests/Berth-Lines/9r7y-tdse"


def wkt_position(position: list[float]) -> str:
    return f"{position[0]:.12f} {position[1]:.12f}"


def wkt_linestring(coordinates: list[list[float]]) -> str:
    return "(" + ", ".join(wkt_position(point) for point in coordinates) + ")"


def geometry_to_wkt(geometry: dict) -> str | None:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None
    if geometry_type == "LineString":
        return "LINESTRING " + wkt_linestring(coordinates)
    if geometry_type == "MultiLineString":
        return "MULTILINESTRING (" + ", ".join(wkt_linestring(line) for line in coordinates) + ")"
    return None


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    payload = json.loads(source_bytes)
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()

    rows = []
    for feature in payload.get("features", []):
        geometry_wkt = geometry_to_wkt(feature.get("geometry") or {})
        if geometry_wkt is None:
            continue
        properties = feature.get("properties") or {}
        berth_num = str(properties.get("berth_num") or "").strip()
        source_id = str(properties.get(":id") or "").strip()
        source_version = str(properties.get(":version") or "").strip()
        if not berth_num:
            berth_num = source_id or f"UNNAMED_{len(rows) + 1}"
        berth_key = hashlib.sha256(f"USLAX|{berth_num}|{geometry_wkt}".encode()).hexdigest()[:24]
        rows.append({
            "geofence_id": f"USLAX_BERTH_{berth_key}",
            "port_id": "USLAX",
            "port_name": "Port of Los Angeles",
            "zone_id": f"USLAX_BERTH_{berth_key}",
            "zone_name": f"Berth proximity: {berth_num}",
            "zone_type": "berth_line",
            "berth_number": berth_num,
            "geometry_wkt": geometry_wkt,
            "geometry_source": "City of Los Angeles Open Data: Berth Lines",
            "geometry_source_url": SOURCE_URL,
            "geometry_version": source_version or "downloaded_geojson",
            "source_feature_id": source_id,
            "source_sha256": source_sha256,
            "source_retrieved_at_utc": retrieved_at,
            "effective_from": "",
            "effective_to": "",
            "is_active": "true",
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else [
        "geofence_id", "port_id", "port_name", "zone_id", "zone_name", "zone_type",
        "berth_number", "geometry_wkt", "geometry_source", "geometry_source_url",
        "geometry_version", "source_feature_id", "source_sha256", "source_retrieved_at_utc",
        "effective_from", "effective_to", "is_active",
    ]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} berth lines to {OUTPUT}")
    print(f"Source SHA-256: {source_sha256}")


if __name__ == "__main__":
    main()
