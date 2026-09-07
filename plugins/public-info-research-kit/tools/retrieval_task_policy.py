"""D-293 task-level retrieval authority; no platform actions or capability claims."""
from __future__ import annotations

from typing import Any

POLICY_ID = "TASK-DRIVEN-RETRIEVAL-AUTHORITY-V1"
CHANNEL_ALIASES = {
    "wechat_search": "wechat", "xhs_search": "xhs",
    "official_origin": "public_web", "map": "map_gis", "spatial": "map_gis",
}


def task_subjects(task: dict[str, Any]) -> list:
    """Accept the old C-32 singular spelling without changing the received task."""
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
