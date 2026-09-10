"""Preserve prior histories; verify saved A/B; execute four untouched conditions."""
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import replay_v012 as replay
ROOT=Path(__file__).resolve().parent
BATCH='0b5220e04007446695d092f763b72020'

def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(value, code):
    if not value: raise ValueError(code)

def recover(folder, spec, config):
    old=read(folder/'result.json')
    require(old['spec']==spec and old['config']==config,'saved_spec_config_mismatch')
    messages=read(ROOT/'visible'/f"{spec['run_id']}.json")
    require(replay.sha(replay.dump(messages))==spec['input_sha256'],'input_hash_mismatch')
    frozen=read(ROOT/'frozen'/f"{spec['case_id']}.json")
    require(replay.sha(frozen['summary'])==spec['summary_sha256'] and replay.sha(replay.dump(frozen['case']))==spec['case_sha256'],'frozen_hash_mismatch')
    allowed={x['source_id'] for x in json.loads(messages[1]['content'])['available_sources']}
    remaining=config['max_tokens']; offset=0; requests=[]; success=[]; failures=[]; wraps=[]; final=None
    count=len(old['calls'])
    require(0<count<=config['max_calls_per_run'],'saved_call_count')
    require(len(list(folder.glob('request-*.json')))==count and len(list(folder.glob('response-*.json')))==count,'unexpected_saved_calls')
    for index, call in enumerate(old['calls']):
        require(call['request']==f'request-{index}.json' and call['response']==f'response-{index}.json','saved_call_refs')
        expected={k:config[k] for k in ['model','temperature','top_p','seed','reasoning']}
        expected.update(messages=messages,max_tokens=remaining,stream=False,n=1)
        require(remaining>0 and read(folder/call['request'])==expected,'saved_request_mismatch')
        response=read(folder/call['response'])
        require(response['returned_model']==config['model'] and response['status']=='complete' and response['finish_reason']=='stop','saved_response_not_complete')
        require(call['returned_identity']==response['returned_model'] and call['finish_reason']==response['finish_reason'] and call['usage']==response['usage'],'saved_telemetry_mismatch')
        used=response['usage']['completion_tokens']
        require(type(used) is int and 0<=used<=remaining,'saved_usage_invalid')
        remaining-=used
        action,wrap=replay.parse_action(response['answer']);wraps.append(wrap)
        if action['action']=='final':
            require(index==count-1,'calls_after_final')
            final=action
            break
        require(spec['condition']=='B','disallowed_saved_retrieval')
        ids=action['source_ids'];events=old['retrieval']['order'][offset:offset+len(ids)]
        require(len(events)==len(ids),'retrieval_event_count')
        found=[]
        for sid,event in zip(ids,events):
            ok=sid in allowed and sid in frozen['documents']
            require(event['source_id']==sid and event['success']==ok and event['reason']==(None if ok else 'source_not_available'),'retrieval_event_mismatch')
            if ok: found.append(frozen['documents'][sid]);success.append(sid)
            else: failures.append(event)
        offset+=len(ids);requests.extend(ids)
        messages=messages+[{'role':'assistant','content':response['answer']},{'role':'user','content':replay.dump({'retrieved_documents':found,'retrieval_events':events,'calls_remaining':config['max_calls_per_run']-index-1})}]
    require(final is not None,'saved_final_missing')
    t=old['retrieval']
    require(t['available_source_ids']==sorted(allowed) and t['requested_source_ids']==requests and t['successfully_retrieved_source_ids']==success and t['failed_retrievals']==failures and len(t['order'])==offset,'retrieval_summary_mismatch')
    result=copy.deepcopy(old)
    result.update(status='completed_pending_semantic_review',final_output=final,evaluation_target_sha256=replay.sha(replay.dump(final)),harness_version='0.1.2')
    result.pop('error_type',None)
    result['recovery']={'original_status':old['status'],'original_error_type':old.get('error_type'),'model_reinvoked':False,'recovered_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_folder':str(folder.relative_to(ROOT)),'inference_telemetry':'original, not replay latency'}
    for call,wrap in zip(result['calls'],wraps): call['response_wrapping']=wrap
    return result

def main():
    for filename in ['SHA256SUMS','RECOVERY_SHA256SUMS','V012_SHA256SUMS']:
        for line in (ROOT/filename).read_text().splitlines():
            expected,name=line.split('  ',1)
            require(digest(ROOT/name)==expected,'code_or_input_hash_mismatch')
    plan=read(ROOT/'plan.json');oldroot=ROOT/'executions'/BATCH;prior=ROOT/'continuations'/BATCH
    ledger=read(prior/'continuation.json')
    require(ledger['status']=='stopped_on_execution_failure' and ledger['first_run_reinvoked'] is False and ledger['new_model_invocations']==2,'unexpected_prior_state')
    for name,expected in ledger['original_files_sha256'].items(): require(digest(ROOT/name)==expected,'original_history_changed')
    for spec in plan['runs'][2:]:
        require(not (oldroot/spec['run_id']).exists() and not (prior/spec['run_id']).exists(),'remaining_already_started')
    folders=[oldroot/plan['runs'][0]['run_id'],prior/plan['runs'][1]['run_id']]
    require(read(folders[0]/'result.json')['error_type']=='JSONDecodeError' and read(folders[1]/'result.json')['error_type']=='ValueError','unexpected_failure_type')
    recovered=[recover(folder,spec,plan['config']) for folder,spec in zip(folders,plan['runs'][:2])]
    token=os.environ.get('DEEPINFRA_TOKEN') or os.environ.get('DEEP_INFRA_API_KEY') or replay.provider.token_from_file(ROOT.parents[3]/'.env')
    token=replay.provider.valid_token(token)
    out=ROOT/'continuations_v012'/BATCH
    out.mkdir(parents=True,exist_ok=False)
    history={str(p.relative_to(ROOT)):digest(p) for base in [oldroot,prior] for p in base.rglob('*.json')}
    ledger={'harness_version':'0.1.2','status':'started','saved_runs_reinvoked':False,'new_model_invocations':0,'historical_file_sha256':history,'results':[],'semantic_review':'unassessed'}
    replay.write(out/'continuation.json',ledger)
    try:
        for result in recovered:
            replay.write(out/result['run_id']/'result.json',result)
            ledger['results'].append({'run_id':result['run_id'],'status':result['status'],'source':'saved_response'})
        print('LIVE: saved A and B validated; zero model calls for recovery.',flush=True)
        def call(payload,timeout):
            ledger['new_model_invocations']+=1;replay.write(out/'continuation.json',ledger)
            return replay.provider.sanitize_response(replay.provider.post_json(payload,token,timeout),plan['config']['model'],token)
        for spec in plan['runs'][2:]:
            result=replay.run_one(spec,plan['config'],call,out)
            ledger['results'].append({'run_id':spec['run_id'],'status':result['status'],'source':'new_execution'})
            replay.write(out/'continuation.json',ledger)
            print('LIVE:',spec['case_id'],spec['condition'],result['status'],flush=True)
            if result['status']!='completed_pending_semantic_review':
                ledger['status']='stopped_on_execution_failure';return 1
        ledger['status']='six_outputs_pending_semantic_review';return 0
    except Exception as exc:
        ledger.update(status='continuation_failure',error_type=type(exc).__name__);return 1
    finally:
        ledger['historical_files_unchanged']=all(digest(ROOT/name)==sha for name,sha in history.items())
        replay.write(out/'continuation.json',ledger)
        print('RESULT_PATH='+str(out),flush=True)

if __name__=='__main__':raise SystemExit(main())
