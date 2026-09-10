import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import replay
import replay_v011
import replay_v012
import replay_protocol_v012 as protocol
import resume_remaining_v012 as resume

FINAL={'action':'final','answer':'SYNTHETIC ONLY','used_source_ids':[],'changes':[{'original':'x','corrected':'y','reason':'synthetic'}],'limitations':[]}

class RecoveryTests(unittest.TestCase):
    def test_preserve_structured_and_string_changes(self):
        for changes in (FINAL['changes'],['synthetic'],['synthetic',{'detail':{'value':1}}]):
            obj=dict(FINAL,changes=changes)
            for raw in (json.dumps(obj),'```json\n'+json.dumps(obj)+'\n```'):
                self.assertEqual(protocol.parse_action(raw)[0],obj)
    def test_invalid_protocol_still_rejected(self):
        for raw in ('[]','{"action":"final"}',json.dumps(dict(FINAL,used_source_ids=[{}])),json.dumps(dict(FINAL,changes={})), 'prose '+json.dumps(FINAL),'```json\n'+json.dumps(FINAL)+'\n`` ` ``','{"action":"retrieve","action":"final"}'):
            with self.assertRaises(ValueError):protocol.parse_action(raw)
    def test_offline_two_recoveries_four_calls_preservation_and_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=replay.ROOT
            for name in ['visible','frozen']:shutil.copytree(source/name,root/name)
            shutil.copyfile(source/'plan.json',root/'plan.json')
            plan=json.loads((root/'plan.json').read_text());config=plan['config']
            def response(action):
                return {'answer':json.dumps(action),'returned_model':config['model'],'status':'complete','finish_reason':'stop','usage':{'completion_tokens':10}}
            oldroot=root/'executions'/resume.BATCH;prior=root/'continuations'/resume.BATCH
            def first(payload,timeout):
                r=response(dict(FINAL,changes=['synthetic']));r['answer']='```json\n'+r['answer']+'\n```';return r
            with patch.object(replay,'ROOT',root):
                a=replay.run_one(plan['runs'][0],config,first,oldroot)
            self.assertEqual(a['error_type'],'JSONDecodeError')
            body=json.loads(json.loads((root/'visible'/f"{plan['runs'][1]['run_id']}.json").read_text())[1]['content'])
            sid=body['available_sources'][0]['source_id'];counter=[]
            def second(payload,timeout):
                counter.append(payload)
                return response({'action':'retrieve','source_ids':[sid]}) if len(counter)==1 else response(dict(FINAL,used_source_ids=[sid]))
            with patch.object(replay_v011,'ROOT',root):
                b=replay_v011.run_one(plan['runs'][1],config,second,prior)
            self.assertEqual(b['error_type'],'ValueError')
            original_hash={str(p.relative_to(root)):resume.digest(p) for p in oldroot.rglob('*.json')}
            replay.write(prior/'continuation.json',{'status':'stopped_on_execution_failure','first_run_reinvoked':False,'new_model_invocations':2,'original_files_sha256':original_hash})
            for name in ['SHA256SUMS','RECOVERY_SHA256SUMS','V012_SHA256SUMS']:
                (root/name).write_text(resume.digest(root/'plan.json')+'  plan.json\n')
            before={str(p):p.read_bytes() for base in [oldroot,prior] for p in base.rglob('*.json')}
            with patch.object(resume,'ROOT',root),patch.object(replay_v012,'ROOT',root),patch.dict('os.environ',{'DEEPINFRA_TOKEN':'synthetic'}),patch.object(replay_v012.provider,'valid_token',return_value='synthetic'),patch.object(replay_v012.provider,'post_json',return_value=response(FINAL)) as calls,patch.object(replay_v012.provider,'sanitize_response',side_effect=lambda r,m,t:r),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(resume.main(),0);self.assertEqual(calls.call_count,4)
                with self.assertRaises(FileExistsError):resume.main()
                self.assertEqual(calls.call_count,4)
                folder=prior/plan['runs'][1]['run_id']
                request=folder/'request-1.json';data=json.loads(request.read_text());data['messages'][-1]['content']='tampered'
                request.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError,'saved_request_mismatch'):resume.recover(folder,plan['runs'][1],config)
                request.write_bytes(before[str(request)])
            self.assertEqual(before,{str(p):p.read_bytes() for base in [oldroot,prior] for p in base.rglob('*.json')})
            result=json.loads((root/'continuations_v012'/resume.BATCH/plan['runs'][1]['run_id']/'result.json').read_text())
            self.assertEqual(result['final_output']['changes'],FINAL['changes'])
            self.assertEqual(result['calls'],[dict(c,response_wrapping='plain_json') for c in b['calls']])
            self.assertFalse(result['recovery']['model_reinvoked'])

if __name__=='__main__':unittest.main()
