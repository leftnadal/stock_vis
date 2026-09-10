"""Read-only compact evidence export; never imports credentials or calls a provider."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
batch=root/'continuations_v012/0b5220e04007446695d092f763b72020'
ledger=batch/'continuation.json'
print('\n=== SAVED RESULTS (not test output) ===')
if ledger.exists(): print(ledger.read_text())
for spec in json.loads((root/'plan.json').read_text())['runs']:
    folder=batch/spec['run_id'];path=folder/'result.json'
    print('\n---',spec['case_id'],spec['condition'],'---')
    if not path.exists():print('No result saved');continue
    result=json.loads(path.read_text())
    print(json.dumps({k:result.get(k) for k in ['run_id','status','error_type','recovery','calls','retrieval','final_output','evaluation_target_sha256']},ensure_ascii=False,indent=2))
    if result['status']!='completed_pending_semantic_review':
        for response in sorted(folder.glob('response-*.json')):
            print(response.name);print(response.read_text())
