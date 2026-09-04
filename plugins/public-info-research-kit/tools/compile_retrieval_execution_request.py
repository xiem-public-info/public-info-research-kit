#!/usr/bin/env python3
"""Compile a received business task and owner plan; never infer machine readiness."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from retrieval_task_policy import validate_task_authorization


def compile_request(task: dict, plan: dict) -> dict:
    channel = plan['channel']
    request = dict(schema='portable_channel_request.v1', task_id=task['task_id'],
        retrieval_task=copy.deepcopy(task), channel=channel, channel_profile=f'{channel}.v1',
        execution_owner='installed_public_info_research_kit',
        downstream_business_owner=task.get('business_owner', 'requesting_user_or_downstream_project'),
        business_question=task['business_question'], intent=plan.get('intent', 'business_research'),
        evidence_type='public_evidence', usage_boundary=task.get('usage_boundary', 'internal_research'),
        stop_condition=plan.get('stop_condition') or task.get('stop_condition') or 'Stop when sufficient, no material gain, or safety boundary reached',
        query_plan_schema='social_query_plan.v1', query_plan=copy.deepcopy(plan['queries']))
    for key in ('surface_id', 'scope_expansion_requested', 'budget_exhausted', 'operation', 'usage', 'shared_gui', 'computer_use', 'end_user_session'):
        if key in plan:
            request[key] = copy.deepcopy(plan[key])
    for query in request['query_plan']:
        query.setdefault('platform', channel)
        if 'surface_id' in plan:
            query.setdefault('surface_id', plan['surface_id'])
    valid, status = validate_task_authorization(request)
    if not valid:
        raise ValueError(status)
    if channel == 'wechat' and plan.get('surface_id') == 'wechat_ai_search':
        return dict(schema='wechat_ai_search_gate_request.v1', task_id=task['task_id'],
            channel='wechat', platform='wechat', aggregate_surface_id='wechat_ai_search',
            aggregate_surface_contract_version='WECHAT-AI-SEARCH-SURFACE-V1',
            execution_owner=request['execution_owner'], downstream_business_owner=request['downstream_business_owner'],
            business_question=task['business_question'],
            aggregate_purpose=plan.get('aggregate_purpose', 'original_source_navigation'),
            ordinary_original_source_surfaces=['wechat_global_article_results'],
            aggregate_answer_evidence_allowed=False, live_execution_requested=True,
            real_gui_validated=False, owner_request=request)
    return request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        request = compile_request(json.loads(args.task.read_text()), json.loads(args.plan.read_text()))
    except (ValueError, KeyError, TypeError) as error:
        print(json.dumps({'passed': False, 'status': str(error)})); return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(request, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'passed': True, 'status': 'compiled_not_executed'}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
