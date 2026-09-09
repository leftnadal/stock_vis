"""One-time continuation, preserving original batch and inputs; no failed-call retry."""
import hashlib
import json
import os
from pathlib import Path
import replay_v011 as replay

ROOT = Path(__file__).resolve().parent
BATCH = '0b5220e04007446695d092f763b72020'

def main():
    for line in (ROOT/'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('original_artifact_hash_mismatch')
    plan = json.loads((ROOT/'plan.json').read_text())
    original = ROOT/'executions'/BATCH
    first = plan['runs'][0]
    folder = original/first['run_id']
    old = json.loads((folder/'result.json').read_text())
    if old['spec'] != first or old['config'] != plan['config'] or old['error_type'] != 'JSONDecodeError' or old['status'] != 'execution_failure':
        raise ValueError('unexpected_original_state')
    if len(old['calls']) != 1 or len(list(original.glob('*/result.json'))) != 1:
        raise ValueError('unexpected_existing_execution')
    for spec in plan['runs'][1:]:
        if (original/spec['run_id']).exists():
            raise ValueError('remaining_run_already_started')
    request = json.loads((folder/'request-0.json').read_text())
    response = json.loads((folder/'response-0.json').read_text())
    action, wrapping = replay.parse_action(response['answer'])
    if action['action'] != 'final':
        raise ValueError('original_response_not_final')
    token = os.environ.get('DEEPINFRA_TOKEN') or os.environ.get('DEEP_INFRA_API_KEY')
    if not token:
        token = replay.provider.token_from_file(ROOT.parents[3]/'.env')
    token = replay.provider.valid_token(token)
    out = ROOT/'continuations'/BATCH
    out.mkdir(parents=True, exist_ok=False)
    manifest = {'original_batch':BATCH, 'harness_version':'0.1.1', 'status':'started',
        'original_files_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.json')},
        'first_run_reinvoked':False, 'new_model_invocations':0, 'results':[],
        'parser_change':'plain JSON or single entire JSON fence; strict required fields; no content repair',
        'semantic_review':'unassessed', 'recovery_latency_is_not_inference_latency':True}
    replay.write(out/'continuation.json', manifest)
    try:
        def saved_call(payload, timeout):
            if payload != request:
                raise ValueError('original_request_mismatch')
            return response
        recovered = replay.run_one(first, plan['config'], saved_call, out)
        manifest['results'].append({'run_id':first['run_id'],'status':recovered['status'],'source':'saved_response'})
        manifest['original_inference_calls'] = old['calls']
        if recovered['status'] != 'completed_pending_semantic_review':
            raise ValueError('saved_response_recovery_failed')
        print('Original A recovered from saved response; no model reinvocation.', flush=True)
        def call(payload, timeout):
            manifest['new_model_invocations'] += 1
            replay.write(out/'continuation.json', manifest)
            return replay.provider.sanitize_response(replay.provider.post_json(payload, token, timeout), plan['config']['model'], token)
        for spec in plan['runs'][1:]:
            result = replay.run_one(spec, plan['config'], call, out)
            manifest['results'].append({'run_id':spec['run_id'],'status':result['status'],'source':'new_execution'})
            replay.write(out/'continuation.json', manifest)
            print(spec['case_id'], spec['condition'], result['status'], flush=True)
            if result['status'] != 'completed_pending_semantic_review':
                manifest['status'] = 'stopped_on_execution_failure'
                return 1
        manifest['status'] = 'six_outputs_pending_semantic_review'
        return 0
    except Exception as exc:
        manifest['status'] = 'continuation_failed'
        manifest['error_type'] = type(exc).__name__
        return 1
    finally:
        replay.write(out/'continuation.json', manifest)
        print('RESULT_PATH=' + str(out), flush=True)

if __name__ == '__main__':
    raise SystemExit(main())
