#!/usr/bin/env python3
"""Check the actual frozen residential rc.8 consumer against this package.

Requires jsonschema and an independently obtained, unchanged consumer checkout.
Uses only its synthetic fixtures; never opens a platform or modifies that checkout.
This integration runner originated in the independent rc.7 candidate review.
"""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,subprocess,sys,tempfile
from jsonschema import Draft202012Validator

parser=argparse.ArgumentParser();parser.add_argument('--producer',type=Path,required=True);parser.add_argument('--consumer',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
producer=args.producer.resolve(); consumer=args.consumer.resolve()
spec=importlib.util.spec_from_file_location('rc8_original_conformance',consumer/'scripts/verify_cross_package_conformance.py'); bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
read=lambda p:json.loads(p.read_text())
sha=lambda v:hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
fixtures=consumer/'fixtures/upstream-exchange'; original=read(fixtures/'request.json'); frozen_bytes=(fixtures/'request.json').read_bytes(); draft=read(fixtures/'public-evidence-envelope.json'); suff=read(fixtures/'sufficiency-input.json'); cases=[]
def check(name,passed,details=None):cases.append({'case':name,'passed':bool(passed),'details':details})
def run(tool,*a):
 p=subprocess.run([sys.executable,'-B',str(producer/'tools'/tool),*map(str,a)],capture_output=True,text=True,cwd=producer,timeout=45)
 try:r=json.loads(p.stdout)
 except Exception:r={'status':'invalid_cli_output','passed':None,'diagnostic':p.stderr[-500:]}
 return p.returncode,r
schema_hash=hashlib.sha256((producer/'schemas/public_evidence_envelope.v1.json').read_bytes()).hexdigest()
check('unchanged_rc8_schema_lock',schema_hash=='343d804eb2bd2be56a97d93c25376d64e55fc8e2e9afac952d2c4e1a630e92e1')
with tempfile.TemporaryDirectory(prefix='rc7-independent-pipeline-') as directory:
 tmp=Path(directory)
 def write(n,v):
  p=tmp/(n+'.json');p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');return p
 rp=write('request',original); initial=copy.deepcopy(original['query_plan']['frozen_queries']); initial=[{**q,'execution_state':'frozen'} for q in initial]
 pp=write('plan',{'channel':'public_web','queries':initial,'batch_state':'initial_frozen_batch'}); cp=tmp/'compiled.json'
 code,r=run('compile_retrieval_execution_request.py','--task',rp,'--plan',pp,'--output',cp)
 check('compile_frozen_rc8_original',code==0 and r.get('passed'),r)
 if code==0 and cp.exists():
  compiled=read(cp);check('compiler_preserves_request_and_criteria',compiled['retrieval_task']==original and compiled['source_request_sha256']==sha(original) and all(compiled['sufficiency_applicability'].get(k)==v for k,v in original['acceptance_contract'].items()))
  code,r=run('compile_retrieval_execution_request.py','--check-execution',cp,'--task',rp);check('execution_check_accepts_initial',code==0 and r.get('passed'),r)
  scope_plan={'channel':'public_web','queries':initial,'batch_state':'in_scope_iteration_batch','parent_batch_id':'OFFLINE-B0'}
  scope_path=tmp/'scope-compiled.json'
  code,r=run('compile_retrieval_execution_request.py','--task',rp,'--plan',write('scope-plan',scope_plan),'--output',scope_path)
  check('existing_scope_iteration_compiles_without_new_approval',code==0 and r.get('passed'),r)
  if scope_path.exists():
   code,r=run('compile_retrieval_execution_request.py','--check-execution',scope_path,'--task',rp)
   check('existing_scope_iteration_execution_passes',code==0 and r.get('passed'),r)
  denied=copy.deepcopy(original);denied['incremental_policy']['in_scope_iteration_allowed']=False
  denied_path=tmp/'denied-compiled.json'
  code,r=run('compile_retrieval_execution_request.py','--task',write('separate-explicit-denial',denied),'--plan',write('denied-plan',scope_plan),'--output',denied_path)
  check('separate_explicit_denial_blocks_scope_iteration',code!=0 and r.get('passed') is False and not denied_path.exists(),r)
  actual=copy.deepcopy(suff);actual['execution_request']=compiled;sp=write('actual',actual);dp=write('draft',draft);ep=tmp/'envelope.json'
  code,r=run('package_evidence.py','--input',dp,'--request',rp,'--sufficiency-input',sp,'--output',ep);check('strict_new_package_from_actual_execution',code==0 and r.get('status')=='pass' and ep.exists(),r)
  if ep.exists():
   envelope=read(ep);request,response,adoption=bridge.consumer_contracts_for(original,envelope,schema_hash)
   compatibility=read(consumer/'external-capabilities/cross-package-compatibility.json')
   outcome=bridge.validate_exchange(request,envelope,response,adoption,compatibility,sufficiency_input=actual)
   check('unmodified_rc8_runtime_consumes_new_package',outcome['status']=='pass',outcome)
   for name,value,path in [('request',request,consumer/'external-capabilities/upstream-task.schema.json'),('response',response,consumer/'external-capabilities/upstream-response.schema.json'),('adoption',adoption,consumer/'external-capabilities/upstream-adoption-receipt.schema.json'),('envelope',envelope,producer/'schemas/public_evidence_envelope.v1.json')]:
    errors=[e.message for e in Draft202012Validator(read(path)).iter_errors(value)];check('actual_jsonschema_'+name,not errors,errors)
   check('sources_evidence_conflicts_gaps_preserved',all(envelope[k]==draft[k] for k in ('sources','items','negative_hits','conflicts','gaps')))
  for key,value in [('stop_condition','改为继续执行'),('subjects',['另一个对象']),('business_question','另一个业务问题'),('source_request_sha256',None)]:
   bad=copy.deepcopy(compiled)
   if value is None:bad.pop(key,None)
   else:bad[key]=value
   code,r=run('compile_retrieval_execution_request.py','--check-execution',write('bad-'+key,bad),'--task',rp);check('reject_execution_'+key,code!=0 and r.get('passed') is False,r)
  for key,value in [('acceptance_mode','quality_sufficiency'),('count_threshold',1),('quality_criteria',[]),('diversity_requirements',{})]:
   bad=copy.deepcopy(actual);bad['consumer_contract'][key]=value;out=tmp/('invalid-'+key+'.json')
   code,r=run('package_evidence.py','--input',dp,'--request',rp,'--sufficiency-input',write('bad-suff-'+key,bad),'--output',out);check('reject_package_'+key,code!=0 and r.get('status')=='fail' and not out.exists(),r)
  bad=copy.deepcopy(actual);bad.pop('execution_request');out=tmp/'missing-exec-output.json'
  code,r=run('package_evidence.py','--input',dp,'--request',rp,'--sufficiency-input',write('missing-execution',bad),'--output',out);check('old_record_not_promoted_to_new_execution',code!=0 and r.get('status')=='fail' and not out.exists(),r)
  # A separate synthetic Owner decision follows the rc8 schema exactly.
  if ep.exists():
   decision=copy.deepcopy(adoption)
   decision["accepted_by"]="residential_production_owner"
   decision['incremental_decision']={'decision':'authorize_incremental','authorized_query_ids':['q02-proposal'],'reason':'虚构离线验证明确批准一个后续批次','limits':'仅一个增量批次；最多30分钟；零费用'}
   decision_schema=read(consumer/'external-capabilities/upstream-adoption-receipt.schema.json')
   errors=[e.message for e in Draft202012Validator(decision_schema).iter_errors(decision)]
   check('approval_keeps_rc8_exact_schema',not errors,errors)
   checked=bridge.validate_exchange(original,envelope,response,decision,compatibility,sufficiency_input=actual)
   check('approval_is_valid_rc8_decision',checked['status']=='pass',checked)
   decision_hash=sha(decision)
   extension={'authorized':True,'authorization_ref':'OFFLINE-OWNER-DECISION','maximum_incremental_batches':1,'time_limit_minutes':30,'cost_limit':'zero'}
   binding={'schema':'continuation_authorization_binding.v1','request_sha256':sha(original),'adoption_sha256':decision_hash,'limits_quote':decision['incremental_decision']['limits'],'adaptive_extension':copy.deepcopy(extension)}
   q={'query_id':'q02-proposal','exact_query_text':'虚构后续批次 归家体验 反例','execution_state':'frozen'}
   continued={'channel':'public_web','queries':[q],'batch_state':'approved_incremental_batch','parent_batch_id':actual['batch']['batch_id'],'continuation_adoption':decision,'continuation_binding':binding,'adaptive_extension':extension}
   cpath=tmp/'continued-execution.json'
   code,r=run('compile_retrieval_execution_request.py','--task',rp,'--plan',write('continued-plan',continued),'--output',cpath);check('approved_continuation_compiles_without_changing_rc8',code==0 and r.get('passed'),r)
   if cpath.exists():
    executed=read(cpath);continued_input=copy.deepcopy(actual);continued_input['execution_request']=executed
    continued_input['continuation_adoption']=copy.deepcopy(decision);continued_input['continuation_binding']=copy.deepcopy(binding);continued_input['consumer_contract']['adaptive_extension']=copy.deepcopy(extension)
    continued_input['batch'].update(batch_id='OFFLINE-B2',batch_state='approved_incremental_batch',parent_batch_id=actual['batch']['batch_id'])
    for row in continued_input['batch']['queries']+continued_input['query_learning_records']:
     row['query_id']=q['query_id'];row['exact_query_text']=q['exact_query_text']
    continued_input['receipt']['stop_reason']='虚构获批的一批已回传，仍保留缺口'
    continued_draft=copy.deepcopy(draft);continued_draft['query_execution'].update(executed_query_ids=[q['query_id']],proposed_incremental_query_ids=[],adaptive_extension_authorized=True)
    continued_draft['stop_reason']=continued_input['receipt']['stop_reason']
    for source in continued_draft['sources']:
     if isinstance(source.get('query_ref'),dict):source['query_ref'].update(query_id=q['query_id'],exact_query_text=q['exact_query_text'])
    out=tmp/'continued-envelope.json'
    code,r=run('package_evidence.py','--input',write('continued-draft',continued_draft),'--request',rp,'--sufficiency-input',write('continued-input',continued_input),'--output',out);check('approved_continuation_strict_packaging',code==0 and r.get('status')=='pass',r)
    if out.exists():
     ce=read(out);cq,cr,ca=bridge.consumer_contracts_for(original,ce,schema_hash)
     checked=bridge.validate_exchange(cq,ce,cr,ca,compatibility,sufficiency_input=continued_input)
     check('unmodified_rc8_consumes_approved_continuation',checked['status']=='pass',checked)
     errors=[]
     for value,path in [(cr,consumer/'external-capabilities/upstream-response.schema.json'),(ca,consumer/'external-capabilities/upstream-adoption-receipt.schema.json'),(ce,producer/'schemas/public_evidence_envelope.v1.json')]:errors.extend(e.message for e in Draft202012Validator(read(path)).iter_errors(value))
     check('continuation_output_schema_unchanged',not errors,errors)
   for name,mutate in [('wrong_request_hash',lambda x:x['continuation_binding'].update(request_sha256='0'*64)),('wrong_adoption_hash',lambda x:x['continuation_binding'].update(adoption_sha256='0'*64)),('changed_limits_quote',lambda x:x['continuation_binding'].update(limits_quote='无限制')),('changed_execution_budget',lambda x:x['adaptive_extension'].update(maximum_incremental_batches=99)),('budget_exhausted',lambda x:x.update(usage={'minutes':30})),('cost_exceeded',lambda x:x.update(usage={'cost':1}))]:
    bad=copy.deepcopy(continued);mutate(bad);out=tmp/(name+'-execution.json')
    code,r=run('compile_retrieval_execution_request.py','--task',rp,'--plan',write(name,bad),'--output',out);check('reject_continuation_'+name,code!=0 and r.get('passed') is False and not out.exists(),r)
   check('original_adoption_not_extended_or_rewritten',sha(decision)==decision_hash and 'request_sha256' not in decision and 'adaptive_extension' not in decision['incremental_decision'])
  code,r=run('validate_public_evidence.py','--input',write('historical-envelope',draft),'--request',rp,'--sufficiency-input',write('historical-suff',suff),'--historical-read-only')
  check('rc6_bound_history_readable_but_not_new_production',code==0 and r.get('status')=='pass' and r.get('production_binding_verified') is False and r.get('validation_scope')=='historical_read_only',r)
  damaged=copy.deepcopy(suff);damaged['consumer_contract']['count_threshold']=1
  code,r=run('validate_public_evidence.py','--input',write('historical-envelope2',draft),'--request',rp,'--sufficiency-input',write('damaged-history',damaged),'--historical-read-only')
  check('history_mode_does_not_hide_changed_content',code!=0 and r.get('status')=='fail',r)
check('rc8_original_stayed_byte_identical',(fixtures/'request.json').read_bytes()==frozen_bytes)
report={'status':'pass' if all(c['passed'] for c in cases) else 'fail','case_count':len(cases),'failure_count':sum(not c['passed'] for c in cases),'cases':cases,'real_retrieval_executed':False,'consumer_modified':False,'semantic_understanding_proven':False}
args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='cases'}));print(json.dumps([c for c in cases if not c['passed']],ensure_ascii=False))
sys.exit(report['failure_count']!=0)
