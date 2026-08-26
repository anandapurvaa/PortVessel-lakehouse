from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-date", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    ais = root / "data/fixtures" / f"ais_{args.process_date}_sample.parquet"
    reference = root / "data/reference/normalized/reference_features.ndjson"
    if not ais.exists():
        raise FileNotFoundError(ais)
    if not reference.exists():
        raise FileNotFoundError(reference)
    record = {
        "process_date": args.process_date,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": [
            {"role": "ais", "path": str(ais), "bytes": ais.stat().st_size, "sha256": sha256(ais)},
            {"role": "reference", "path": str(reference), "bytes": reference.stat().st_size, "sha256": sha256(reference)},
        ],
    }
    output = root / "data/manifests" / f"manifest_{args.process_date}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
