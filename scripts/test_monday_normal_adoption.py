"""Read-only acceptance of all five normal adoptions; no live saves."""
import hashlib,json,re,sys,unittest
from pathlib import Path
import weekly_readonly_guard as guard
import generate_portal

ROOT=Path(__file__).resolve().parents[1]
class MondayAdoption(unittest.TestCase):
 def test_no_remaining_readonly_outputs(self):
  self.assertEqual(guard.top_dates(),[])
  self.assertEqual(guard.manifest(),{})
 def test_exact_normal_outputs(self):
  adoptions=json.loads((ROOT/'scripts/weekly_normal_adoptions.json').read_text('utf8'))
  self.assertEqual(set(adoptions),{'261116','261117','261118','261119','261120'})
  for date,adoption in adoptions.items():
   with self.subTest(date=date):
    self.assertEqual(set(adoption['adopted']),{'share/'+date+'/'+s for s in ['index.html','daily/index.html','instructions/index.html']})
    for rel,digest in adoption['adopted'].items():
     data=(ROOT/rel).read_bytes()
     self.assertEqual(hashlib.sha256(data).hexdigest(),digest,rel)
     html=data.decode('utf8');self.assertFalse(guard.readonly(html))
     config=json.loads(re.search(r'<script id="shared-ledger-config" type="application/json">(.*?)</script>',html,re.S)[1])
     self.assertFalse(config.get('sourceOnly',False))
     self.assertEqual(config['date'],date)
     self.assertTrue(config['cases'])
     self.assertTrue(all(len(x['base'])==15 for x in config['cases']))
     if date=='261116':self.assertEqual([x['cs'] for x in config['cases']],['51400871','51400870','51400869'])
 def test_top_existing_routes(self):
  self.assertEqual(generate_portal.validate_portal_top_only_output(ROOT),[])
  text=(ROOT/'portal/index.html').read_text('utf8')
  for date in ['261116','261117','261118','261119','261120']:self.assertIn('../share/'+date+'/',text)
 def test_bad_retirement_pair_rejected(self):
  before='<div data-source-only="true">not approved</div>'
  after=(ROOT/'share/261116/index.html').read_text('utf8')
  self.assertEqual(guard.portal(before,after,'','261116',lambda *a:['wrong']),['Explicit provisional retirement/adoption plan required'])
 def test_normal_path_preserves_validator(self):
  text=(ROOT/'share/261116/index.html').read_text('utf8')
  self.assertEqual(guard.portal(text,text,'','261116',lambda *a:['ordinary failure']),['ordinary failure'])

if __name__=='__main__':unittest.main()
