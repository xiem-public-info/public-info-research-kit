#!/usr/bin/env python3
"""D-293 portable task, AI, scope and iteration regression cases; no GUI actions."""
import copy
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from compile_retrieval_execution_request import compile_request
from check_portable_channel_preflight import validate as owner
from check_wechat_ai_search_gate_preflight import validate as ai
from retrieval_task_policy import validate_task_authorization
from validate_adaptive_query_sufficiency import validate_package, validate_applicability
from validate_d292_research_orchestration import validate as orchestration
from run_portable_channel_preflight import base_request


def main():
    cases=[]
    def check(name, value): cases.append({'case_id':name,'passed':bool(value)})
    base=base_request(); task={'task_id':base['task_id'],'business_question':base['business_question'],'subjects':['Example project']}
    plan={k:copy.deepcopy(v) for k,v in base.items() if k in ('channel','shared_gui','computer_use','end_user_session','stop_condition')}
    plan['queries']=base['query_plan']
    singular=copy.deepcopy(task); singular['subject']=singular.pop('subjects')[0]
    singular['sufficiency']={'policy':'d237_required','acceptance_mode':'quality_sufficiency','stop_condition':'original task stop'}
    compiled=compile_request(singular,plan)
    check('singular_subject_preserved',compiled['subjects']==[singular['subject']] and compiled['retrieval_task']==singular)
    check('business_sufficiency_mapped',validate_applicability(compiled['sufficiency_applicability'])['passed'])
    check('original_stop_wins',compiled['stop_condition']=='original task stop')
    check('missing_criteria_not_invented',validate_applicability(compile_request(task,plan)['sufficiency_applicability'])['status']=='d237_consumer_contract_required')
    for surface in ('wechat_ai_search','wechat_global_article_results','wechat_video_search','wechat_mini_program_search','wechat_public_account_search'):
        selected=copy.deepcopy(plan); selected['surface_id']=surface
        request=compile_request(task,selected)
        receipt=ai(request,require_live=True) if surface=='wechat_ai_search' else owner(request,require_live=True)
        check(surface,receipt['passed'] and receipt['execution_authorized'] and not receipt['platform_opened'])
    plan['surface_id']='wechat_ai_search'
    request=compile_request(task,plan)
    for purpose in ('semantic_clarification','next_query_planning'):
        r=copy.deepcopy(request); r['aggregate_purpose']=purpose
        check(purpose, ai(r,require_live=True)['execution_authorized'])
    for name, field, value in [('excluded_channel','excluded_channels',['wechat']),('excluded_surface','excluded_surfaces',['wechat_ai_search']),('stopped','status','stopped'),('explicit_denial','authorized',False),('query_budget','limits',{'max_queries':0})]:
        r=copy.deepcopy(request); r['owner_request']['retrieval_task'][field]=value
        check(name,not ai(r,require_live=True)['passed'])
    for name,field,value in [('wrong_task','task_id','other'),('wrong_surface','surface_id','wechat_global_article_results'),('expansion','scope_expansion_requested',True),('external_write','operation','publish')]:
        r=copy.deepcopy(request); r['owner_request'][field]=value
        check(name,not ai(r,require_live=True)['passed'])
    for name,section,field in [('tool_gap','computer_use','available'),('permission_gap','computer_use','permissions_ready'),('login_gap','end_user_session','logged_in')]:
        r=copy.deepcopy(request); r['owner_request'][section][field]=False
        check(name,not ai(r,require_live=True)['passed'])
    r=copy.deepcopy(request); r['owner_request']['shared_gui']['lease_state']='planned'; check('gui_busy',not ai(r,require_live=True)['passed'])
    r=copy.deepcopy(request); r['real_gui_validated']=True; check('false_live_claim',not ai(r)['passed'])
    r=copy.deepcopy(request); r['owner_request']['query_plan'][0]['execution_state']='proposed_incremental'; check('unfrozen_query',not ai(r,require_live=True)['passed'])
    r=copy.deepcopy(request); r['owner_request']['retrieval_task']['channel_scope']=['public_web']; check('legacy_hints',ai(r,require_live=True)['passed'])
    r['owner_request']['retrieval_task']['channel_scope_exclusive']=True; check('explicit_exclusive',not ai(r,require_live=True)['passed'])
    r=copy.deepcopy(request); r['owner_request']['live_gate']={'authorized':False,'approved_by':'end_user','read_only':True,'stop_condition':'stop'}; check('explicit_gate_denial',not ai(r,require_live=True)['passed'])
    r=copy.deepcopy(request); r['owner_request']['query_plan'][0]['acceptance']['minimum_actual_opens']=0; check('ai_zero_article_opens',ai(r,require_live=True)['passed'])
    fixture=json.loads((ROOT/'tests/fixtures/golden-tasks/golden_research_partial.json').read_text())
    fixture['batch'].update(batch_state='in_scope_iteration_batch',parent_batch_id='parent')
    ex=copy.deepcopy(base); ex.pop('live_gate'); ex['task_id']=fixture['task_id']; ex['retrieval_task']={**task,'task_id':fixture['task_id']}; ex['query_plan']=[{**q,'execution_state':'frozen'} for q in fixture['batch']['queries']]
    fixture['execution_request']=ex; fixture['receipt']['needs_downstream_authorization']=False
    check('in_scope_iteration_without_extension',validate_package(fixture)['passed'])
    bad=copy.deepcopy(fixture); bad['execution_request']['query_plan'][0]['exact_query_text']='different'; check('iteration_query_binding',not validate_package(bad)['passed'])
    bad=copy.deepcopy(fixture); bad['execution_request']['scope_expansion_requested']=True; check('iteration_scope_expansion',not validate_package(bad)['passed'])
    d292=json.loads((ROOT/'tests/fixtures/d292-research-orchestration/valid.json').read_text())
    d292['task_id']=fixture['task_id']; d292['in_scope_iteration_package']=fixture
    d292['first_return']['merged_increment_proposal'].update(downstream_authorization_required=False, execution_authorized=True)
    check('d292_in_scope_iteration',orchestration(d292)['passed'])
    d292['in_scope_iteration_package']=bad
    check('d292_expansion_rejected',not orchestration(d292)['passed'])

    direct_task = {"task_id": "direct-read", "business_question": "Read https://mp.weixin.qq.com/s/example", "subjects": ["article"], "stop_condition": "Stop after reading the supplied article"}
    direct_plan = {"channel": "wechat", "queries": [], "simple_direct_retrieval_exemption": {"exemption_type": "known_url_read", "evidence_target": "https://mp.weixin.qq.com/s/example"}}
    direct_request = compile_request(direct_task, direct_plan)
    check("direct_read_no_extra_user_exemption", validate_applicability(direct_request["sufficiency_applicability"])["passed"] and not validate_applicability(direct_request["sufficiency_applicability"])["d237_required"])
    check("direct_read_original_request_preserved", direct_request["retrieval_task"] == direct_task and direct_request["sufficiency_applicability"]["simple_direct_retrieval_exemption"]["human_authorization_ref"] == "received_task:direct-read")
    for characteristic in ("multiple_independent_queries", "comparative_or_pattern_judgment", "support_and_counterevidence_required", "adaptive_extension_possible"):
        complex_plan = copy.deepcopy(direct_plan); complex_plan["research_characteristics"] = [characteristic]
        check("direct_url_does_not_exempt_" + characteristic, not validate_applicability(compile_request(direct_task, complex_plan)["sufficiency_applicability"])["passed"])
    required = copy.deepcopy(direct_task); required["sufficiency"] = {"policy": "d237_required", "acceptance_mode": "quality_sufficiency"}
    check("explicit_research_standard_preserved", validate_applicability(compile_request(required, direct_plan)["sufficiency_applicability"])["d237_required"])
    report={'status':'pass' if all(c['passed'] for c in cases) else 'fail','case_count':len(cases),'failure_count':sum(not c['passed'] for c in cases),'cases':cases,'platform_opened':False,'network_accessed':False}
    print(json.dumps(report,indent=2)); return int(report['status']!='pass')
if __name__=='__main__': raise SystemExit(main())
