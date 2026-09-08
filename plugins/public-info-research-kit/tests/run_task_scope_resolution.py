#!/usr/bin/env python3
"""Reviewed interpretations -> compiler -> portable preflight/sufficiency.

These fixtures are not a language model or evidence of live execution stability.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from compile_retrieval_execution_request import compile_request
from retrieval_task_policy import validate_scope_interpretation
from validate_adaptive_query_sufficiency import validate_applicability
from check_portable_channel_preflight import validate
from run_portable_channel_preflight import base_request

QA, EVIDENCE = 'ROUTE-COMPETITOR-QA', 'ROUTE-PROJECT-DEEPDIVE'
cases = []


def interpreted(text, routes, domain='residential', research=False, exclusions=()):
    task = dict(task_id='example', business_question=text, business_domain=domain, subjects=['项目甲'])
    plan = dict(channel='xhs', queries=[], scope_interpretation=dict(
        task_id=task['task_id'], request_text=text, domain=domain, research_required=research,
        actions=[dict(id=str(i), request_quote=text, route_id=route) for i,route in enumerate(routes)],
        exclusions=[dict(route_id=route, request_quote=text) for route in exclusions], unresolved_items=[]),
        action_coverage={str(i):dict(disposition='execute') for i in range(len(routes))})
    return task, plan


for text in ['本轮先只收集住宅竞品户型图片', '帮我收集这些住宅竞品的户型图即可',
             '下游给出住宅竞品名单，本轮收集户型图片，不做资格复核。']:
    t,p=interpreted(text,[EVIDENCE],exclusions=(QA,))
    c=compile_request(t,p)
    assert c['retrieval_task']==t and c['scope_consistency']['execution_routes']==[EVIDENCE]
    cases.append(dict(case='light_equivalence:'+text,passed=True))

for text in ['不仅取住宅竞品图片，还要复核资格', '先复核住宅竞品资格，再取图片']:
    t,p=interpreted(text,[EVIDENCE,QA],research=True)
    assert QA in compile_request(t,p)['scope_consistency']['execution_routes']
    cases.append(dict(case='additive:'+text,passed=True))

t,p=interpreted('SaaS竞品QA与分类',[EVIDENCE],domain='non_residential',research=True)
assert compile_request(t,p)['scope_consistency']['domain']=='non_residential'
cases.append(dict(case='domain_not_generic_qa_keyword',passed=True))
t,p=interpreted('补项目甲的供应与竞争威胁',[QA],research=True)
assert compile_request(t,p)['scope_consistency']['domain']=='residential'
cases.append(dict(case='inherited_domain_without_housing_word',passed=True))

for name in ['excluded_action','omitted_action','wrong_domain','false_reuse','unsupported_route','lowered_research']:
    t,p=interpreted('住宅竞品只取图，不做资格复核',[EVIDENCE],exclusions=(QA,))
    if name=='excluded_action': p['scope_interpretation']['actions'][0]['route_id']=QA
    if name=='omitted_action': p['action_coverage']={}
    if name=='wrong_domain': p['scope_interpretation']['domain']='non_residential'
    if name=='false_reuse': p['action_coverage']['0']['disposition']='reuse'
    if name=='unsupported_route': p['scope_interpretation']['actions'][0]['route_id']='ROUTE-UNKNOWN'
    if name=='lowered_research': t['sufficiency']={'policy':'d237_required'}
    assert validate_scope_interpretation(t,p)['status']=='scope_conflict'
    try: compile_request(t,p)
    except ValueError as e: assert 'scope_conflict:' in str(e)
    else: raise AssertionError(name)
    cases.append(dict(case=name,passed=True))

t,p=interpreted('先取住宅图片，其他要求待解释',[EVIDENCE])
p['scope_interpretation']['unresolved_items']=['其他要求待解释']
c=compile_request(t,p)
assert c['scope_consistency']['status']=='owner_scope_pending'
assert c['scope_consistency']['execution_routes']==[EVIDENCE]
assert not c['scope_consistency']['task_completion_claim_allowed']
cases.append(dict(case='pending_does_not_expand',passed=True))

t,p=interpreted('读取指定文章 https://example.org/article',['ROUTE-WECHAT-KNOWN-URL'])
p['channel']='wechat'
p['simple_direct_retrieval_exemption']={'exemption_type':'known_url_read','evidence_target':'https://example.org/article','stop_condition':'Stop after supplied article'}
checked=validate_applicability(compile_request(t,p)['sufficiency_applicability'])
assert checked['passed'] and not checked['d237_required']
cases.append(dict(case='bounded_read_actual_consumer',passed=True))

t,p=interpreted('研究住宅竞品当前供应与资格',[QA],research=True)
t['sufficiency']={'policy':'d237_required','acceptance_mode':'quality_sufficiency','qualification_policy':'原文对应对象','diversity_policy':'同源去重'}
fixture=base_request('xhs')
for key in ('shared_gui','computer_use','end_user_session'): p[key]=copy.deepcopy(fixture[key])
p['queries']=copy.deepcopy(fixture['query_plan']);p['queries'][0]['action_id']='0'
c=compile_request(t,p)
assert validate_applicability(c['sufficiency_applicability'])['passed']
checked=validate(c,require_live=True)
assert checked['passed'] and checked['execution_entrypoint']=='cua.getApp'
assert not checked['actual_tool_execution_verified'] and not checked['platform_opened']
cases.append(dict(case='scope_reaches_channel_preflight_without_execution_claim',passed=True))

print(json.dumps(dict(status='pass',case_count=len(cases),failure_count=0,cases=cases,
    real_model_reliability_tested=False,platform_opened=False,external_write_executed=False),ensure_ascii=False,indent=2))
