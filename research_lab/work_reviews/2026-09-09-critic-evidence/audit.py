"""Offline provenance inventory. No model calls, no semantic grading."""
from pathlib import Path
import json, hashlib, collections

ROOT = Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
def digest(x): return sha(json.dumps(x, ensure_ascii=False, indent=2, sort_keys=True).encode())

def main():
    cases = {c['id']: c for c in json.loads((ROOT/'sources/calibration.json').read_text())}
    records, checks, inv = [], [], []
    for p in sorted((ROOT/'inputs').glob('*.json')):
        d = json.loads(p.read_text())
        inv.append({'file': str(p.relative_to(ROOT)), 'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size})
        if p.name.startswith('manifest'):
            if 'case_hash' in d:
                checks.append({'manifest': p.name, 'case': d['case_id'], 'case_hash_matches_v081': d['case_hash']==digest(cases[d['case_id']])})
        elif 'result' in d:
            r = d['result']
            records.append({'file':p.name, 'label':d.get('label'), 'model':d.get('requested_model'), 'response_id':r.get('response_id'), 'status':r.get('status'), 'finish_reason':r.get('finish_reason'), 'answer_sha256':sha(r.get('answer','').encode()), 'answer_bytes':len(r.get('answer','').encode())})
    # Conditional arithmetic counterexample, not an estimate of a real firm.
    # A market's growth does not bound an individual supplier's growth.
    diagnostic = {'assumed_ai_share':0.24, 'assumed_ai_growth':1.00, 'assumed_non_ai_growth':0.02,
                  'illustrative_total_growth':0.24*1.00+0.76*0.02,
                  'market_match_scenario_contribution':0.24*0.42,
                  'is_forecast':False, 'is_empirical_observation':False}
    out={'scope':'retrospective offline structural audit; no quality score',
         'manifest_count':len(list((ROOT/'inputs').glob('manifest*.json'))),
         'output_count':len(records), 'case_hash_checks':checks,
         'all_available_case_hashes_match':all(c['case_hash_matches_v081'] for c in checks),
         'output_status_counts':dict(collections.Counter(r['status'] for r in records)),
         'outputs':records, 'file_inventory':inv, 'arithmetic_diagnostic':diagnostic,
         'limitations':['Historical execution and reviewer blinding not independently attested.',
                        'Filename suffixes do not establish run or parent linkage.',
                        'Prompt bodies and hashes not reconstructed for 13 review manifests.',
                        'Completion status does not establish answer quality.',
                        'No local Mac measurements or hosted model calls performed.']}
    (ROOT/'audit_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['manifest_count','output_count','all_available_case_hashes_match','output_status_counts']},ensure_ascii=False))

if __name__=='__main__':main()
