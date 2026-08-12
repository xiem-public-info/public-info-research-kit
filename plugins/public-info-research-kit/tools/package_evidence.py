#!/usr/bin/env python3
"""Create a deterministic local evidence envelope without changing evidence classes."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from validate_public_evidence import validate


def package(draft: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    result = copy.deepcopy(draft)
    result["schema"] = "public_evidence_envelope.v1"
    result.setdefault("package_id", "pending")
    canonical = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    result["package_id"] = "evidence-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    receipt = validate(result)
    receipt["input_item_count"] = len(draft.get("items") or [])
    receipt["output_item_count"] = len(result.get("items") or [])
    receipt["input_evidence_classes"] = [item.get("evidence_class") for item in draft.get("items") or []]
    receipt["output_evidence_classes"] = [item.get("evidence_class") for item in result.get("items") or []]
    receipt["evidence_class_changed"] = receipt["input_evidence_classes"] != receipt["output_evidence_classes"]
    if receipt["evidence_class_changed"]:
        receipt["status"] = "fail"
        receipt["errors"].append("packager changed an evidence class")
        receipt["error_count"] = len(receipt["errors"])
    return result, receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    draft = json.loads(args.input.read_text(encoding="utf-8"))
    envelope, receipt = package(draft)
    if receipt["status"] == "pass":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
