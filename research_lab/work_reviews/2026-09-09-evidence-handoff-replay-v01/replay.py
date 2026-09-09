"""Restricted two-case replay. No imports of protected expectations into requests."""
import json, os, time, uuid, hashlib, datetime, argparse
from pathlib import Path
import provider_adapter as provider
ROOT=Path(__file__).resolve().parent
def dump(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(dump(x))
PROFILE=['existing_error_repaired','correct_content_preserved','introduced_error','unsupported_assertion_added','unsupported_strengthening','material_condition_preserved','material_condition_lost','evidence_retrieved_correctly','evidence_used_correctly','appropriate_abstention_unassessed','final_conclusion_scope_calibration','execution_failure_truncation']
def retrieve(ids,allowed,docs):
 events=[];found=[]
 for sid in ids:
  start=time.perf_counter();ok=isinstance(sid,str) and sid in allowed and sid in docs
  events.append({'source_id':sid,'success':ok,'reason':None if ok else 'source_not_available','latency_seconds':time.perf_counter()-start})
  if ok:found.append(docs[sid])
 return found,events
def run_one(spec,config,call,outroot):
 rid=spec['run_id'];out=outroot/rid;out.mkdir(parents=True,exist_ok=False)
 messages=json.loads((ROOT/'visible'/f'{rid}.json').read_text())
 if sha(dump(messages))!=spec['input_sha256']:raise ValueError('input_hash_mismatch')
 frozen=json.loads((ROOT/'frozen'/f"{spec['case_id']}.json").read_text())
 if sha(frozen['summary'])!=spec['summary_sha256'] or sha(dump(frozen['case']))!=spec['case_sha256']:raise ValueError('frozen_hash_mismatch')
 body=json.loads(messages[1]['content']);allowed={x['source_id'] for x in body['available_sources']}
 result={'run_id':rid,'execution_started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'harness_version':'0.1.0','spec':spec,'config':config,'status':'running','calls':[],
 'retrieval':{'available_source_ids':sorted(allowed),'requested_source_ids':[],'successfully_retrieved_source_ids':[],'failed_retrievals':[],'order':[], 'material_source_not_requested':{'status':'unassessed','reason':'post-run protected review required'},'retrieved_but_unused_material_source':{'status':'unassessed','reason':'source IDs alone do not prove semantic use'}},
 'evaluation':{k:{'status':'unassessed','warrant':[]} for k in PROFILE},'final_output':None,'actual_cost_usd':None}
 remaining=config['max_tokens']
 try:
  for index in range(config['max_calls_per_run']):
   if remaining<=0:result['status']='output_budget_exhausted';break
   payload={k:config[k] for k in ['model','temperature','top_p','seed','reasoning']}
   payload.update({'messages':messages,'max_tokens':remaining,'stream':False,'n':1})
   write(out/f'request-{index}.json',payload)
   start=time.perf_counter();response=call(payload,config['timeout_seconds']);elapsed=time.perf_counter()-start
   write(out/f'response-{index}.json',response)
   result['calls'].append({'request':f'request-{index}.json','response':f'response-{index}.json','latency_seconds':elapsed,'returned_identity':response.get('returned_model'),'finish_reason':response.get('finish_reason'),'usage':response.get('usage')})
   if response.get('returned_model')!=config['model']:result['status']='model_identity_mismatch';break
   if response.get('status')!='complete' or response.get('finish_reason')!='stop':result['status']='execution_or_truncation_failure';break
   usage=response.get('usage',{}).get('completion_tokens')
   if not isinstance(usage,int) or usage<0:result['status']='usage_unavailable';break
   remaining-=usage
   text=response['answer'];action=json.loads(text)
   if action.get('action')=='final':result['final_output']=action;result['status']='completed_pending_semantic_review';break
   if action.get('action')!='retrieve' or not isinstance(action.get('source_ids'),list):result['status']='invalid_protocol';break
   if spec['condition']!='B':result['status']='disallowed_retrieval_attempt';break
   ids=action['source_ids'];found,events=retrieve(ids,allowed,frozen['documents'])
   t=result['retrieval'];t['requested_source_ids'].extend(ids);t['order'].extend(events)
   t['successfully_retrieved_source_ids'].extend(e['source_id'] for e in events if e['success'])
   t['failed_retrievals'].extend(e for e in events if not e['success'])
   messages=messages+[{'role':'assistant','content':text},{'role':'user','content':dump({'retrieved_documents':found,'retrieval_events':events,'calls_remaining':config['max_calls_per_run']-index-1})}]
  else:result['status']='call_limit_exhausted'
 except Exception as exc:
  # Never serialize provider exception messages or credentials.
  result['status']='execution_failure';result['error_type']=type(exc).__name__
 finally:
  result['evaluation_target_sha256']=sha(dump(result['final_output'])) if result['final_output'] is not None else None
  write(out/'result.json',result)
 return result
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');args=ap.parse_args()
 plan=json.loads((ROOT/'plan.json').read_text())
 token=os.environ.get('DEEPINFRA_TOKEN') or os.environ.get('DEEP_INFRA_API_KEY')
 pre={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'credential_present':bool(token),'planned_runs':6,'model_invocations':0,'status':'ready_for_hosted_execution' if token else 'blocked_before_model_invocation','reason':None if token else 'existing_provider_credentials_unavailable','network_reachability':'unverified'}
 if not args.execute or not token:
  out=ROOT/'preflight'/f'{uuid.uuid4().hex}.json';write(out,pre);print(dump(pre));return 0 if token else 2
 token=provider.valid_token(token)
 def call(payload,timeout):return provider.sanitize_response(provider.post_json(payload,token,timeout),plan['config']['model'],token)
 out=ROOT/'executions'/uuid.uuid4().hex
 for spec in plan['runs']:
  r=run_one(spec,plan['config'],call,out)
  # Preserve artifacts and stop batch; never retry or silently switch backend.
  if r['status']!='completed_pending_semantic_review':break
 print(str(out))
if __name__=='__main__':raise SystemExit(main())
