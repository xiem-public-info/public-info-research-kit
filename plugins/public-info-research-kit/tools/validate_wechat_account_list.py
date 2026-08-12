#!/usr/bin/env python3
"""Validate WeChat publisher-list requests and terminal receipts without platform access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


REQUEST_SCHEMA = "wechat_publisher_list_request.v1"
RECEIPT_SCHEMA = "wechat_publisher_list_receipt.v1"
TERMINAL = {"fulfilled", "partial", "gap"}
ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def canonical_sha256(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalized(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def validate_request(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != REQUEST_SCHEMA:
        errors.append(f"schema must be {REQUEST_SCHEMA}")
    for field in ("task_id", "subject", "business_question", "usage_boundary", "stop_condition"):
        if not normalized(data.get(field)):
            errors.append(f"missing required field: {field}")
    evidence = data.get("requested_evidence")
    if not isinstance(evidence, list) or not evidence or any(not normalized(x) for x in evidence):
        errors.append("requested_evidence must be a non-empty string list")

    accounts = data.get("publisher_accounts")
    if not isinstance(accounts, list) or not accounts:
        errors.append("publisher_accounts must be a non-empty list")
        accounts = []
    ids: set[str] = set()
    identity_names: dict[str, str] = {}
    for index, account in enumerate(accounts):
        if not isinstance(account, dict):
            errors.append(f"publisher_accounts[{index}] must be an object")
            continue
        publisher_id = str(account.get("publisher_id") or "")
        if not ID_RE.fullmatch(publisher_id):
            errors.append(f"publisher_accounts[{index}].publisher_id is invalid")
        elif publisher_id in ids:
            errors.append(f"duplicate publisher_id: {publisher_id}")
        ids.add(publisher_id)
        display_name = normalized(account.get("display_name"))
        if not display_name:
            errors.append(f"publisher_accounts[{index}].display_name is required")
        names = [display_name] + [normalized(x) for x in account.get("aliases", [])]
        if any(not name for name in names):
            errors.append(f"publisher_accounts[{index}] contains an empty alias")
        if len(set(names)) != len(names):
            errors.append(f"publisher_accounts[{index}] contains duplicate display name or alias")
        for name in names:
            if not name:
                continue
            previous = identity_names.get(name)
            if previous and previous != publisher_id:
                errors.append(f"ambiguous publisher name or alias: {name}")
            identity_names[name] = publisher_id

    strategy = data.get("query_strategy")
    if not isinstance(strategy, dict):
        errors.append("query_strategy is required")
    else:
        keywords = strategy.get("keywords")
        if not isinstance(keywords, list) or not keywords or any(not normalized(x) for x in keywords):
            errors.append("query_strategy.keywords must be a non-empty string list")
        if not isinstance(strategy.get("include_aliases"), bool):
            errors.append("query_strategy.include_aliases must be boolean")
        maximum = strategy.get("max_articles_per_publisher")
        if not isinstance(maximum, int) or isinstance(maximum, bool) or not 1 <= maximum <= 100:
            errors.append("query_strategy.max_articles_per_publisher must be an integer from 1 to 100")
    return sorted(set(errors))


def validate_receipt(data: dict[str, Any], request: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != RECEIPT_SCHEMA:
        errors.append(f"schema must be {RECEIPT_SCHEMA}")
    for field in ("task_id", "request_sha256", "usage_boundary"):
        if not normalized(data.get(field)):
            errors.append(f"missing required field: {field}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(data.get("request_sha256") or "")):
        errors.append("request_sha256 must be 64 lowercase hex characters")

    publisher_results = data.get("publisher_results")
    if not isinstance(publisher_results, list) or not publisher_results:
        errors.append("publisher_results must be a non-empty list")
        publisher_results = []
    result_ids: list[str] = []
    for index, result in enumerate(publisher_results):
        if not isinstance(result, dict):
            errors.append(f"publisher_results[{index}] must be an object")
            continue
        publisher_id = str(result.get("publisher_id") or "")
        result_ids.append(publisher_id)
        status = result.get("status")
        if status not in TERMINAL:
            errors.append(f"publisher_results[{index}].status must be terminal")
        if status in {"partial", "gap"} and not normalized(result.get("gap_reason")):
            errors.append(f"publisher_results[{index}] requires gap_reason")
        if status == "gap" and not normalized(result.get("retry_condition")):
            errors.append(f"publisher_results[{index}] requires retry_condition")
    if len(result_ids) != len(set(result_ids)):
        errors.append("publisher_results contains duplicate publisher_id")

    query_results = data.get("query_results")
    if not isinstance(query_results, list):
        errors.append("query_results must be a list")
        query_results = []
    query_ids: list[str] = []
    candidate_count = 0
    for index, result in enumerate(query_results):
        if not isinstance(result, dict):
            errors.append(f"query_results[{index}] must be an object")
            continue
        query_id = str(result.get("query_id") or "")
        query_ids.append(query_id)
        items = result.get("candidate_pointers") or []
        if not isinstance(items, list) or any(not normalized(x) for x in items):
            errors.append(f"query_results[{index}].candidate_pointers must be a string list")
        else:
            candidate_count += len(items)
    if len(query_ids) != len(set(query_ids)):
        errors.append("query_results contains duplicate query_id")

    unique_items = data.get("unique_items")
    if not isinstance(unique_items, list):
        errors.append("unique_items must be a list")
        unique_items = []
    pointers: list[str] = []
    for index, item in enumerate(unique_items):
        if not isinstance(item, dict):
            errors.append(f"unique_items[{index}] must be an object")
            continue
        pointer = normalized(item.get("stable_pointer"))
        if not pointer:
            errors.append(f"unique_items[{index}].stable_pointer is required")
        pointers.append(pointer)
        source_queries = item.get("source_query_ids")
        if not isinstance(source_queries, list) or not source_queries:
            errors.append(f"unique_items[{index}].source_query_ids is required")
        elif any(query_id not in query_ids for query_id in source_queries):
            errors.append(f"unique_items[{index}] references an unknown query_id")
    if len(pointers) != len(set(pointers)):
        errors.append("unique_items must be deduplicated by stable_pointer")

    summary = data.get("dedup_summary")
    if not isinstance(summary, dict):
        errors.append("dedup_summary is required")
    else:
        expected_unique = len(unique_items)
        expected_duplicates = candidate_count - expected_unique
        if summary.get("input_hit_count") != candidate_count:
            errors.append("dedup_summary.input_hit_count mismatch")
        if summary.get("unique_item_count") != expected_unique:
            errors.append("dedup_summary.unique_item_count mismatch")
        if summary.get("duplicate_hit_count") != expected_duplicates:
            errors.append("dedup_summary.duplicate_hit_count mismatch")
        if expected_duplicates < 0:
            errors.append("unique_items cannot exceed input hits")

    if request is not None:
        request_errors = validate_request(request)
        if request_errors:
            errors.append("linked request is invalid")
        expected_ids = [str(x.get("publisher_id") or "") for x in request.get("publisher_accounts", [])]
        if sorted(expected_ids) != sorted(result_ids):
            errors.append("every input publisher must have exactly one terminal result")
        if data.get("task_id") != request.get("task_id"):
            errors.append("task_id does not match request")
        if data.get("request_sha256") != canonical_sha256(request):
            errors.append("request_sha256 does not match request")
        if data.get("usage_boundary") != request.get("usage_boundary"):
            errors.append("usage_boundary does not match request")
    return sorted(set(errors))


def validate(data: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
    if data.get("schema") == REQUEST_SCHEMA:
        errors = validate_request(data)
        kind = "request"
    elif data.get("schema") == RECEIPT_SCHEMA:
        errors = validate_receipt(data, request)
        kind = "receipt"
    else:
        errors = ["unsupported schema"]
        kind = "unknown"
    return {
        "schema": "wechat_publisher_list_validation.v1",
        "kind": kind,
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "platform_opened": False,
        "network_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    request = json.loads(args.request.read_text(encoding="utf-8")) if args.request else None
    result = validate(data, request)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
