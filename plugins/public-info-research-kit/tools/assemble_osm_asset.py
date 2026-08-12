#!/usr/bin/env python3
"""Assemble a bounded local OSM screenshot into an attributed SVG; never fetch tiles."""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
from pathlib import Path
from typing import Any

from validate_osm_display_receipt import validate as validate_display_receipt


MAX_SOURCE_BYTES = 25 * 1024 * 1024
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}


def assemble(source_image: Path, display_receipt: dict[str, Any], output: Path, project_watermark: str | None) -> dict[str, Any]:
    errors: list[str] = []
    display_validation = validate_display_receipt(display_receipt)
    if not display_validation["passed"]:
        errors.extend(display_validation["errors"])
    if not source_image.is_file():
        errors.append("source image does not exist")
    size = source_image.stat().st_size if source_image.is_file() else 0
    if size <= 0:
        errors.append("source image is empty")
    if size > MAX_SOURCE_BYTES:
        errors.append("source image exceeds 25 MiB")
    mime = mimetypes.guess_type(source_image.name)[0] or ""
    if mime not in ALLOWED_MIME:
        errors.append("source image type must be PNG, JPEG, WebP, or SVG")
    if output.suffix.casefold() != ".svg":
        errors.append("output must use the .svg extension")
    if errors:
        return {
            "schema": "osm_asset_assembly_receipt.v1",
            "status": "fail",
            "errors": sorted(set(errors)),
            "network_accessed": False,
            "tile_downloaded": False,
            "output_written": False,
        }

    encoded = base64.b64encode(source_image.read_bytes()).decode("ascii")
    scope = html.escape(str(display_receipt["display_extent_or_scope"]))
    watermark = html.escape(project_watermark.strip()) if project_watermark and project_watermark.strip() else ""
    watermark_node = f'<text x="24" y="42" class="watermark">{watermark}</text>' if watermark else ""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1600" height="1000" viewBox="0 0 1600 1000" role="img" aria-label="OpenStreetMap bounded viewport: {scope}">
  <style>
    .attribution {{ font: 22px -apple-system, BlinkMacSystemFont, sans-serif; fill: #111; }}
    .watermark {{ font: 28px -apple-system, BlinkMacSystemFont, sans-serif; font-weight: 600; fill: #111; paint-order: stroke; stroke: white; stroke-width: 5px; }}
  </style>
  <rect width="1600" height="1000" fill="white"/>
  <image x="0" y="0" width="1600" height="950" preserveAspectRatio="xMidYMid meet" href="data:{mime};base64,{encoded}"/>
  {watermark_node}
  <rect x="0" y="950" width="1600" height="50" fill="white" fill-opacity="0.94"/>
  <a xlink:href="https://www.openstreetmap.org/copyright">
    <text x="1576" y="982" text-anchor="end" class="attribution">© OpenStreetMap contributors</text>
  </a>
</svg>
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    return {
        "schema": "osm_asset_assembly_receipt.v1",
        "status": "pass",
        "errors": [],
        "output_pointer": output.name,
        "source_pointer": source_image.name,
        "usage_mode": display_receipt["usage_mode"],
        "customer_facing_map_ready": display_receipt.get("customer_facing_map_ready") is True,
        "spatial_evidence_ready": display_receipt.get("spatial_evidence_ready") is True,
        "display_validation": "pass",
        "attribution_text": "© OpenStreetMap contributors",
        "attribution_visible_in_output": True,
        "network_accessed": False,
        "tile_downloaded": False,
        "prefetch_executed": False,
        "offline_tile_package_created": False,
        "output_written": True,
        "boundary": "Assembly preserves a display receipt; it does not create or validate spatial facts.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-image", type=Path, required=True)
    parser.add_argument("--display-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path)
    parser.add_argument("--project-watermark")
    args = parser.parse_args()
    display_receipt = json.loads(args.display_receipt.read_text(encoding="utf-8"))
    result = assemble(args.source_image, display_receipt, args.output, args.project_watermark)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.receipt_output:
        args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
        args.receipt_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
