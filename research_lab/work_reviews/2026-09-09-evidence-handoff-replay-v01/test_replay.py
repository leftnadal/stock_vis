import unittest,json,tempfile
from pathlib import Path
import replay
class ReplayChecks(unittest.TestCase):
 def setUp(self):self.p=json.loads((replay.ROOT/'plan.json').read_text())
 def test_six_frozen_conditions(self):
  self.assertEqual(len(self.p['runs']),6)
  for case in ['hard-003','hard-006']:
   rs=[r for r in self.p['runs'] if r['case_id']==case]
   self.assertEqual({r['condition'] for r in rs},set('ABC'))
   self.assertEqual(len({r['summary_sha256'] for r in rs}),1)
   self.assertTrue(all(r['candidate_refs']==rs[0]['candidate_refs'] for r in rs))
 def test_visible_boundaries(self):
  prompts=set()
  for r in self.p['runs']:
   raw=(replay.ROOT/'visible'/f"{r['run_id']}.json").read_text();m=json.loads(raw);prompts.add(m[0]['content'])
   self.assertEqual(replay.sha(replay.dump(m)),r['input_sha256'])
   self.assertNotIn('protected_expectations',raw);self.assertNotIn(r['case_id'],raw)
   d=json.loads(m[1]['content'])
   if r['condition']=='A':self.assertEqual(d['available_sources'],[]);self.assertEqual(d['provided_documents'],[])
   if r['condition']=='B':self.assertTrue(d['available_sources']);self.assertEqual(d['provided_documents'],[])
   if r['condition']=='C':self.assertTrue(d['provided_documents']);self.assertEqual(d['available_sources'],[])
  self.assertEqual(len(prompts),1)
 def test_invalid_source_never_disclosed(self):
  docs={'a':{'text':'available'},'b':{'text':'protected'}}
  found,events=replay.retrieve(['a','b','missing'],{'a'},docs)
  self.assertEqual(found,[docs['a']]);self.assertEqual([e['success'] for e in events],[True,False,False])
 def test_B_protocol_mock_not_model_result(self):
  r=next(r for r in self.p['runs'] if r['condition']=='B');m=json.loads((replay.ROOT/'visible'/f"{r['run_id']}.json").read_text());sid=json.loads(m[1]['content'])['available_sources'][0]['source_id'];calls=[]
  def fake(payload,timeout):
   calls.append(payload)
   a={'action':'retrieve','source_ids':[sid,'missing']} if len(calls)==1 else {'action':'final','answer':'MOCK ONLY','used_source_ids':[sid]}
   return {'answer':json.dumps(a),'returned_model':self.p['config']['model'],'status':'complete','finish_reason':'stop','usage':{'completion_tokens':10}}
  with tempfile.TemporaryDirectory() as d:
   out=replay.run_one(r,self.p['config'],fake,Path(d))
   self.assertEqual(out['status'],'completed_pending_semantic_review');self.assertEqual(len(out['retrieval']['failed_retrievals']),1);self.assertEqual(len(calls),2)
   self.assertEqual(calls[1]['max_tokens'],8182)
   self.assertTrue(all(v['status']=='unassessed' for v in out['evaluation'].values()))
if __name__=='__main__':unittest.main()
