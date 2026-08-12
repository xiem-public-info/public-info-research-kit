#!/usr/bin/env python3
"""Validate the portable public-evidence envelope and reject sensitive state."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlsplit


SCHEMA = "public_evidence_envelope.v1"
CLASSES = {"fact_candidate", "soft_evidence", "platform_observation", "conflict", "gap"}
STATUSES = {"fulfilled", "partial", "gap"}
FORBIDDEN_KEYS = {
    "cookie",
    "cookies",
    "authorization",
    "accesstoken",
    "refreshtoken",
    "xsectoken",
    "xsecsource",
    "storagestate",
    "localstorage",
    "sessionstorage",
    "requestheaders",
    "qrcredential",
    "clipboardcontent",
    "profilepath",
    "browserprofile",
    "userdatadir",
}
FORBIDDEN_QUERY_KEYS = {"xsec_token", "xsec_source", "access_token", "refresh_token", "authorization"}


def norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield child_path, child, str(key)
            yield from walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield child_path, child, ""
            yield from walk(child, child_path)


def sensitive_errors(data: Any) -> list[str]:
    errors: list[str] = []
    for path, value, key in walk(data):
        if key and norm_key(key) in FORBIDDEN_KEYS:
            errors.append(f"forbidden sensitive field at {path}")
        if not isinstance(value, str):
            continue
        lowered = value.casefold()
        if "/users/" in lowered or "file:///users/" in lowered:
            errors.append(f"portable evidence cannot contain a macOS home path at {path}")
        if re.search(r"(^|[;\s])cookie\s*:", value, re.IGNORECASE):
            errors.append(f"cookie header-like value at {path}")
        if re.search(r"(^|[;\s])authorization\s*:", value, re.IGNORECASE):
            errors.append(f"authorization header-like value at {path}")
        if value.startswith(("http://", "https://")):
            query_keys = {key.casefold() for key, _ in parse_qsl(urlsplit(value).query, keep_blank_values=True)}
            if query_keys & FORBIDDEN_QUERY_KEYS:
                errors.append(f"transient or account-state URL parameter at {path}")
    return errors


def validate(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    for field in ("package_id", "task_id", "subject", "release_version", "package_boundary"):
        if not nonempty(data.get(field)):
            errors.append(f"missing required field: {field}")

    request = data.get("request")
    request_fields = ("business_question", "requested_evidence", "channel_scope", "time_scope", "geo_scope", "usage_boundary", "stop_condition")
    if not isinstance(request, dict):
        errors.append("request must be an object")
        request = {}
    for field in request_fields:
        if not request.get(field):
            errors.append(f"request missing field: {field}")

    sources = data.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        sources = []
    source_ids: list[str] = []
    source_by_id: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        source_id = str(source.get("source_id") or "")
        source_ids.append(source_id)
        source_by_id[source_id] = source
        for field in ("source_id", "channel", "source_role", "stable_pointer", "title", "publisher", "observed_at"):
            if not nonempty(source.get(field)):
                errors.append(f"sources[{index}] missing field: {field}")
    if len(source_ids) != len(set(source_ids)):
        errors.append("source_id must be unique")

    items = data.get("items")
    if not isinstance(items, list):
        errors.append("items must be a list")
        items = []
    item_ids: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] must be an object")
            continue
        item_id = str(item.get("item_id") or "")
        item_ids.append(item_id)
        evidence_class = item.get("evidence_class")
        status = item.get("status")
        if evidence_class not in CLASSES:
            errors.append(f"items[{index}].evidence_class is invalid")
        if status not in STATUSES:
            errors.append(f"items[{index}].status is invalid")
        if not nonempty(item.get("usage_boundary")):
            errors.append(f"items[{index}].usage_boundary is required")
        refs = item.get("source_refs") or []
        if not isinstance(refs, list):
            errors.append(f"items[{index}].source_refs must be a list")
            refs = []
        unknown_refs = [ref for ref in refs if ref not in source_by_id]
        if unknown_refs:
            errors.append(f"items[{index}] references unknown sources")

        if evidence_class != "gap" and not nonempty(item.get("original_claim")):
            errors.append(f"items[{index}].original_claim is required")
        if evidence_class in {"fact_candidate", "soft_evidence", "platform_observation"} and not refs:
            errors.append(f"items[{index}] requires at least one source_ref")
        if evidence_class in {"soft_evidence", "platform_observation"} and item.get("certainty") == "confirmed_fact":
            errors.append(f"items[{index}] soft evidence cannot be upgraded to confirmed_fact")
        if evidence_class == "conflict":
            conflict_refs = item.get("conflict_refs") or []
            if not isinstance(conflict_refs, list) or len(set(conflict_refs)) < 2:
                errors.append(f"items[{index}] conflict requires at least two distinct conflict_refs")
            elif any(ref not in source_by_id for ref in conflict_refs):
                errors.append(f"items[{index}] conflict references an unknown source")
        if evidence_class == "gap" or status == "gap":
            if not nonempty(item.get("gap_reason")):
                errors.append(f"items[{index}] gap_reason is required")
            if not nonempty(item.get("retry_condition")):
                errors.append(f"items[{index}] retry_condition is required")
    if len(item_ids) != len(set(item_ids)):
        errors.append("item_id must be unique")

    errors.extend(sensitive_errors(data))
    errors = sorted(set(errors))
    return {
        "schema": "public_evidence_validation_receipt.v1",
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "errors": errors,
        "network_accessed": False,
        "external_write_executed": False,
        "evidence_class_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = validate(data)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
