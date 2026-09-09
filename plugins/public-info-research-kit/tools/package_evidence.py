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
from request_contract import make_binding


def package(draft: dict[str, Any], original_request: dict | None = None,
            sufficiency_input: dict | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    result = copy.deepcopy(draft)
    result["schema"] = "public_evidence_envelope.v1"
    binding_issue = None
    if original_request is not None and sufficiency_input is not None:
        try:
            result["contract_binding"] = make_binding(original_request, sufficiency_input)
        except (ValueError, TypeError) as exc:
            binding_issue = str(exc)
    result.setdefault("package_id", "pending")
    canonical = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    result["package_id"] = "evidence-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    receipt = validate(result, original_request, sufficiency_input)
    if binding_issue:
        receipt["status"] = "fail"
        receipt["errors"].append(binding_issue)
        receipt["error_count"] = len(receipt["errors"])
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
    parser.add_argument("--request", type=Path, help="Original frozen request; required for research packaging")
    parser.add_argument("--sufficiency-input", type=Path, help="Actual D237 package, including any separate continuation_adoption")
    args = parser.parse_args()
    draft = json.loads(args.input.read_text(encoding="utf-8"))
    envelope, receipt = package(draft, json.loads(args.request.read_text()) if args.request else None,
                                json.loads(args.sufficiency_input.read_text()) if args.sufficiency_input else None)
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
