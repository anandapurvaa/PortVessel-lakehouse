from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from google.cloud import bigquery

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")
DATASET = os.environ.get("BQ_DATASET", "portvessel_dev_staging")
TABLE = os.environ.get("BQ_TABLE", "ais_pings")
CONTRACT_PATH = os.environ.get("CONTRACT_PATH", "pipeline_contract.json")

TYPE_ALIASES = {
    "INTEGER": "INT64",
    "FLOAT": "FLOAT64",
    "BOOLEAN": "BOOL",
}


def canonical_type(value: str) -> str:
    return TYPE_ALIASES.get(value.upper(), value.upper())


def main() -> None:
    contract = json.loads(Path(CONTRACT_PATH).read_text(encoding="utf-8"))
    required = {
        item["name"]: (canonical_type(item["type"]), item["nullable"])
        for item in contract["required_columns"]
    }

    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    table = client.get_table(f"{PROJECT_ID}.{DATASET}.{TABLE}")
    actual = {
        field.name: (canonical_type(field.field_type), field.mode != "REQUIRED")
        for field in table.schema
    }

    missing = {
        name: expected
        for name, expected in required.items()
        if name not in actual
    }
    type_mismatches = {
        name: {"expected": expected[0], "actual": actual[name][0]}
        for name, expected in required.items()
        if name in actual and expected[0] != actual[name][0]
    }
    nullability_mismatches = {
        name: {"expected_nullable": expected[1], "actual_nullable": actual[name][1]}
        for name, expected in required.items()
        if name in actual and expected[1] and not actual[name][1]
    }

    if missing or type_mismatches or nullability_mismatches:
        raise RuntimeError(
            json.dumps(
                {
                    "missing": missing,
                    "type_mismatches": type_mismatches,
                    "nullability_mismatches": nullability_mismatches,
                    "actual_schema": actual,
                },
                indent=2,
                default=str,
            )
        )

    schema_hash = hashlib.sha256(
        json.dumps(actual, sort_keys=True).encode("utf-8")
    ).hexdigest()
    print(
        json.dumps(
            {
                "status": "PASS",
                "table": f"{PROJECT_ID}.{DATASET}.{TABLE}",
                "schema_hash": schema_hash,
                "contract_version": contract["contract_version"],
            }
        )
    )


if __name__ == "__main__":
    main()
