#!/usr/bin/env python3
"""Validate portable evidence, consumer rejection boundaries and sensitive-state removal."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlsplit
from request_contract import binding_errors, same, canonical_sha256, request_identity
from validate_adaptive_query_sufficiency import validate_package as validate_sufficiency


SCHEMA = "public_evidence_envelope.v1"
CLASSES = {"fact_candidate", "soft_evidence", "platform_observation", "conflict", "gap"}
ITEM_STATUSES = {"fulfilled", "partial", "gap"}
UPSTREAM_STATUSES = {"fulfilled", "partial", "gap", "stopped"}
DOWNSTREAM_STATUSES = {"not_assessed", "accepted", "accepted_with_conditions", "rejected"}
SOURCE_STRENGTHS = {"primary_official", "structured", "visible_original", "soft", "platform_clue", "aggregate_clue"}
FACT_CAPABLE_STRENGTHS = {"primary_official", "structured", "visible_original"}
SOCIAL_CHANNELS = {"wechat", "xhs"}
CERTAINTIES = {"candidate", "soft_signal", "platform_only", "conflicted", "gap"}
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
    "password",
}
FORBIDDEN_QUERY_KEYS = {"xsec_token", "xsec_source", "access_token", "refresh_token", "authorization", "cookie"}
TOP_FIELDS = {
    "schema",
    "package_id",
    "task_id",
    "request_id",
    "project_id",
    "subject",
    "release_version",
    "upstream_status",
    "downstream_acceptance",
    "request",
    "query_execution",
    "sources",
    "items",
    "negative_hits",
    "conflicts",
    "gaps",
    "stop_reason",
    "package_boundary",
    "contract_binding",
}


def norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(nonempty(item) for item in value)


def nonnegative_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


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
            query_keys = {item.casefold() for item, _ in parse_qsl(urlsplit(value).query, keep_blank_values=True)}
            if query_keys & FORBIDDEN_QUERY_KEYS:
                errors.append(f"transient or account-state URL parameter at {path}")
    return errors


def validate(data: dict[str, Any], original_request: dict | None = None,
             sufficiency_input: dict | None = None, *, allow_legacy_unbound: bool = False, historical_read_only: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    unknown_top = sorted(set(data) - TOP_FIELDS)
    if unknown_top:
        errors.append("unknown top-level fields: " + ", ".join(unknown_top))
    for field in ("package_id", "task_id", "request_id", "subject", "release_version", "stop_reason", "package_boundary"):
        if not nonempty(data.get(field)):
            errors.append(f"missing required field: {field}")
    if data.get("project_id") is not None and not nonempty(data.get("project_id")):
        errors.append("project_id must be a non-empty string or null")
    if data.get("upstream_status") not in UPSTREAM_STATUSES:
        errors.append("upstream_status is invalid")

    downstream = data.get("downstream_acceptance")
    if not isinstance(downstream, dict):
        errors.append("downstream_acceptance must be an object")
        downstream = {}
    else:
        if set(downstream) - {"status", "decided_by", "reason"}:
            errors.append("downstream_acceptance has unknown fields")
    if downstream.get("status") not in DOWNSTREAM_STATUSES:
        errors.append("downstream_acceptance.status is invalid")
    elif downstream.get("status") != "not_assessed":
        errors.append("upstream evidence envelope cannot claim downstream acceptance")
    if downstream.get("decided_by") is not None:
        errors.append("upstream evidence envelope must leave downstream decided_by null")
    if not nonempty(downstream.get("reason")):
        errors.append("downstream_acceptance.reason is required")

    request = data.get("request")
    request_fields = ("business_question", "requested_evidence", "channel_scope", "time_scope", "geo_scope", "usage_boundary", "stop_condition")
    if not isinstance(request, dict):
        errors.append("request must be an object")
        request = {}
    for field in request_fields:
        value = request.get(field)
        if field in {"requested_evidence", "channel_scope"}:
            if not nonempty_string_list(value) or not value:
                errors.append(f"request missing field: {field}")
        elif not nonempty(value):
            errors.append(f"request missing field: {field}")

    query_execution = data.get("query_execution")
    if not isinstance(query_execution, dict):
        errors.append("query_execution must be an object")
        query_execution = {}
    else:
        allowed = {
            "mode",
            "plan_schema",
            "plan_version",
            "acceptance_mode",
            "evidence_sufficiency_status",
            "executed_query_ids",
            "proposed_incremental_query_ids",
            "adaptive_extension_authorized",
            "result_batch_count",
            "actual_open_count",
            "failure_attribution_complete",
        }
        if set(query_execution) - allowed:
            errors.append("query_execution has unknown fields")
    mode = query_execution.get("mode")
    if mode not in {"research_retrieval", "simple_direct_retrieval"}:
        errors.append("query_execution.mode is invalid")
    if mode == "research_retrieval":
        if query_execution.get("plan_schema") != "social_query_plan.v1" or not nonempty(query_execution.get("plan_version")):
            errors.append("research retrieval requires social_query_plan.v1 and plan_version")
    elif mode == "simple_direct_retrieval":
        if query_execution.get("plan_schema") is not None or query_execution.get("plan_version") is not None:
            errors.append("simple direct retrieval must not invent a social query plan")
    allowed_modes = {"hybrid", "count_based", "quality_sufficiency"} if mode == "research_retrieval" else {"exempt_simple_direct_retrieval"}
    if query_execution.get("acceptance_mode") not in allowed_modes:
        errors.append("query_execution.acceptance_mode is invalid")
    binding = data.get("contract_binding")
    if binding is not None:
        errors.extend(binding_errors(binding, original_request, None if historical_read_only else sufficiency_input))
        if isinstance(binding, dict):
            if binding.get("request_id") != data.get("request_id"):
                errors.append("contract_binding_request_mismatch")
            acceptance = binding.get("acceptance_contract", {})
            if not isinstance(acceptance, dict) or acceptance.get("acceptance_mode") != query_execution.get("acceptance_mode"):
                errors.append("contract_binding_execution_mode_mismatch")
        if original_request is None and not historical_read_only:
            errors.append("original_request_required_for_bound_validation")
        if historical_read_only and sufficiency_input is not None and isinstance(binding, dict) and binding.get("sufficiency_package_sha256") != canonical_sha256(sufficiency_input):
            errors.append("historical_sufficiency_hash_mismatch")
    elif mode == "research_retrieval" and not allow_legacy_unbound and not historical_read_only:
        errors.append("contract_binding_required")
    if original_request is not None:
        for key in ("request_id", "task_id", "project_id"):
            expected = request_identity(original_request) if key == "request_id" else original_request.get(key)
            if data.get(key) != expected:
                errors.append("envelope_request_mismatch:" + key)
    if sufficiency_input is not None:
        if not historical_read_only:
            checked = validate_sufficiency(sufficiency_input, original_request)
            if not checked["passed"]:
                errors.append("sufficiency_validation_failed:" + checked["status"])
                errors.extend(checked.get("errors", []))
        elif isinstance(binding, dict) and isinstance(binding.get("acceptance_contract"), dict):
            for key, value in binding["acceptance_contract"].items():
                if not same(value, sufficiency_input.get("consumer_contract", {}).get(key)):
                    errors.append("historical_acceptance_mismatch:" + key)
        actual = sufficiency_input.get("receipt", {})
        if query_execution.get("evidence_sufficiency_status") != actual.get("evidence_sufficiency_status"):
            errors.append("sufficiency_status_mismatch")
        for output_key, receipt_key in (("result_batch_count", "executed_result_batch_count"), ("actual_open_count", "actual_open_count")):
            if not same(query_execution.get(output_key), actual.get(receipt_key)):
                errors.append("sufficiency_execution_count_mismatch:" + output_key)
        batch = sufficiency_input.get("batch", {})
        if batch.get("batch_state") != "proposed_incremental_batch":
            ids = [q.get("query_id") for q in batch.get("queries", []) if isinstance(q, dict)]
            if set(query_execution.get("executed_query_ids", [])) != set(ids):
                errors.append("sufficiency_executed_query_mismatch")
        extension = sufficiency_input.get("consumer_contract", {}).get("adaptive_extension", {})
        if query_execution.get("adaptive_extension_authorized") is not extension.get("authorized"):
            errors.append("sufficiency_extension_flag_mismatch")
    elif mode == "research_retrieval" and not allow_legacy_unbound and not historical_read_only:
        errors.append("sufficiency_input_required")
    if query_execution.get("evidence_sufficiency_status") not in {"sufficient", "partially_sufficient", "expression_supply_gap", "not_assessed"}:
        errors.append("query_execution.evidence_sufficiency_status is invalid")
    for field in ("executed_query_ids", "proposed_incremental_query_ids"):
        value = query_execution.get(field)
        if not nonempty_string_list(value):
            errors.append(f"query_execution.{field} must be a string list")
    overlap = set(query_execution.get("executed_query_ids") or []) & set(query_execution.get("proposed_incremental_query_ids") or [])
    if overlap:
        errors.append("proposed incremental queries cannot be listed as executed")
    if query_execution.get("adaptive_extension_authorized") not in {True, False}:
        errors.append("query_execution.adaptive_extension_authorized must be boolean")
    for field in ("result_batch_count", "actual_open_count"):
        if not nonnegative_integer(query_execution.get(field)):
            errors.append(f"query_execution.{field} must be a non-negative integer")
    if query_execution.get("failure_attribution_complete") is not True:
        errors.append("query_execution.failure_attribution_complete must be true")

    sources = data.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        sources = []
    source_by_id: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        required = ("source_id", "channel", "source_role", "source_strength", "stable_pointer", "title", "publisher", "observed_at", "discovery_mode")
        for field in required:
            if not nonempty(source.get(field)):
                errors.append(f"sources[{index}] missing field: {field}")
        source_id = source.get("source_id")
        if nonempty(source_id):
            if source_id in source_by_id:
                errors.append("source_id must be unique")
            source_by_id[source_id] = source
        if source.get("source_strength") not in SOURCE_STRENGTHS:
            errors.append(f"sources[{index}].source_strength is invalid")
        if source.get("discovery_mode") not in {"query_results_discovery", "known_url_or_direct"}:
            errors.append(f"sources[{index}].discovery_mode is invalid")
        if source.get("channel") in SOCIAL_CHANNELS and source.get("discovery_mode") == "query_results_discovery":
            query_ref = source.get("query_ref")
            if not isinstance(query_ref, dict):
                errors.append(f"sources[{index}].query_ref is required")
            else:
                for field in ("query_id", "exact_query_text", "plan_version", "searcher_mode"):
                    if not nonempty(query_ref.get(field)):
                        errors.append(f"sources[{index}].query_ref.{field} is required")
                for field in ("result_batch_count", "actual_open_count"):
                    if not nonnegative_integer(query_ref.get(field)):
                        errors.append(f"sources[{index}].query_ref.{field} must be non-negative")

    items = data.get("items")
    if not isinstance(items, list):
        errors.append("items must be a list")
        items = []
    item_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{index}] must be an object")
            continue
        item_id = item.get("item_id")
        if not nonempty(item_id):
            errors.append(f"items[{index}].item_id is required")
        elif item_id in item_by_id:
            errors.append("item_id must be unique")
        else:
            item_by_id[item_id] = item
        evidence_class = item.get("evidence_class")
        status = item.get("status")
        if evidence_class not in CLASSES:
            errors.append(f"items[{index}].evidence_class is invalid")
        if status not in ITEM_STATUSES:
            errors.append(f"items[{index}].status is invalid")
        if item.get("certainty") not in CERTAINTIES:
            errors.append(f"items[{index}].certainty is invalid")
        if not nonempty(item.get("usage_boundary")):
            errors.append(f"items[{index}].usage_boundary is required")
        if not nonempty_string_list(item.get("allowed_use")) or not item.get("allowed_use"):
            errors.append(f"items[{index}].allowed_use is required")
        if not nonempty_string_list(item.get("blocked_use")):
            errors.append(f"items[{index}].blocked_use must be a string list")
        refs = item.get("source_refs")
        if not isinstance(refs, list) or not all(nonempty(ref) for ref in refs):
            errors.append(f"items[{index}].source_refs must be a string list")
            refs = []
        if any(ref not in source_by_id for ref in refs):
            errors.append(f"items[{index}] references unknown sources")
        if evidence_class != "gap" and not nonempty(item.get("original_claim")):
            errors.append(f"items[{index}].original_claim is required")
        if evidence_class in {"fact_candidate", "soft_evidence", "platform_observation"} and not refs:
            errors.append(f"items[{index}] requires at least one source_ref")
        if evidence_class == "fact_candidate":
            strengths = {source_by_id.get(ref, {}).get("source_strength") for ref in refs}
            if not strengths & FACT_CAPABLE_STRENGTHS:
                errors.append(f"items[{index}] soft evidence cannot enter fact_candidate")
            if item.get("certainty") != "candidate":
                errors.append(f"items[{index}] fact_candidate certainty must remain candidate")
        if evidence_class in {"soft_evidence", "platform_observation"}:
            required_blocks = {"project_hard_fact", "market_generalization"}
            if not required_blocks.issubset(set(item.get("blocked_use") or [])):
                errors.append(f"items[{index}] soft or platform evidence must block hard-fact and market-generalization use")
            if item.get("certainty") not in {"soft_signal", "platform_only"}:
                errors.append(f"items[{index}] soft or platform evidence certainty is too strong")
        if evidence_class == "conflict":
            conflict_refs = item.get("conflict_refs")
            if not isinstance(conflict_refs, list) or len(set(conflict_refs)) < 2 or any(ref not in source_by_id for ref in conflict_refs):
                errors.append(f"items[{index}] conflict requires two distinct known sources")
            if item.get("certainty") != "conflicted":
                errors.append(f"items[{index}] conflict certainty must be conflicted")
        if evidence_class == "gap" or status == "gap":
            if not nonempty(item.get("gap_reason")) or not nonempty(item.get("retry_condition")):
                errors.append(f"items[{index}] gap_reason and retry_condition are required")
            if item.get("blocking_level") not in {"blocking", "non_blocking"}:
                errors.append(f"items[{index}].blocking_level is required")
            if item.get("certainty") != "gap":
                errors.append(f"items[{index}] gap certainty must be gap")

    negative_hits = data.get("negative_hits")
    if not isinstance(negative_hits, list):
        errors.append("negative_hits must be a list")
        negative_hits = []
    negative_ids: set[str] = set()
    for index, hit in enumerate(negative_hits):
        if not isinstance(hit, dict):
            errors.append(f"negative_hits[{index}] must be an object")
            continue
        for field in ("negative_hit_id", "query_id", "observed", "usage_boundary"):
            if not nonempty(hit.get(field)):
                errors.append(f"negative_hits[{index}].{field} is required")
        hit_id = hit.get("negative_hit_id")
        if hit_id in negative_ids:
            errors.append("negative_hit_id must be unique")
        negative_ids.add(hit_id)
        refs = hit.get("source_refs")
        if not isinstance(refs, list) or any(ref not in source_by_id for ref in refs):
            errors.append(f"negative_hits[{index}].source_refs is invalid")

    conflicts = data.get("conflicts")
    gaps = data.get("gaps")
    if not nonempty_string_list(conflicts):
        errors.append("conflicts must be a string list")
        conflicts = []
    if not nonempty_string_list(gaps):
        errors.append("gaps must be a string list")
        gaps = []
    actual_conflicts = {item_id for item_id, item in item_by_id.items() if item.get("evidence_class") == "conflict"}
    actual_gaps = {item_id for item_id, item in item_by_id.items() if item.get("evidence_class") == "gap"}
    if sufficiency_input is not None:
        for row in sufficiency_input.get("receipt", {}).get("cumulative_evidence", []):
            identity = row if isinstance(row, str) else row.get("evidence_item_id") if isinstance(row, dict) else None
            if identity not in item_by_id or identity in actual_conflicts | actual_gaps:
                errors.append("qualified_evidence_must_reference_usable_items")
    if set(conflicts) != actual_conflicts:
        errors.append("conflicts must enumerate every conflict item exactly once")
    if set(gaps) != actual_gaps:
        errors.append("gaps must enumerate every gap item exactly once")
    if data.get("upstream_status") == "fulfilled" and any(item_by_id[item_id].get("blocking_level") == "blocking" for item_id in actual_gaps):
        errors.append("fulfilled upstream status cannot hide a blocking gap")

    errors.extend(sensitive_errors(data))
    errors = sorted(set(errors))
    consumer_rejection_required = any(
        "soft evidence cannot enter fact_candidate" in error
        or "upstream evidence envelope cannot claim downstream acceptance" in error
        or "cannot hide a blocking gap" in error
        for error in errors
    )
    return {
        "schema": "public_evidence_validation_receipt.v2",
        "status": "pass" if not errors else "fail",
        "error_count": len(errors),
        "errors": errors,
        "source_count": len(sources),
        "item_count": len(items),
        "negative_hit_count": len(negative_hits),
        "conflict_count": len(actual_conflicts),
        "gap_count": len(actual_gaps),
        "upstream_status": data.get("upstream_status"),
        "downstream_acceptance_status": downstream.get("status"),
        "consumer_rejection_required": consumer_rejection_required,
        "network_accessed": False,
        "external_write_executed": False,
        "evidence_class_changed": False,
        "downstream_acceptance_changed": False,
        "validation_scope": "historical_read_only" if historical_read_only else "legacy_structure_only" if binding is None and allow_legacy_unbound else "request_and_sufficiency_bound",
        "production_binding_verified": not historical_read_only and not errors and original_request is not None and sufficiency_input is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--sufficiency-input", type=Path)
    parser.add_argument("--allow-legacy-unbound", action="store_true", help="Historical read-only structure review; never a production adoption approval")
    parser.add_argument("--historical-read-only", action="store_true", help="Read rc6 bound or older evidence without claiming current execution or adoption checks")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    validation = validate(data, json.loads(args.request.read_text()) if args.request else None,
                          json.loads(args.sufficiency_input.read_text()) if args.sufficiency_input else None,
                          allow_legacy_unbound=args.allow_legacy_unbound, historical_read_only=args.historical_read_only)
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
