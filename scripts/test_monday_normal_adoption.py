"""Read-only acceptance of the scoped Monday normal adoption; no live saves."""
import hashlib,json,re,sys,unittest
from pathlib import Path
import weekly_readonly_guard as guard
import generate_portal

ROOT=Path(__file__).resolve().parents[1]
class MondayAdoption(unittest.TestCase):
 def test_other_days_remain_locked(self):
  manifest=guard.manifest()
  self.assertEqual(guard.top_dates(),['261117','261118','261119','261120'])
  self.assertEqual(len(manifest),18)
  for rel,digest in manifest.items():
   self.assertEqual(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(),digest,rel)
 def test_exact_normal_outputs(self):
  adoption=json.loads((ROOT/'scripts/weekly_normal_adoptions.json').read_text('utf8'))['261116']
  self.assertEqual(set(adoption['adopted']),{'share/261116/'+s for s in ['index.html','daily/index.html','instructions/index.html']})
  for rel,digest in adoption['adopted'].items():
   data=(ROOT/rel).read_bytes()
   self.assertEqual(hashlib.sha256(data).hexdigest(),digest)
   html=data.decode('utf8');self.assertFalse(guard.readonly(html))
   config=json.loads(re.search(r'<script id="shared-ledger-config" type="application/json">(.*?)</script>',html,re.S)[1])
   self.assertFalse(config.get('sourceOnly',False))
   self.assertEqual([x['cs'] for x in config['cases']],['51400871','51400870','51400869'])
   self.assertTrue(all(len(x['base'])==15 for x in config['cases']))
 def test_top_existing_routes(self):
  self.assertEqual(generate_portal.validate_portal_top_only_output(ROOT),[])
  text=(ROOT/'portal/index.html').read_text('utf8')
  self.assertIn('../share/261116/',text)
 def test_bad_retirement_pair_rejected(self):
  before='<div data-source-only="true">not approved</div>'
  after=(ROOT/'share/261116/index.html').read_text('utf8')
  self.assertEqual(guard.portal(before,after,'','261116',lambda *a:['wrong']),['Explicit provisional retirement/adoption plan required'])
 def test_normal_path_preserves_validator(self):
  text=(ROOT/'share/261116/index.html').read_text('utf8')
  self.assertEqual(guard.portal(text,text,'','261116',lambda *a:['ordinary failure']),['ordinary failure'])

if __name__=='__main__':unittest.main()
