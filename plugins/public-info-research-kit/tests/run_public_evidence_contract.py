#!/usr/bin/env python3
"""Offline golden, rejection and packaging checks for public_evidence_envelope.v1."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
FIXTURES = ROOT / "tests/fixtures"
sys.path.insert(0, str(TOOLS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("validate_public_evidence", TOOLS / "validate_public_evidence.py")
PACKAGER = load_module("package_evidence", TOOLS / "package_evidence.py")


def get_parent(value: Any, path: list[Any], create: bool = False) -> tuple[Any, Any]:
    current = value
    for key in path[:-1]:
        if isinstance(key, int):
            current = current[key]
        else:
            if create and key not in current:
                current[key] = {}
            current = current[key]
    return current, path[-1]


def replace(value: Any, path: list[Any], replacement: Any, create: bool = False) -> None:
    parent, key = get_parent(value, path, create=create)
    parent[key] = replacement


def remove(value: Any, path: list[Any]) -> None:
    parent, key = get_parent(value, path)
    if isinstance(parent, list):
        parent.pop(key)
    else:
        parent.pop(key, None)


def main() -> int:
    golden_path = FIXTURES / "golden-tasks/golden_public_evidence_envelope.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    mutations = json.loads((FIXTURES / "negative-cases/public_evidence_mutations.json").read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []

    valid = VALIDATOR.validate(golden)
    cases.append(
        {
            "case_id": "golden_evidence_envelope",
            "expected_status": "pass",
            "actual_status": valid["status"],
            "passed": valid["status"] == "pass" and valid["negative_hit_count"] == 1 and valid["conflict_count"] == 1 and valid["gap_count"] == 1,
        }
    )

    stopped = copy.deepcopy(golden)
    stopped["upstream_status"] = "stopped"
    stopped["stop_reason"] = "触发明确安全停止线，停止当前渠道执行并保留已取得证据与缺口"
    stopped_receipt = VALIDATOR.validate(stopped)
    cases.append(
        {
            "case_id": "stopped_is_a_valid_upstream_state",
            "expected_status": "pass",
            "actual_status": stopped_receipt["status"],
            "passed": stopped_receipt["status"] == "pass" and stopped_receipt["upstream_status"] == "stopped",
        }
    )

    empty_enumerations = copy.deepcopy(golden)
    empty_enumerations["items"] = [
        item
        for item in empty_enumerations["items"]
        if item["evidence_class"] not in {"conflict", "gap"}
    ]
    empty_enumerations["conflicts"] = []
    empty_enumerations["gaps"] = []
    empty_enumerations["upstream_status"] = "fulfilled"
    empty_enumerations["query_execution"]["evidence_sufficiency_status"] = "sufficient"
    empty_enumerations["stop_reason"] = "达到请求方冻结的质量、数量与来源多样性条件"
    empty_receipt = VALIDATOR.validate(empty_enumerations)
    cases.append(
        {
            "case_id": "empty_conflicts_and_gaps_use_empty_arrays",
            "expected_status": "pass",
            "actual_status": empty_receipt["status"],
            "passed": empty_receipt["status"] == "pass" and empty_receipt["conflict_count"] == 0 and empty_receipt["gap_count"] == 0,
        }
    )

    for mutation in mutations["cases"]:
        payload = copy.deepcopy(golden)
        operation = mutation["operation"]
        if operation == "replace":
            replace(payload, mutation["path"], mutation["value"])
        elif operation == "add":
            replace(payload, mutation["path"], mutation["value"], create=True)
        elif operation == "remove":
            remove(payload, mutation["path"])
        elif operation == "multi_replace":
            for change in mutation["changes"]:
                replace(payload, change["path"], change["value"])
        else:
            raise ValueError(f"unknown mutation operation: {operation}")
        receipt = VALIDATOR.validate(payload)
        expected = mutation["expected_error_contains"]
        cases.append(
            {
                "case_id": mutation["case_id"],
                "expected_status": "fail",
                "actual_status": receipt["status"],
                "passed": receipt["status"] == "fail" and any(expected in error for error in receipt["errors"]),
            }
        )

    draft = copy.deepcopy(golden)
    draft["package_id"] = "pending"
    envelope, receipt = PACKAGER.package(draft)
    cases.append(
        {
            "case_id": "packager_preserves_classes_and_consumer_boundary",
            "expected_status": "pass",
            "actual_status": receipt["status"],
            "passed": (
                receipt["status"] == "pass"
                and receipt["evidence_class_changed"] is False
                and envelope["downstream_acceptance"]["status"] == "not_assessed"
                and envelope["negative_hits"] == golden["negative_hits"]
                and envelope["conflicts"] == golden["conflicts"]
                and envelope["gaps"] == golden["gaps"]
                and envelope["stop_reason"] == golden["stop_reason"]
            ),
        }
    )

    report = {
        "schema": "public_evidence_contract_fixture_report.v1",
        "status": "pass" if all(case["passed"] for case in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not case["passed"] for case in cases),
        "cases": cases,
        "network_accessed": False,
        "external_write_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
