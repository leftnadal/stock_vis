import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import replay
import replay_v011
import replay_protocol
import resume_replay

FINAL = {'action':'final','answer':'SYNTHETIC TEST ONLY','used_source_ids':[], 'changes':[], 'limitations':[]}

class ProtocolTests(unittest.TestCase):
    def test_plain_and_fenced_same_action(self):
        for text in (json.dumps(FINAL), '```json\n'+json.dumps(FINAL)+'\n```'):
            self.assertEqual(replay_protocol.parse_action(text)[0], FINAL)
    def test_prose_broken_multiple_fences_rejected(self):
        body=json.dumps(FINAL)
        for text in ('Explanation '+body, '```json\n'+body+'\n`` ` ``', '```json\n'+body+'\n```\nExtra', '```json\n'+body+'\n```\n```json\n{}\n```'):
            with self.assertRaises(ValueError): replay_protocol.parse_action(text)
    def test_schema_duplicate_and_nonfinite_rejected(self):
        for text in ('[]','{"action":"final"}','{"action":"retrieve","source_ids":[1]}','{"action":"retrieve","action":"retrieve","source_ids":[]}','{"action":"retrieve","source_ids":[],"x":NaN}'):
            with self.assertRaises(ValueError): replay_protocol.parse_action(text)
    def test_retrieval_fence(self):
        self.assertEqual(replay_protocol.parse_action('```json\n{"action":"retrieve","source_ids":["a"]}\n```')[0]['source_ids'], ['a'])
    def test_recover_then_only_five_new_calls_and_no_overwrite(self):
        source = replay.ROOT
        plan = json.loads((source/'plan.json').read_text())
        def response(payload):
            return {'answer':'```json\n'+json.dumps(FINAL)+'\n```','returned_model':plan['config']['model'],'status':'complete','finish_reason':'stop','usage':{'completion_tokens':10}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            import shutil
            shutil.copytree(source/'visible', root/'visible')
            shutil.copytree(source/'frozen', root/'frozen')
            shutil.copyfile(source/'plan.json',root/'plan.json')
            import hashlib
            files=sorted(p for p in root.rglob('*') if p.is_file())
            (root/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(root))+'\n' for p in files))
            original=root/'executions'/resume_replay.BATCH
            with patch.object(replay,'ROOT',root):
                result=replay.run_one(plan['runs'][0],plan['config'],lambda payload,timeout:response(payload),original)
            self.assertEqual(result['error_type'],'JSONDecodeError')
            before={str(p):p.read_bytes() for p in original.rglob('*.json')}
            with patch.object(resume_replay,'ROOT',root), patch.object(replay_v011,'ROOT',root), patch.dict('os.environ',{'DEEPINFRA_TOKEN':'synthetic-test-token'}), patch.object(replay_v011.provider,'valid_token',return_value='synthetic-test-token'), patch.object(replay_v011.provider,'post_json',side_effect=lambda payload,token,timeout: response(payload)) as calls, patch.object(replay_v011.provider,'sanitize_response',side_effect=lambda r,model,token:r):
                self.assertEqual(resume_replay.main(),0)
                self.assertEqual(calls.call_count,5)
                with self.assertRaises(FileExistsError): resume_replay.main()
                self.assertEqual(calls.call_count,5)
            self.assertEqual(before,{str(p):p.read_bytes() for p in original.rglob('*.json')})
            m=json.loads((root/'continuations'/resume_replay.BATCH/'continuation.json').read_text())
            self.assertEqual(len(m['results']),6)
            self.assertFalse(m['first_run_reinvoked'])

if __name__=='__main__':unittest.main()
