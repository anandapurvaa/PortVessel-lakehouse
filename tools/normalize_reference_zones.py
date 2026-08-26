from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python normalize_reference_zones.py INPUT.geojson OUTPUT.geojson")

    source_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    data = json.loads(source_path.read_text(encoding="utf-8"))

    for index, feature in enumerate(data.get("features", []), start=1):
        properties = feature.setdefault("properties", {})
        object_id = properties.get("OBJECTID") or feature.get("id") or index
        name = properties.get("OBJNAM") or f"Operational zone {object_id}"
        info = properties.get("INFORM") or ""
        lowered = f"{name} {info}".lower()

        if "anchorage" in lowered:
            zone_type = "anchorage"
        elif "terminal" in lowered or "berth" in lowered:
            zone_type = "terminal"
        else:
            zone_type = "port"

        properties.update({
            "zone_id": f"la_lb_{object_id}",
            "zone_name": name,
            "zone_type": zone_type,
            "port_id": "los_angeles_long_beach",
            "effective_from": "2024-01-01",
            "effective_to": None,
            "source_name": "MarineCadastre operational anchorage reference",
            "source_url": "https://marinecadastre.gov/ais/",
            "license": "Verify current source terms before publication",
            "geometry_version": "2024-01-01"
        })

    data["name"] = "PortVessel Los Angeles Long Beach operational zones"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print({"status": "PASS", "features": len(data.get("features", [])), "output": str(output_path)})


if __name__ == "__main__":
    main()
