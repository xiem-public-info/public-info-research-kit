#!/usr/bin/env python3
"""Offline positive and negative OpenStreetMap display-receipt fixtures."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/validate_osm_display_receipt.py"
SPEC = importlib.util.spec_from_file_location("validate_osm_display_receipt", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def base() -> dict:
    return {
        "schema": "osm_standard_map_receipt.v1",
        "basemap_provider": "OpenStreetMap Standard",
        "basemap_kind": "standard_cartographic_not_satellite",
        "capture_mode": "human_viewport_screenshot",
        "usage_mode": "customer_material",
        "attribution_visible": True,
        "attribution_text": "© OpenStreetMap contributors",
        "copyright_url": "https://www.openstreetmap.org/copyright",
        "bulk_tile_downloaded": False,
        "prefetch_executed": False,
        "offline_tile_package_created": False,
        "screenshot_or_asset_pointer": "bounded-map-example.png",
        "display_extent_or_scope": "某项目与三个比较对象的有限视窗",
        "spatial_evidence_ready": True,
        "comparison_scope_clear": True,
        "labels_legible": True,
        "label_collision_checked": True,
        "customer_facing_map_ready": True,
    }


def case(case_id: str, receipt: dict, expected: bool) -> dict:
    actual = MODULE.validate(receipt)["passed"]
    return {"case_id": case_id, "expected_passed": expected, "actual_passed": actual, "passed": actual is expected}


def main() -> int:
    valid = base()
    cases = [case("valid_customer_map", valid, True)]
    row = copy.deepcopy(valid)
    row["basemap_kind"] = "satellite_imagery"
    cases.append(case("osm_standard_is_not_satellite", row, False))
    row = copy.deepcopy(valid)
    row["attribution_visible"] = False
    cases.append(case("visible_attribution_required", row, False))
    row = copy.deepcopy(valid)
    row["bulk_tile_downloaded"] = True
    cases.append(case("bulk_tile_download_rejected", row, False))
    row = copy.deepcopy(valid)
    row["labels_legible"] = False
    cases.append(case("unreadable_labels_not_customer_ready", row, False))
    row = copy.deepcopy(valid)
    row["spatial_evidence_ready"] = False
    cases.append(case("display_cannot_replace_spatial_evidence", row, False))
    report = {
        "schema": "osm_display_receipt_fixture_report.v1",
        "status": "pass" if all(item["passed"] for item in cases) else "fail",
        "case_count": len(cases),
        "failure_count": sum(not item["passed"] for item in cases),
        "cases": cases,
        "map_service_called": False,
        "external_write_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
