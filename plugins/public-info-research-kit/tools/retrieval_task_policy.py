"""D-293 task-level retrieval authority; no platform actions or capability claims."""
from __future__ import annotations

from typing import Any
from request_contract import (normalize_request, canonical_sha256, same, REQUIREMENT_FIELDS,
                              request_identity, declared_stop, batch_authority_errors)

POLICY_ID = "TASK-DRIVEN-RETRIEVAL-AUTHORITY-V1"
CHANNEL_ALIASES = {
    "wechat_search": "wechat", "xhs_search": "xhs",
    "official_origin": "public_web", "map": "map_gis", "spatial": "map_gis",
}
# Existing retrieval capability IDs, not natural-language phrases or a new router.
SCOPE_ROUTE_IDS = {
    "ROUTE-CUSTOMER-RESEARCH-UPSTREAM", "ROUTE-COMPETITOR-QA", "ROUTE-PROJECT-DEEPDIVE",
    "ROUTE-XHS", "ROUTE-WECHAT-AI-SEARCH-GATE", "ROUTE-WECHAT-KNOWN-URL",
    "ROUTE-WECHAT-DESKTOP", "ROUTE-VERTICAL-MINI-PROGRAM", "ROUTE-OFFICIAL-RESOLVER",
    "ROUTE-PLAYWRIGHT-DYNAMIC", "ROUTE-AUTHORIZED-SOURCE-GAP", "ROUTE-PUBLIC-VIDEO",
    "ROUTE-RSSHUB-PUBLIC", "ROUTE-MAP",
}


def explicit_research_requirements(payload: dict[str, Any]) -> list[str]:
    """Hard business requirements survive direct reading; optional targets do not."""
    fields = ("count_threshold", "quality_criteria", "diversity_requirements", "required_object_ids")
    policy = payload.get("qualification_policy")
    sources = (payload, policy) if isinstance(policy, dict) else (payload,)

    def has_requirement(value: object) -> bool:
        values = value.values() if isinstance(value, dict) else value if isinstance(value, list) else (value,)
        return any(item not in (None, "", [], {}, False) for item in values)

    return [field for field in fields if any(has_requirement(source.get(field)) for source in sources)]


def task_subjects(task: dict[str, Any]) -> list:
    """Accept the old C-32 singular spelling without changing the received task."""
    task = normalize_request(task)
    value = task.get("subjects") if "subjects" in task else task.get("subject")
    if isinstance(value, (str, dict)) and value:
        return [value]
    return value if isinstance(value, list) else []


def validate_task_authorization(request: dict[str, Any]) -> tuple[bool, str]:
    """Validate the received business contract, not a self-declared allow flag.

    The owner attaches the actual received contract to its compiled execution
    request. Content from a webpage/AI answer is never a task contract.
    Semantic relevance and real capability remain the owner's responsibility.
    """
    task = request.get("retrieval_task")
    if not isinstance(task, dict):
        return False, "retrieval_task_contract_required"
    try:
        original_task = task
        task = normalize_request(task)
    except (ValueError, TypeError) as exc:
        return False, str(exc)
    if "source_request_sha256" not in request or not isinstance(request.get("sufficiency_applicability"), dict):
        return False, "execution_binding_required"
    if request.get("request_id") != request_identity(original_task):
        return False, "execution_request_id_mismatch"
    if "source_request_sha256" in request and request["source_request_sha256"] != canonical_sha256(original_task):
        return False, "execution_request_hash_mismatch"
    compiled = request.get("sufficiency_applicability")
    if isinstance(compiled, dict):
        for key in REQUIREMENT_FIELDS:
            expected = task.get("sufficiency", {})
            if key == "research_characteristics" and isinstance(expected.get(key), list) and isinstance(compiled.get(key), list) and set(expected[key]).issubset(compiled[key]):
                continue
            if key in expected and (key not in compiled or not same(compiled[key], expected[key])):
                return False, "execution_contract_mismatch:" + key
    if not task.get("task_id") or task["task_id"] != request.get("task_id"):
        return False, "retrieval_task_scope_mismatch"
    if not isinstance(task.get("business_question"), str) or not task["business_question"].strip():
        return False, "retrieval_business_question_required"
    if not task_subjects(task):
        return False, "retrieval_subjects_required"
    if task.get("authorized") is False or task.get("status") in {"cancelled", "paused", "stopped"}:
        return False, "retrieval_task_stopped"
    if not request.get("stop_condition"):
        return False, "retrieval_stop_condition_required"
    if declared_stop(task) and request["stop_condition"] != declared_stop(task):
        return False, "execution_stop_condition_mismatch"
    if request.get("subjects") != task_subjects(task):
        return False, "execution_subjects_mismatch"
    if request.get("business_question") != task["business_question"]:
        return False, "execution_business_question_mismatch"
    batch_errors = batch_authority_errors(original_task, request)
    if batch_errors:
        return False, batch_errors[0]
    for field in ("scope_expansion_requested", "budget_exhausted"):
        if field in request and not isinstance(request[field], bool):
            return False, "retrieval_scope_invalid"
    channel = CHANNEL_ALIASES.get(request.get("channel"), request.get("channel"))
    surface = request.get("aggregate_surface_id") or request.get("surface_id")
    for field in ("excluded_channels", "excluded_surfaces", "channel_scope"):
        value = task.get(field)
        if value is not None and (not isinstance(value, list) or any(not isinstance(x, str) for x in value)):
            return False, "retrieval_scope_invalid"
    excluded = {CHANNEL_ALIASES.get(x, x) for x in task.get("excluded_channels", [])}
    if channel in excluded or surface in task.get("excluded_surfaces", []):
        return False, "retrieval_scope_excluded"
    for query in request.get("query_plan", []):
        if isinstance(query, dict) and query.get("surface_id") in task.get("excluded_surfaces", []):
            return False, "retrieval_scope_excluded"
    # Old channel lists are planning hints; only an explicitly exclusive scope
    # narrows the D-293 default. Do not reintroduce per-channel approval by alias.
    scope = task.get("channel_scope")
    if task.get("channel_scope_exclusive") is True and scope is not None and "all" not in scope:
        if channel not in {CHANNEL_ALIASES.get(x, x) for x in scope}:
            return False, "retrieval_scope_excluded"
    limits = task.get("limits", {})
    usage = request.get("usage", {})
    if not isinstance(limits, dict) or not isinstance(usage, dict):
        return False, "retrieval_budget_invalid"
    for limit_key, used_key in (("max_queries", "queries"), ("max_minutes", "minutes"), ("max_cost", "cost")):
        if limit_key not in limits:
            continue
        limit, used = limits[limit_key], usage.get(used_key, 0)
        if any(not isinstance(x, (int, float)) or isinstance(x, bool) or x < 0 for x in (limit, used)):
            return False, "retrieval_budget_invalid"
        exhausted = used > limit if limit_key == "max_cost" else used >= limit
        if exhausted or (limit_key == "max_queries" and used + len(request.get("query_plan", [])) > limit):
            return False, "retrieval_budget_exhausted"
    if request.get("scope_expansion_requested") is True:
        return False, "retrieval_scope_expansion_requires_decision"
    if request.get("budget_exhausted") is True:
        return False, "retrieval_budget_exhausted"
    if request.get("operation", "public_retrieval") != "public_retrieval":
        return False, "retrieval_operation_not_covered"
    return True, "task_contract_authorized"


def validate_execution_request(request: dict, original_request: dict | None = None) -> tuple[bool, str]:
    """Actual pre-execution check shared by the CLI and channel preflights."""
    if request.get("schema") == "wechat_ai_search_gate_request.v1":
        inner = request.get("owner_request")
        if not isinstance(inner, dict) or any(request.get(key) != inner.get(key) for key in ("task_id", "business_question")):
            return False, "ai_execution_owner_mismatch"
        return validate_execution_request(inner, original_request)
    if original_request is not None and not same(request.get("retrieval_task"), original_request):
        return False, "execution_original_request_mismatch"
    valid, status = validate_task_authorization(request)
    if not valid:
        return valid, status
    if request.get("batch_state") == "proposed_incremental_batch":
        return False, "proposed_batch_not_authorized_for_execution"
    from validate_adaptive_query_sufficiency import validate_applicability
    applicability = validate_applicability(request["sufficiency_applicability"])
    if not applicability["passed"]:
        return False, applicability["status"]
    return True, "execution_contract_checked_not_executed"


def validate_scope_interpretation(task: dict, plan: dict) -> dict:
    """Check an owner's interpretation against its plan; do not parse user prose.

    The model owns semantic completeness and domain interpretation. Exact quotes,
    task binding and action coverage make that interpretation reviewable; they do
    not prove that the model understood the request or verified the evidence.
    """
    task = normalize_request(task)
    scope = plan.get("scope_interpretation")
    result = {"status": "owner_interpretation_required", "errors": [],
              "domain": "unknown", "execution_routes": [], "reuse_routes": [],
              "research_required": False, "unresolved_items": [],
              "task_completion_claim_allowed": False,
              "semantic_understanding_verified": False}
    if scope is None:
        return result
    if not isinstance(scope, dict):
        return {**result, "status": "scope_conflict", "errors": ["scope_interpretation_invalid"]}
    errors = []
    source = task.get("request_text") or task.get("business_question", "")
    if not isinstance(source, str) or not source or not task.get("task_id"):
        return {**result, "status": "scope_conflict", "errors": ["original_request_required"]}
    if scope.get("task_id") != task.get("task_id") or scope.get("request_text") != source:
        errors.append("original_request_binding_mismatch")
    domain = scope.get("domain", "unknown")
    if not isinstance(domain, str) or domain not in {"residential", "non_residential", "unknown"}:
        errors.append("business_domain_invalid")
    inherited_domain = task.get("business_domain")
    if inherited_domain is not None and inherited_domain not in ("residential", "non_residential", "unknown"):
        errors.append("received_business_domain_invalid")
    inherited_known = inherited_domain in ("residential", "non_residential")
    if inherited_known and inherited_domain != domain:
        errors.append("business_domain_conflicts_with_received_context")
    basis = scope.get("domain_basis")
    if not inherited_known and domain != "unknown" and (not isinstance(basis, str) or not basis or basis not in source):
        errors.append("business_domain_basis_required")
    if not isinstance(scope.get("research_required"), bool):
        errors.append("research_requirement_not_interpreted")
    sufficiency = task.get("sufficiency", {})
    if not isinstance(sufficiency, dict):
        errors.append("retrieval_sufficiency_invalid")
        sufficiency = {}
    research_inputs = {**task, **sufficiency}
    queries = plan.get("queries", [])
    if not isinstance(queries, list):
        errors.append("queries_invalid")
        queries = []
    if scope.get("research_required") is False and (
        sufficiency.get("policy", task.get("sufficiency_policy")) == "d237_required"
        or research_inputs.get("acceptance_mode")
        or explicit_research_requirements(research_inputs)
        or research_inputs.get("research_characteristics")
        or plan.get("research_characteristics") or len(queries) > 1
    ):
        errors.append("research_requirement_conflicts_with_task_or_plan")
    if scope.get("research_required") is True and plan.get("simple_direct_retrieval_exemption"):
        errors.append("research_action_conflicts_with_direct_read_exemption")
    actions = scope.get("actions", [])
    exclusions = scope.get("exclusions", [])
    unresolved = scope.get("unresolved_items", [])
    coverage = plan.get("action_coverage", {})
    if (not isinstance(actions, list) or not isinstance(exclusions, list)
            or not isinstance(unresolved, list) or not isinstance(coverage, dict)):
        return {**result, "status": "scope_conflict", "errors": errors + ["scope_collections_invalid"]}
    excluded_routes = set()
    for item in exclusions:
        if (not isinstance(item, dict) or not isinstance(item.get("route_id"), str)
                or item["route_id"] not in SCOPE_ROUTE_IDS
                or not isinstance(item.get("request_quote"), str)
                or not item["request_quote"] or item["request_quote"] not in source):
            errors.append("exclusion_basis_invalid")
        else:
            excluded_routes.add(item["route_id"])
    for item in unresolved:
        if not isinstance(item, str) or not item or item not in source:
            errors.append("unresolved_source_invalid")
    ids = set()
    execution, reuse, deferred = set(), set(), []
    for action in actions:
        if not isinstance(action, dict):
            errors.append("action_invalid")
            continue
        action_id, route_id = action.get("id"), action.get("route_id")
        quote = action.get("request_quote")
        if not isinstance(action_id, str) or not action_id or action_id in ids:
            errors.append("action_id_invalid_or_duplicate")
            continue
        ids.add(action_id)
        if not isinstance(route_id, str) or route_id not in SCOPE_ROUTE_IDS or not isinstance(quote, str) or not quote or quote not in source:
            errors.append("action_basis_invalid")
            continue
        handling = coverage.get(action_id)
        if not isinstance(handling, dict):
            errors.append("action_omitted_from_plan:" + action_id)
            continue
        disposition = handling.get("disposition")
        if disposition in ("execute", "reuse"):
            if route_id in excluded_routes:
                errors.append("planned_action_explicitly_excluded:" + action_id)
            if route_id == "ROUTE-COMPETITOR-QA" and domain == "non_residential":
                errors.append("residential_route_conflicts_with_domain")
            if route_id == "ROUTE-COMPETITOR-QA" and domain == "unknown":
                deferred.append(action_id)
            elif disposition == "execute":
                execution.add(route_id)
            else:
                reuse.add(route_id)
                refs = handling.get("evidence_refs")
                if not (isinstance(refs, list) and refs and all(isinstance(ref, str) and ref.strip() for ref in refs)):
                    errors.append("reuse_evidence_reference_required:" + action_id)
        elif disposition == "defer" and handling.get("reason"):
            deferred.append(action_id)
        else:
            errors.append("action_disposition_invalid:" + action_id)
    if set(coverage) - ids:
        errors.append("unrequested_action_in_plan")
    for query in queries:
        if not isinstance(query, dict) or "action_id" not in query:
            errors.append("query_action_reference_required")
        else:
            query_action = query["action_id"]
            handling = coverage.get(query_action, {}) if isinstance(query_action, str) else {}
            if (not isinstance(query_action, str) or query_action not in ids
                    or not isinstance(handling, dict) or handling.get("disposition") != "execute"
                    or query_action in deferred):
                errors.append("query_not_linked_to_executing_action")
    if not actions and not unresolved:
        errors.append("interpreted_actions_required")
    if errors:
        return {**result, "status": "scope_conflict", "errors": errors, "domain": domain}
    return {**result, "status": "owner_scope_pending" if unresolved or deferred else "scope_consistent",
            "domain": domain, "execution_routes": sorted(execution), "reuse_routes": sorted(reuse),
            "research_required": scope["research_required"], "unresolved_items": unresolved,
            "deferred_action_ids": deferred, "excluded_routes": sorted(excluded_routes),
            "task_completion_claim_allowed": False}
