#!/usr/bin/env python3
"""Run D-291 spatial coordinate evidence positive and negative fixtures."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "spatial_coordinate_evidence_v2"
VALIDATOR_PATH = ROOT / "tools" / "validate_spatial_coordinate_evidence_v2.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_spatial_coordinate_evidence_v2", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_value(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def resolve_parent(data: Any, path: str) -> tuple[Any, str]:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current, parts[-1]


def apply_mutation(data: dict[str, Any], mutation: dict[str, Any]) -> None:
    op = mutation["op"]
    path = mutation["path"]
    if op == "append":
        target = resolve_value(data, path)
        if not isinstance(target, list):
            raise ValueError(f"append target is not a list: {path}")
        target.append(mutation["value"])
        return

    parent, key = resolve_parent(data, path)
    if op == "set":
        if isinstance(parent, list):
            parent[int(key)] = mutation["value"]
        else:
            parent[key] = mutation["value"]
        return
    if op == "delete":
        if isinstance(parent, list):
            del parent[int(key)]
        else:
            parent.pop(key, None)
        return
    raise ValueError(f"Unsupported mutation op: {op}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local spatial coordinate evidence v2 fixtures.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    schema = json.loads((FIXTURE_DIR / "schema.json").read_text(encoding="utf-8"))
    fixture_plan = json.loads((FIXTURE_DIR / "cases.json").read_text(encoding="utf-8"))
    validator = load_validator()

    object_role_enum = set(
        schema["properties"]["objects"]["items"]["properties"]["role"]["enum"]
    )
    distance_type_enum = set(
        schema["properties"]["distances"]["items"]["properties"]["distance_type"]["enum"]
    )
    schema_checks = {
        "malformed_payload_reports_invalid": validator.delivery_summary(None, validator.validate_contract(None))["delivery_status"] == "invalid",
        "schema_id_matches": schema.get("$id") == validator.SCHEMA_VERSION,
        "schema_version_const_matches": (
            schema["properties"]["schema_version"].get("const") == validator.SCHEMA_VERSION
        ),
        "caller_owns_object_set": (
            schema["properties"]["input_ownership"]["properties"]["object_set_owner"].get("const")
            == validator.OBJECT_SET_OWNER
        ),
        "single_centerpoint_model_matches": validator.PROJECT_LOCATION_MODEL == "single_map_marker_centerpoint",
        "object_roles_match": object_role_enum == validator.OBJECT_ROLES,
        "distance_types_match": distance_type_enum == validator.DISTANCE_TYPES,
        "downstream_rendering_owner_matches": (
            schema["properties"]["four_side_coordinate_evidence"]["properties"]["rendering_owner"].get("const")
            == validator.FOUR_SIDE_RENDERING_OWNER
        ),
        "downstream_outline_use_matches": (
            schema["properties"]["four_side_coordinate_evidence"]["properties"]["outline_use"].get("const")
            == validator.FOUR_SIDE_OUTLINE_USE
        ),
        "legacy_entrance_guard_present": "actual_entrance" in validator.FORBIDDEN_LEGACY_KEYS,
        "legacy_boundary_guard_present": "nearest_boundary" in validator.FORBIDDEN_LEGACY_KEYS,
        "osm_bulk_guards_present": all(
            schema["properties"]["osm_use"]["properties"][key].get("const") is False
            for key in ("bulk_tile_downloaded", "prefetch_executed", "offline_tile_package_created")
        ),
        "not_assessed_can_have_empty_basis": (
            "minItems"
            not in schema["properties"]["relative_access_findings"]["items"]["properties"]["basis_distance_ids"]
        ),
    }
    schema_ok = all(schema_checks.values())

    results: list[dict[str, Any]] = []
    for case in fixture_plan["cases"]:
        contract = copy.deepcopy(
            json.loads((FIXTURE_DIR / case["base"]).read_text(encoding="utf-8"))
        )
        for mutation in case.get("mutations", []):
            apply_mutation(contract, mutation)

        errors = validator.validate_contract(contract)
        actual_valid = not errors
        actual_codes = sorted({item["code"] for item in errors})
        expected_codes = sorted(case.get("expected_error_codes", []))
        expected_codes_seen = all(code in actual_codes for code in expected_codes)
        passed = actual_valid == case["expected_valid"] and expected_codes_seen
        if "expected_delivery_status" in case:
            delivery = validator.delivery_summary(contract, errors)
            passed = passed and delivery["delivery_status"] == case["expected_delivery_status"] and delivery["task_completion"] == "not_assessed_against_business_goal"
        results.append(
            {
                "case_id": case["case_id"],
                "expected_valid": case["expected_valid"],
                "actual_valid": actual_valid,
                "expected_error_codes": expected_codes,
                "actual_error_codes": actual_codes,
                "passed": passed,
            }
        )

    failed = [item for item in results if not item["passed"]]
    receipt = {
        "status": "pass" if schema_ok and not failed else "fail",
        "schema_version": validator.SCHEMA_VERSION,
        "schema_checks": schema_checks,
        "case_count": len(results),
        "positive_case_count": sum(1 for case in fixture_plan["cases"] if case["expected_valid"]),
        "negative_case_count": sum(1 for case in fixture_plan["cases"] if not case["expected_valid"]),
        "failure_count": len(failed) + (0 if schema_ok else 1),
        "results": results,
        "boundary": (
            "local D-291 contract only; no live map, route service, API, rendering, "
            "competitor decision or downstream write"
        ),
    }

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
