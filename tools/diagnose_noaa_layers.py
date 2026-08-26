from __future__ import annotations

import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET


def xml_summary(path: Path) -> dict:
    try:
        root = ET.parse(path).getroot()
        text = " ".join((root.itertext()))
        return {
            "exists": True,
            "bytes": path.stat().st_size,
            "xml_root": root.tag,
            "text_preview": " ".join(text.split())[:500],
        }
    except Exception as exc:
        return {"exists": True, "error": repr(exc)}


def inspect_layer(path: Path) -> dict:
    result = {"layer": path.name, "files": {}}
    for suffix in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".shp.xml"]:
        candidate = path.with_suffix(suffix) if suffix != ".shp.xml" else Path(str(path) + ".xml")
        if candidate.exists():
            result["files"][candidate.name] = {
                "bytes": candidate.stat().st_size,
                "summary": xml_summary(candidate) if candidate.suffix == ".xml" else None,
            }
    try:
        import geopandas as gpd
        frame = gpd.read_file(path)
        result["shapefile"] = {
            "features": len(frame),
            "crs": str(frame.crs),
            "columns": list(frame.columns),
            "non_null_counts": {str(c): int(frame[c].notna().sum()) for c in frame.columns},
        }
    except Exception as exc:
        result["shapefile_error"] = repr(exc)
    return result


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    folder = root / "data/reference/noaa_harbour"
    layers = [
        "Harbour_Harbour_Area_Administrative_area.shp",
        "Harbour_Anchorage_Area.shp",
        "Harbour_Restricted_Area_area.shp",
        "Harbour_Berth_area.shp",
        "Harbour_Berth_line.shp",
        "Harbour_Berth_point.shp",
    ]
    report = []
    for filename in layers:
        path = folder / filename
        if path.exists():
            report.append(inspect_layer(path))
        else:
            report.append({"layer": filename, "error": "missing .shp"})
    output = root / "data/reference/noaa_harbour/diagnostic_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for item in report:
        shp = item.get("shapefile", {})
        print(item["layer"], "features=", shp.get("features"), "files=", ", ".join(item.get("files", {})))
    print(f"Wrote diagnostic report to {output}")


if __name__ == "__main__":
    main()
