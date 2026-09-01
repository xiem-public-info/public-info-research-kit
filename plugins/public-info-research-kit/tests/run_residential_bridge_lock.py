#!/usr/bin/env python3
"""Offline mutation fixtures for the residential bridge lock."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "bridges/residential-v0.2/consumer-contract-lock.v0.2.json"
MODULE_PATH = ROOT / "tools/validate_residential_bridge.py"
SPEC = importlib.util.spec_from_file_location("validate_residential_bridge", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def check(case_id: str, payload: dict, expected: bool, error_contains: str | None = None) -> dict:
    receipt = MODULE.validate(payload)
    matched = True if error_contains is None else any(error_contains in error for error in receipt["errors"])
    return {"case_id": case_id, "expected_passed": expected, "actual_passed": receipt["passed"], "passed": receipt["passed"] is expected and matched}


def main() -> int:
    golden = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    cases = [check("frozen_bridge_lock", golden, True)]
    row = copy.deepcopy(golden)
    row["producer"]["sha256"] = "0" * 64
    cases.append(check("producer_hash_drift_rejected", row, False, "producer schema hash mismatch"))
    row = copy.deepcopy(golden)
    row["consumer"]["contracts"][1]["$id"] = row["consumer"]["contracts"][0]["$id"]
    cases.append(check("duplicate_consumer_id_rejected", row, False, "duplicated"))
    row = copy.deepcopy(golden)
    row["consumer"]["contracts"][0]["sha256"] = "not-a-hash"
    cases.append(check("invalid_consumer_hash_rejected", row, False, "hash is invalid"))
    row = copy.deepcopy(golden)
    row["consumer"]["contracts"][0]["path"] = "/tmp/private.schema.json"
    cases.append(check("absolute_consumer_path_rejected", row, False, "path must be relative"))
    row = copy.deepcopy(golden)
    row["conformance"]["consumer_validated_producer_fixture"] = False
    cases.append(check("one_way_conformance_rejected", row, False, "bidirectional"))
    row = copy.deepcopy(golden)
    row["boundaries"]["upstream_fulfilled_equals_downstream_accepted"] = True
    cases.append(check("fulfilled_equals_accepted_rejected", row, False, "boundaries"))

    report = {
        "schema": "residential_bridge_lock_fixture_report.v0.2",
        "status": "pass" if all(row["passed"] for row in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not row["passed"] for row in cases),
        "cases": cases,
        "network_accessed": False,
        "platform_opened": False,
        "external_write_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
