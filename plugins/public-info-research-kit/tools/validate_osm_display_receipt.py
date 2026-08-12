#!/usr/bin/env python3
"""Validate bounded OpenStreetMap Standard screenshot/display receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "osm_standard_map_receipt.v1"
CAPTURE_MODES = {"human_viewport_screenshot", "bounded_manual_viewport_stitch"}
USAGE_MODES = {"internal_research", "customer_material"}


def validate(receipt: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(receipt.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    require(receipt.get("basemap_provider") == "OpenStreetMap Standard", "basemap_provider must be OpenStreetMap Standard")
    require(receipt.get("basemap_kind") == "standard_cartographic_not_satellite", "OSM Standard must not be labelled satellite imagery")
    require(receipt.get("capture_mode") in CAPTURE_MODES, "capture_mode must be bounded human-viewed screenshot or stitch")
    require(receipt.get("usage_mode") in USAGE_MODES, "invalid usage_mode")
    require(receipt.get("attribution_visible") is True, "visible OpenStreetMap attribution is required")
    attribution = str(receipt.get("attribution_text", ""))
    require("OpenStreetMap contributors" in attribution, "attribution_text must credit OpenStreetMap contributors")
    require(str(receipt.get("copyright_url", "")).startswith("https://www.openstreetmap.org/copyright"), "copyright_url is required")
    require(receipt.get("bulk_tile_downloaded") is False, "bulk tile downloading is forbidden")
    require(receipt.get("prefetch_executed") is False, "tile prefetch is forbidden")
    require(receipt.get("offline_tile_package_created") is False, "offline tile packages are forbidden")
    require(bool(receipt.get("screenshot_or_asset_pointer")), "screenshot_or_asset_pointer is required")
    require(bool(receipt.get("display_extent_or_scope")), "display_extent_or_scope is required")

    if receipt.get("customer_facing_map_ready") is True:
        require(receipt.get("usage_mode") == "customer_material", "customer-facing ready requires customer_material usage")
        require(receipt.get("spatial_evidence_ready") is True, "customer-facing ready requires spatial_evidence_ready")
        require(receipt.get("comparison_scope_clear") is True, "customer-facing ready requires clear comparison scope")
        require(receipt.get("labels_legible") is True, "customer-facing ready requires legible labels")
        require(receipt.get("label_collision_checked") is True, "customer-facing ready requires label collision check")

    return {
        "schema": "osm_standard_map_validation_receipt.v1",
        "status": "pass" if not errors else "fail",
        "passed": not errors,
        "error_count": len(errors),
        "errors": errors,
        "not_production": True,
        "map_service_called": False,
        "external_write_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    result = validate(receipt)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
