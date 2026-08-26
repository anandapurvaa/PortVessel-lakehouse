from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python reference_smoke_test.py PROJECT_ROOT")
    root = Path(sys.argv[1]).resolve()
    path = root / "data/reference/normalized/reference_features.ndjson"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    required = {"zone_id", "zone_name", "zone_type", "port_id", "geometry", "source_name", "source_url", "license"}
    assert rows, "No normalized features found"
    assert all(required <= set(row) for row in rows), "Required fields missing"
    assert all(row["geometry"] for row in rows), "Feature without geometry"
    types = sorted({row["zone_type"] for row in rows})
    ports = sorted({row["port_id"] for row in rows})
    print({"features": len(rows), "zone_types": types, "ports": ports, "status": "PASS"})


if __name__ == "__main__":
    main()
