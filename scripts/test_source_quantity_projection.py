"""Synthetic projection fixtures; no original inspection or live-data claims."""
from copy import deepcopy
from pathlib import Path
import argparse,hashlib,json,sys,tempfile,unittest

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--pc-root',type=Path,required=True);args,remaining=parser.parse_known_args()
 sys.path.insert(0,str(args.pc_root));sys.argv=[sys.argv[0],*remaining]
else:
 args=None
if args is not None:
 from source_quantity_projection import retained_projections,apply_blank_projections,FILE,SCHEMA,OBSERVATIONS

CASE='00000001';FIELD='branch_cut_under_10';REF='synthetic-public-ref'
def observation(status='observed_blank',raw=''):
 return {'status':status,'raw_text':raw,'source':{'kind':'cs','sha256':hashlib.sha256(b'synthetic fixture source').hexdigest(),'page':1,'case_key':CASE,'span_label':'SYNTHETIC ONLY','field':FIELD}}
def entries(state='nonapplicable_candidate',text='非該当候補（正式未確認）'):
 return [{'cs':CASE,'label':'SYNTHETIC ONLY','conditions':'unchanged nonquantity condition','quantities':[{'field':FIELD,'state':state,'text':text},{'field':'root_cut_under_10','state':'source_positive','text':'25（原典値・正式未確認）'}]}]

@unittest.skipIf(args is None,'Requires explicit isolated PC source root')
class SourceProjectionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'scripts').mkdir()
  (self.root/FILE).write_text(json.dumps({'schema':SCHEMA,'source_ref':REF,'projections':[]}))
  self.private=self.root/'private-observations.json'
 def tearDown(self):self.tmp.cleanup()
 def write_private(self,rows):
  self.private.write_text(json.dumps({'schema':OBSERVATIONS,'source_ref':REF,'observations':rows}))
 def row(self,o=None):return {'date':'261116','case_key':CASE,'field':FIELD,'observation':o if o is not None else observation()}
 def revised(self):return retained_projections(self.root,REF,['261116'],self.private)
 def test_inspected_blank_is_retained_and_regeneration_cannot_revert(self):
  self.write_private([self.row()]);retained=self.revised()
  public=json.dumps(retained,ensure_ascii=False)
  self.assertNotIn('raw_text',public);self.assertNotIn('source',retained['projections'][0]['projection'])
  self.assertNotIn(observation()['source']['sha256'],public)
  (self.root/FILE).write_text(public);self.private.unlink()
  replay=retained_projections(self.root,REF,['261116'])
  self.assertEqual(retained,replay)
  a,b=entries(),entries();apply_blank_projections(a,'261116',retained);apply_blank_projections(b,'261116',replay)
  self.assertEqual(a,b);self.assertEqual(a[0]['quantities'][0]['text'],'0（原典空欄）')
  self.assertEqual(a[0]['quantities'][1],entries()[0]['quantities'][1]);self.assertEqual(a[0]['conditions'],entries()[0]['conditions'])
  apply_blank_projections(b,'261116',replay);self.assertEqual(a,b)
 def test_unobserved_unreadable_and_conflict_never_become_zero(self):
  for status in ['not_referenced','unreadable','conflict']:
   self.write_private([self.row({'status':status,'raw_text':''})]);self.assertEqual(self.revised()['projections'],[])
 def test_existing_positive_is_conflict_existing_zero_is_preserved(self):
  self.write_private([self.row()]);retained=self.revised()
  with self.assertRaises(ValueError):apply_blank_projections(entries('source_positive','25（原典値）'),'261116',retained)
  zero=entries('formal_confirmed','0（既存確認済み）');before=deepcopy(zero);apply_blank_projections(zero,'261116',retained);self.assertEqual(before,zero)
 def test_wrong_date_case_field_duplicate_and_numeric_corrections_rejected(self):
  for key,value in [('date','261117'),('field','road_width_m')]:
   row=self.row();row[key]=value;self.write_private([row])
   with self.assertRaises(ValueError):self.revised()
  row=self.row();self.write_private([row,row])
  with self.assertRaises(ValueError):self.revised()
  self.write_private([self.row(observation('observed_value','25'))])
  with self.assertRaises(ValueError):self.revised()
  self.write_private([self.row()]);retained=self.revised();other=entries();other[0]['cs']='00000002'
  with self.assertRaises(ValueError):apply_blank_projections(other,'261116',retained)
 def test_unresolved_new_evidence_does_not_silently_override_retained_zero(self):
  self.write_private([self.row()]);retained=self.revised();(self.root/FILE).write_text(json.dumps(retained))
  self.write_private([self.row({'status':'conflict'})])
  with self.assertRaises(ValueError):self.revised()
 def test_missing_inspection_and_bare_zero_without_evidence_rejected(self):
  for o in [{'raw_text':''},observation(raw='25'),observation(raw=None)]:
   self.write_private([self.row(o)])
   with self.assertRaises(ValueError):self.revised()
  self.write_private([self.row()]);retained=self.revised();retained['projections'][0]['projection']['evidence_sha256']=None
  (self.root/FILE).write_text(json.dumps(retained))
  with self.assertRaises(ValueError):retained_projections(self.root,REF,['261116'])

if __name__=='__main__':unittest.main()
