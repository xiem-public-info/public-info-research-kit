#!/usr/bin/env python3
"""Frozen-request-first regression checks; all material is synthetic and offline."""
from __future__ import annotations
import copy
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTABLE = (ROOT / "tools/request_contract.py").is_file()
TOOLS = ROOT / "tools" if PORTABLE else ROOT / "scripts/public_info_base"
FIXTURES = ROOT / "tests/fixtures/residential-contract-binding"
sys.path.insert(0, str(TOOLS))
from request_contract import canonical_sha256, normalize_request, check_sufficiency_binding
from compile_retrieval_execution_request import compile_request
from retrieval_task_policy import validate_task_authorization
SUFF = importlib.import_module("validate_adaptive_query_sufficiency" if PORTABLE else "validate_adaptive_query_sufficiency_contract")


def main() -> int:
    request = json.loads((FIXTURES / "request.json").read_text())
    suff = json.loads((FIXTURES / "sufficiency-input.json").read_text())
    if not PORTABLE:
        suff["schema"] = SUFF.CONTRACT["package_schema"]
    before = canonical_sha256(request)
    query = request["query_plan"]["frozen_queries"][0]
    plan = {"channel": "public_web", "queries": [{"query_id": query["query_id"], "exact_query_text": query["exact_query_text"], "execution_state": "frozen"}]}
    cases = []
    def check(name, condition):
        cases.append({"case_id": name, "passed": bool(condition)})

    compiled = compile_request(request, plan)
    suff["execution_request"] = copy.deepcopy(compiled)
    check("residential_full_mapping", all(compiled["sufficiency_applicability"].get(k) == v for k, v in request["acceptance_contract"].items()))
    check("objects_stops_and_original_preserved", compiled["subjects"] == [request["object_scope"]["canonical_subject"], *request["object_scope"]["comparison_objects"]] and compiled["stop_condition"] == "；".join(request["stop_conditions"]) and compiled["retrieval_task"] == request)
    check("partial_receipt_is_valid_not_complete", SUFF.validate_package(suff, request)["passed"] and suff["receipt"]["evidence_sufficiency_status"] == "partially_sufficient")
    for key, changed in (("acceptance_mode", "quality_sufficiency"), ("count_threshold", 1), ("quality_criteria", []), ("diversity_requirements", {}), ("qualified_match_classes", ["supporting"]), ("research_characteristics", [])):
        bad = copy.deepcopy(suff); bad["consumer_contract"][key] = changed
        check("sufficiency_rejects_drift_" + key, not SUFF.validate_package(bad, request)["passed"])
        bad_exec = copy.deepcopy(compiled); bad_exec["sufficiency_applicability"][key] = changed
        check("execution_rejects_drift_" + key, not validate_task_authorization(bad_exec)[0])
    bad = copy.deepcopy(compiled); bad["retrieval_task"]["acceptance_contract"]["count_threshold"] = 1
    check("request_mutation_after_compile_rejected", validate_task_authorization(bad)[1] == "execution_request_hash_mismatch")
    other = copy.deepcopy(request); other["request_id"] += "-OTHER"
    check("same_task_different_request_rejected", not SUFF.validate_package(suff, other)["passed"])
    conflict = copy.deepcopy(request); conflict["sufficiency"] = {"acceptance_mode": "quality_sufficiency"}
    try:
        compile_request(conflict, plan); rejected = False
    except ValueError as exc:
        rejected = "request_contract_conflict" in str(exc)
    check("conflicting_input_copies_rejected", rejected)
    missing = copy.deepcopy(request); del missing["acceptance_contract"]["count_threshold"]
    try:
        compile_request(missing, plan); rejected = False
    except ValueError:
        rejected = True
    check("missing_original_criterion_not_inferred", rejected)
    scope_request = copy.deepcopy(request)
    scope_request["incremental_policy"]["in_scope_iteration_allowed"] = True
    scope_request["stop_conditions"] = request["stop_conditions"][:-1]
    iteration = copy.deepcopy(suff); iteration["batch"].update(batch_state="in_scope_iteration_batch", parent_batch_id="B0")
    iteration["source_request_sha256"] = canonical_sha256(scope_request)
    iteration_plan = {**copy.deepcopy(plan), "batch_state": "in_scope_iteration_batch", "parent_batch_id": "B0"}
    iteration["execution_request"] = compile_request(scope_request, iteration_plan)
    check("in_scope_iteration_keeps_extension_false", SUFF.validate_package(iteration, scope_request)["passed"] and not iteration["consumer_contract"]["adaptive_extension"]["authorized"])
    denied = copy.deepcopy(request); denied["incremental_policy"]["in_scope_iteration_allowed"] = False
    forbidden = copy.deepcopy(iteration); forbidden["source_request_sha256"] = canonical_sha256(denied)
    forbidden["execution_request"] = copy.deepcopy(iteration["execution_request"])
    forbidden["execution_request"].update(retrieval_task=denied, source_request_sha256=canonical_sha256(denied))
    check("explicit_iteration_stop_respected", not SUFF.validate_package(forbidden, denied)["passed"])
    outside = copy.deepcopy(compiled); outside["scope_expansion_requested"] = True
    check("scope_expansion_requires_decision", validate_task_authorization(outside)[1] == "retrieval_scope_expansion_requires_decision")
    extension = copy.deepcopy(suff); extension["batch"].update(batch_state="approved_incremental_batch", parent_batch_id="B0")
    extension["consumer_contract"]["adaptive_extension"] = {"authorized": True, "authorization_ref": "owner-decision-example", "maximum_incremental_batches": 1, "time_limit_minutes": 30, "cost_limit": "zero"}
    check("extension_cannot_self_authorize", not SUFF.validate_package(extension, request)["passed"])
    extension["continuation_adoption"] = {"schema": "residential.upstream_adoption_receipt.v0.2", "request_id": request["request_id"], "task_id": request["task_id"], "project_id": request["project_id"], "accepted_by": "residential_production_owner", "incremental_decision": {"decision": "authorize_incremental", "authorized_query_ids": [query["query_id"]], "limits": "one synthetic batch, no cost"}}
    extension["continuation_binding"] = {"schema": "continuation_authorization_binding.v1",
        "request_sha256": canonical_sha256(request), "adoption_sha256": canonical_sha256(extension["continuation_adoption"]),
        "limits_quote": extension["continuation_adoption"]["incremental_decision"]["limits"],
        "adaptive_extension": copy.deepcopy(extension["consumer_contract"]["adaptive_extension"])}
    approved_plan = {**copy.deepcopy(plan), "batch_state": "approved_incremental_batch", "parent_batch_id": "B0",
        "continuation_adoption": copy.deepcopy(extension["continuation_adoption"]),
        "continuation_binding": copy.deepcopy(extension["continuation_binding"]),
        "adaptive_extension": copy.deepcopy(extension["consumer_contract"]["adaptive_extension"])}
    extension["execution_request"] = compile_request(request, approved_plan)
    check("separate_owner_decision_preserves_frozen_request", SUFF.validate_package(extension, request)["passed"] and canonical_sha256(request) == before and not request["incremental_policy"]["execution_authorized"])
    extension["continuation_adoption"]["incremental_decision"]["authorized_query_ids"] = ["wrong-query"]
    check("continuation_query_scope_checked", not SUFF.validate_package(extension, request)["passed"])
    if PORTABLE:
        from package_evidence import package
        from validate_public_evidence import validate
        from check_portable_channel_preflight import _collect_forbidden
        draft = json.loads((FIXTURES / "draft-envelope.json").read_text())
        envelope, result = package(draft, request, suff)
        check("bound_packager_and_validator_pass", result["status"] == "pass" and result["production_binding_verified"])
        check("packaging_preserves_evidence_and_gaps", all(envelope[k] == draft[k] for k in ("sources", "items", "negative_hits", "conflicts", "gaps", "stop_reason", "upstream_status")) and canonical_sha256(request) == before)
        for mode in ("quality_sufficiency", "quality", "unknown"):
            bad = copy.deepcopy(draft); bad["query_execution"]["acceptance_mode"] = mode
            check("packager_rejects_mode_" + mode, package(bad, request, suff)[1]["status"] == "fail")
        bad_suff = copy.deepcopy(suff); bad_suff["receipt"]["cumulative_evidence"].append({"evidence_item_id": "ITEM-G1"})
        check("gaps_are_not_qualified_evidence", package(draft, request, bad_suff)[1]["status"] == "fail")
        check("legacy_read_only_is_explicit", validate(draft)["status"] == "fail" and validate(draft, allow_legacy_unbound=True)["validation_scope"] == "legacy_structure_only")
        check("legacy_draft_not_production_repackaged", package(draft)[1]["status"] == "fail")
        bad = copy.deepcopy(envelope); bad["contract_binding"]["request_sha256"] = "0" * 64
        check("legacy_flag_cannot_ignore_bad_binding", validate(bad, request, suff, allow_legacy_unbound=True)["status"] == "fail")
        check("business_authorization_enum_is_not_a_credential", not _collect_forbidden({"retrieval_task": request}))
        bad_request = copy.deepcopy(request); bad_request["authorization"] = "Bearer synthetic-forbidden-value"
        check("authorization_header_still_rejected", bool(_collect_forbidden({"retrieval_task": bad_request})))
    report = {"schema": "request_contract_binding_tests.v1", "status": "pass" if all(c["passed"] for c in cases) else "fail", "case_count": len(cases), "failure_count": sum(not c["passed"] for c in cases), "cases": cases, "network_accessed": False, "platform_opened": False, "external_write_executed": False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
