"""Deterministic business-contract adaptation and immutable request binding.

This module reads declared fields, never interprets user prose or executes work.
Keep the portable copy behavior-identical; the original request stays unchanged.
"""
from __future__ import annotations

import copy
import hashlib
import json

RESIDENTIAL_SCHEMA = "residential.upstream_task.v0.2"
BINDING_SCHEMA = "public_retrieval_contract_binding.v1"
ACCEPTANCE_FIELDS = (
    "acceptance_mode", "qualified_match_classes", "quality_criteria",
    "count_threshold", "diversity_requirements", "research_characteristics",
)
REQUIREMENT_FIELDS = ACCEPTANCE_FIELDS + (
    "qualification_policy", "diversity_policy", "count_target", "diversity_targets",
    "required_object_ids", "marginal_gain_fields", "non_counted_match_classes",
    "evidence_usage_permission", "adaptive_extension", "sufficiency_policy",
)


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def same(left: object, right: object) -> bool:
    return canonical_sha256(left) == canonical_sha256(right)


def merge_declared(target: dict, source: dict, fields=REQUIREMENT_FIELDS) -> None:
    for key in fields:
        if key in source:
            if key in target and not same(target[key], source[key]):
                raise ValueError("request_contract_conflict:" + key)
            target[key] = copy.deepcopy(source[key])


def normalize_request(original: dict) -> dict:
    if not isinstance(original, dict):
        raise ValueError("retrieval_task_contract_required")
    task = copy.deepcopy(original)
    sufficiency = task.get("sufficiency", {})
    if not isinstance(sufficiency, dict):
        raise ValueError("retrieval_sufficiency_invalid")
    merge_declared(sufficiency, task)
    if task.get("schema") == RESIDENTIAL_SCHEMA:
        contract = task.get("acceptance_contract")
        if not isinstance(contract, dict) or any(key not in contract for key in ACCEPTANCE_FIELDS):
            raise ValueError("residential_acceptance_contract_required")
        if contract["acceptance_mode"] not in {"hybrid", "count_based", "quality_sufficiency"}:
            raise ValueError("invalid_acceptance_mode")
        merge_declared(sufficiency, contract)
        objects = task.get("object_scope")
        if not isinstance(objects, dict) or not isinstance(objects.get("canonical_subject"), str) or not objects["canonical_subject"].strip():
            raise ValueError("residential_object_scope_required")
        comparisons = objects.get("comparison_objects")
        if not isinstance(comparisons, list) or any(not isinstance(x, str) or not x.strip() for x in comparisons):
            raise ValueError("residential_comparison_objects_invalid")
        subjects = list(dict.fromkeys([objects["canonical_subject"], *comparisons]))
        if "subjects" in task and not same(task["subjects"], subjects):
            raise ValueError("request_contract_conflict:subjects")
        task["subjects"] = subjects
        task["business_domain"] = "residential"
        stops = task.get("stop_conditions")
        if not isinstance(stops, list) or not stops or any(not isinstance(x, str) or not x.strip() for x in stops):
            raise ValueError("residential_stop_conditions_required")
        stop = "；".join(stops)
        if "stop_condition" in task and task["stop_condition"] != stop:
            raise ValueError("request_contract_conflict:stop_condition")
        task["stop_condition"] = stop
        if task.get("authorization") not in {"confirmed", "synthetic_fixture"}:
            raise ValueError("residential_authorization_required")
        policy = task.get("incremental_policy")
        if not isinstance(policy, dict) or type(policy.get("execution_authorized")) is not bool:
            raise ValueError("residential_incremental_policy_required")
        extension = {"authorized": policy["execution_authorized"]}
        for key in ("authorization_ref", "maximum_incremental_batches", "time_limit_minutes", "cost_limit"):
            if key not in policy:
                raise ValueError("residential_incremental_policy_required:" + key)
            extension[key] = policy[key]
        merge_declared(sufficiency, {"adaptive_extension": extension})
        if "in_scope_iteration_allowed" in policy:
            if type(policy["in_scope_iteration_allowed"]) is not bool:
                raise ValueError("in_scope_iteration_policy_invalid")
            if "in_scope_iteration_allowed" in task and task["in_scope_iteration_allowed"] != policy["in_scope_iteration_allowed"]:
                raise ValueError("request_contract_conflict:in_scope_iteration_allowed")
            task["in_scope_iteration_allowed"] = policy["in_scope_iteration_allowed"]
        task["business_owner"] = "residential_production_owner"
        task["requested_evidence"] = copy.deepcopy(task.get("requested_evidence_roles", []))
        destination = task.get("downstream_destination", {})
        task.setdefault("usage_boundary", "；".join(destination.get("allowed_uses", [])))
    if sufficiency:
        task["sufficiency"] = sufficiency
    return task


def acceptance_contract(original: dict) -> dict:
    task = normalize_request(original)
    if task.get("schema") == RESIDENTIAL_SCHEMA:
        return copy.deepcopy(task["acceptance_contract"])
    return {key: copy.deepcopy(task.get("sufficiency", {})[key])
            for key in REQUIREMENT_FIELDS if key in task.get("sufficiency", {})
            and key not in {"adaptive_extension", "sufficiency_policy"}}


def check_sufficiency_binding(original: dict, package: dict) -> list[str]:
    errors = []
    try:
        expected = acceptance_contract(original)
    except (ValueError, TypeError) as exc:
        return [str(exc)]
    for key in ("task_id", "request_id"):
        if not original.get(key) or package.get(key) != original[key]:
            errors.append("sufficiency_request_mismatch:" + key)
    if package.get("source_request_sha256") != canonical_sha256(original):
        errors.append("sufficiency_request_hash_mismatch")
    consumer = package.get("consumer_contract", {})
    if not isinstance(consumer, dict):
        return errors + ["invalid_consumer_contract"]
    for key, value in expected.items():
        if key not in consumer or not same(value, consumer[key]):
            errors.append("sufficiency_contract_mismatch:" + key)
    task = normalize_request(original)
    batch = package.get("batch", {})
    if batch.get("batch_state") == "in_scope_iteration_batch" and task.get("in_scope_iteration_allowed") is False:
        errors.append("in_scope_iteration_explicitly_disallowed")
    expected_extension = task.get("sufficiency", {}).get("adaptive_extension")
    actual_extension = consumer.get("adaptive_extension")
    if expected_extension is not None and not same(expected_extension, actual_extension):
        decision = package.get("continuation_adoption", {})
        valid_decision = isinstance(decision, dict) and decision.get("schema") == "residential.upstream_adoption_receipt.v0.2"
        valid_decision = valid_decision and all(decision.get(key) == original.get(key) for key in ("request_id", "task_id", "project_id"))
        valid_decision = valid_decision and decision.get("accepted_by") == "residential_production_owner"
        increment = decision.get("incremental_decision", {}) if valid_decision else {}
        ids = increment.get("authorized_query_ids", [])
        query_ids = [q.get("query_id") for q in batch.get("queries", []) if isinstance(q, dict)]
        valid_decision = valid_decision and increment.get("decision") == "authorize_incremental" and bool(increment.get("limits"))
        valid_decision = valid_decision and isinstance(ids, list) and bool(query_ids) and set(query_ids).issubset(set(ids))
        if batch.get("batch_state") != "approved_incremental_batch" or not valid_decision:
            errors.append("sufficiency_extension_authority_mismatch")
    return errors


def make_binding(original: dict, package: dict) -> dict:
    errors = check_sufficiency_binding(original, package)
    if errors:
        raise ValueError(";".join(errors))
    return {
        "schema": BINDING_SCHEMA,
        "request_schema": original.get("schema", "retrieval_task"),
        "request_id": original["request_id"],
        "request_sha256": canonical_sha256(original),
        "acceptance_contract": acceptance_contract(original),
        "sufficiency_package_sha256": canonical_sha256(package),
    }


def binding_errors(binding: dict, original: dict | None = None, package: dict | None = None) -> list[str]:
    fields = {"schema", "request_schema", "request_id", "request_sha256", "acceptance_contract", "sufficiency_package_sha256"}
    if not isinstance(binding, dict) or set(binding) != fields or binding.get("schema") != BINDING_SCHEMA:
        return ["contract_binding_invalid"]
    errors = []
    for key in ("request_schema", "request_id"):
        if not isinstance(binding.get(key), str) or not binding[key].strip():
            errors.append("contract_binding_invalid:" + key)
    for key in ("request_sha256", "sufficiency_package_sha256"):
        value = binding.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            errors.append("contract_binding_invalid:" + key)
    if not isinstance(binding.get("acceptance_contract"), dict):
        errors.append("contract_binding_invalid:acceptance_contract")
    if original is not None:
        try:
            if binding.get("request_id") != original.get("request_id") or binding.get("request_schema") != original.get("schema", "retrieval_task"):
                errors.append("contract_binding_request_mismatch")
            if binding.get("request_sha256") != canonical_sha256(original):
                errors.append("contract_binding_request_hash_mismatch")
            if not same(binding.get("acceptance_contract"), acceptance_contract(original)):
                errors.append("contract_binding_acceptance_mismatch")
        except (ValueError, TypeError) as exc:
            errors.append(str(exc))
    if package is not None:
        if binding.get("sufficiency_package_sha256") != canonical_sha256(package):
            errors.append("contract_binding_sufficiency_hash_mismatch")
        if original is not None:
            errors.extend(check_sufficiency_binding(original, package))
    return errors
