#!/usr/bin/env python3
"""Actual execution, native task identity and historical-read-only regressions."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from compile_retrieval_execution_request import compile_request
from package_evidence import package
from request_contract import canonical_sha256, make_binding
from retrieval_task_policy import validate_execution_request
from validate_adaptive_query_sufficiency import validate_package
from validate_public_evidence import validate
from check_portable_channel_preflight import validate as preflight
from run_portable_channel_preflight import base_request


def main():
    fixture = ROOT / "tests/fixtures/residential-contract-binding"
    read = lambda name: json.loads((fixture / name).read_text())
    original, old_suff, draft = map(read, ("request.json", "sufficiency-input.json", "draft-envelope.json"))
    original_hash = canonical_sha256(original)
    query = old_suff["batch"]["queries"][0]
    plan = {"channel": "public_web", "queries": [{"query_id": query["query_id"],
        "exact_query_text": query["exact_query_text"], "execution_state": "frozen"}]}
    execution = compile_request(original, plan)
    actual = {**copy.deepcopy(old_suff), "execution_request": copy.deepcopy(execution)}
    cases = []

    def check(name, passed, detail=None):
        cases.append({"case_id": name, "passed": bool(passed), "detail": detail})

    check("bound_actual_execution_passes", validate_package(actual, original)["production_binding_verified"])
    check("missing_original_not_a_live_bypass", not validate_package(actual)["passed"])
    check("legacy_flag_cannot_bypass_bound_original", not validate_package(actual, allow_legacy_unbound=True)["passed"])
    check("old_record_requires_actual_execution_for_new_package", package(draft, original, old_suff)[1]["status"] == "fail")
    for name, mutation in (
        ("missing_execution", lambda value: value.pop("execution_request")),
        ("missing_execution_hash", lambda value: value["execution_request"].pop("source_request_sha256")),
        ("changed_batch_state", lambda value: value["execution_request"].update(batch_state="proposed_incremental_batch")),
        ("changed_parent", lambda value: value["execution_request"].update(parent_batch_id="unexpected-parent")),
        ("changed_query", lambda value: value["execution_request"]["query_plan"][0].update(exact_query_text="different")),
        ("unfrozen_query", lambda value: value["execution_request"]["query_plan"][0].update(execution_state="proposed_incremental")),
    ):
        bad = copy.deepcopy(actual); mutation(bad)
        check(name, not validate_package(bad, original)["passed"])

    # Create this separate native fixture before freezing it. No request id is added.
    native = {"task_id": "NATIVE-OFFLINE-001", "project_id": original["project_id"],
        "business_question": original["business_question"], "subjects": ["Example project"],
        "business_owner": "native_business_owner", "stop_condition": "先完成这一批，收到后续决定再继续",
        "in_scope_iteration_allowed": False, "sufficiency": copy.deepcopy(old_suff["consumer_contract"])}
    native_hash = canonical_sha256(native)
    compiled = compile_request(native, plan)
    check("native_owner_and_natural_stop_preserved", compiled["downstream_business_owner"] == native["business_owner"]
          and compiled["stop_condition"] == native["stop_condition"])
    check("native_request_identity_is_read_only_fallback", compiled["request_id"] == native["task_id"]
          and "request_id" not in compiled["retrieval_task"])
    native_suff = copy.deepcopy(actual)
    native_suff.update(task_id=native["task_id"], request_id=native["task_id"], source_request_sha256=native_hash,
                       execution_request=compiled)
    native_draft = copy.deepcopy(draft)
    native_draft.update(task_id=native["task_id"], request_id=native["task_id"])
    native_envelope, outcome = package(native_draft, native, native_suff)
    check("native_no_request_id_end_to_end", outcome["status"] == "pass" and outcome["production_binding_verified"], outcome)
    wrong = copy.deepcopy(native_envelope); wrong["request_id"] = "unrelated"
    check("native_fallback_does_not_allow_other_request", validate(wrong, native, native_suff)["status"] == "fail")
    wrong = copy.deepcopy(compiled); wrong["stop_condition"] = "continue indefinitely"
    check("native_natural_stop_cannot_be_rewritten", not validate_execution_request(wrong, native)[0])
    try:
        compile_request(native, {**plan, "batch_state": "in_scope_iteration_batch", "parent_batch_id": "B0"})
        rejected = False
    except ValueError:
        rejected = True
    check("native_explicit_iteration_denial", rejected)

    # The Owner record stays separate from the frozen native request.
    decision = {"schema": "native_owner_decision.v1", "request_id": native["task_id"],
        "task_id": native["task_id"], "project_id": native["project_id"], "accepted_by": native["business_owner"],
        "incremental_decision": {"decision": "authorize_incremental", "authorized_query_ids": [query["query_id"]],
                                 "limits": "One synthetic batch, thirty minutes, zero cost"}}
    extension = {"authorized": True, "authorization_ref": "synthetic-native-owner-decision", "maximum_incremental_batches": 1,
                 "time_limit_minutes": 30, "cost_limit": "zero"}
    sidecar = {"schema": "continuation_authorization_binding.v1", "request_sha256": native_hash,
        "adoption_sha256": canonical_sha256(decision), "limits_quote": decision["incremental_decision"]["limits"],
        "adaptive_extension": copy.deepcopy(extension)}
    approved = {**copy.deepcopy(plan), "batch_state": "approved_incremental_batch", "parent_batch_id": "B0",
                "continuation_adoption": decision, "continuation_binding": sidecar, "adaptive_extension": extension}
    continued = compile_request(native, approved)
    check("native_separate_owner_authority_works", validate_execution_request(continued, native)[0])
    wrong = copy.deepcopy(continued); wrong["continuation_adoption"]["accepted_by"] = "residential_production_owner"
    wrong["continuation_binding"]["adoption_sha256"] = canonical_sha256(wrong["continuation_adoption"])
    check("native_owner_not_replaced_by_residential_owner", not validate_execution_request(wrong, native)[0])
    wrong = copy.deepcopy(continued); wrong["usage"] = {"incremental_batches": 1}
    check("approved_batch_budget_exhaustion", not validate_execution_request(wrong, native)[0])
    check("native_original_not_rewritten", canonical_sha256(native) == native_hash and "request_id" not in native)

    historical = {**copy.deepcopy(draft), "contract_binding": make_binding(original, old_suff)}
    result = validate(historical, original, old_suff, historical_read_only=True)
    check("historical_bound_shape_is_read_only", result["status"] == "pass" and not result["production_binding_verified"])
    check("history_flag_without_sources_not_production", not validate(historical, historical_read_only=True)["production_binding_verified"])
    malformed_results = []
    for malformed in ("malformed", {**historical["contract_binding"], "acceptance_contract": []}):
        wrong = copy.deepcopy(historical); wrong["contract_binding"] = malformed
        result = validate(wrong, original, old_suff, historical_read_only=True)
        malformed_results.append(result["status"] == "fail" and any(error.startswith("contract_binding_invalid") for error in result["errors"]))
    check("malformed_history_binding_structured_rejection", all(malformed_results))
    wrong = copy.deepcopy(old_suff); wrong["consumer_contract"]["count_threshold"] = 1
    check("historical_hash_corruption_rejected", validate(historical, original, wrong, historical_read_only=True)["status"] == "fail")
    gate = base_request(); gate.pop("retrieval_task")
    check("legacy_live_gate_without_original_cannot_execute", not preflight(gate, require_live=True)["passed"])

    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        task_path = temporary / "request.json"; task_path.write_text(json.dumps(original))
        execution_path = temporary / "execution.json"
        for name, value, expected in (
            ("cli_actual_execution", execution, True),
            ("cli_missing_hash", {key: val for key, val in execution.items() if key != "source_request_sha256"}, False),
        ):
            execution_path.write_text(json.dumps(value))
            completed = subprocess.run([sys.executable, str(ROOT / "tools/compile_retrieval_execution_request.py"),
                "--task", str(task_path), "--check-execution", str(execution_path)], capture_output=True, text=True)
            result = json.loads(completed.stdout)
            check(name, result["passed"] is expected and (completed.returncode == 0) is expected)
    check("original_residential_fixture_unchanged", canonical_sha256(original) == original_hash)
    report = {"status": "pass" if all(case["passed"] for case in cases) else "fail", "case_count": len(cases),
        "failure_count": sum(not case["passed"] for case in cases), "cases": cases,
        "network_accessed": False, "platform_opened": False, "external_write_executed": False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(report["status"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
