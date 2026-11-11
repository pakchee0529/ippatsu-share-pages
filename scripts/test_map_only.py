import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,re,copy,unittest,hashlib,os
import repair_archive_maps as r
ROOT=Path(os.environ['MAP_REPAIR_TEST_OUTPUT_ROOT']).resolve()
REPO=Path(os.environ['MAP_REPAIR_TEST_REPO']).resolve()
MAN=json.loads(Path(os.environ['MAP_REPAIR_TEST_MANIFEST']).read_text(encoding='utf-8'))
GPS=Path(os.environ['MAP_REPAIR_TEST_GPS']).resolve()
P,C=r.load_dependencies(REPO/'scripts',MAN['helpers']);G=r.load_gps(GPS,MAN['gps_sha256'],P)
FIX={row['date']:(r.proof_bytes(REPO,row['current'],row['date'],'current'),r.proof_bytes(REPO,row['source'],row['date'],'source'),row['repair_roles']) for row in MAN['pages']}
def repaired(date='261030',a=None,b=None,g=None,roles=None):
 x,y,z=FIX[date];return r.repair(x if a is None else a,y if b is None else b,date,G if g is None else g,P,C,z if roles is None else roles)
def fail(**kw):
 try:repaired(**kw)
 except (ValueError,KeyError):return
 raise AssertionError('Expected fail closed')
def snapshot():
 return {str(p.relative_to(REPO)):r.sha(p.read_bytes()) for p in REPO.rglob('*') if p.is_file() and '.git' not in p.relative_to(REPO).parts}

def independent_check(date,before,after):
 # Independent business-byte selections, not the production stripping function.
 patterns=[rb'<table\b.*?</table>',rb'<span class="status-pill.*?</span>',rb'<p class="archive-status-line".*?</p>',rb'<a\b[^>]*href="[^"]*(?:forms|saved-forms)[^"]*".*?</a>',rb'<section id="final-ledger-forms".*?</section>',rb'<h2 class="card-title".*?</h2>',rb'<p class="item-mgmt".*?</p>',rb'<[^>]+data-quantity-[^>]+>[^<]*']
 checks={str(i):re.findall(p,before,re.S)==re.findall(p,after,re.S) for i,p in enumerate(patterns)}
 assert all(checks.values()),checks
 if date=='261028':assert C.CARD.findall(before.decode())==C.CARD.findall(after.decode()),'All original 10/28 cards must be byte identical'
 # Runtime script byte-identical including handlers; new refs must resolve locally.
 def runtime(b):
  result=[]
  for s in re.findall(rb'<script\b[^>]*>.*?</script>',b,re.S):
   if b'var twoMaps' in s:
    text=s.decode();a,z=r.point_range(text);result.append((text[:a]+text[z:]).encode())
  return result
 assert runtime(before)==runtime(after) and len(runtime(after))==1
 tags=C.Tags(after.decode()).tags;ids={a['id']:a for _,a in tags if 'id' in a}
 for tag,a in tags:
  if 'data-two-open' in a:
   assert tag=='button' and all(a[k] in ids for k in ('data-two-wrap','data-two-map','data-two-json'))
   assert a['aria-controls']==a['data-two-wrap'] and ids[a['data-two-json']]['type']=='application/json'
 return {'protected_patterns_equal':checks,'map_runtime_byte_equal':True,'handler_refs_resolve':True,'all_261028_cards_byte_equal':date=='261028'}

class Tests(unittest.TestCase):
 def helper_bytes_fixture(self,mode):
  import subprocess,tempfile,py_compile
  folder=Path(tempfile.mkdtemp(prefix='helper-bytes-',dir=ROOT))
  clean=b'MARKER="clean"\n';stale=b'MARKER="stale"\n'
  helper=folder/'generate_portal.py';helper.write_bytes(stale)
  stamp=helper.stat();py_compile.compile(str(helper),doraise=True)
  helper.write_bytes(clean);os.utime(helper,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
  for name in ['archive_map_contract.py','portal_immediate_status_client.py']:(folder/name).write_bytes(b'VALUE=1\n')
  code=r"""import sys,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,sys.argv[1])
import repair_archive_maps as r
folder=Path(sys.argv[2]);mode=sys.argv[3]
locks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.py')}
if mode=='swap':
 original=r.sha
 def changing_sha(data):
  digest=original(data)
  if b'MARKER' in data:(folder/'generate_portal.py').write_bytes(b'MARKER="stale"\n')
  return digest
 r.sha=changing_sha
p,c=r.load_dependencies(folder,locks)
assert p.MARKER=='clean',p.MARKER
assert p.__verified_source_bytes__==b'MARKER="clean"\n'
print('verified-byte execution passed')
"""
  result=subprocess.run([sys.executable,'-B','-c',code,str(Path(__file__).resolve().parent),str(folder),mode],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
 def test_gps_source_swap_after_hash(self):
  import tempfile
  from unittest.mock import patch
  folder=Path(tempfile.mkdtemp(prefix='gps-bytes-',dir=ROOT));path=folder/'gps.json'
  original=b'{"Pole1":"34,135"}';path.write_bytes(original);read=Path.read_bytes
  def swapping(p):
   data=read(p)
   if p==path:p.write_bytes(b'{"Pole1":"35,136"}')
   return data
  with patch.object(Path,'read_bytes',swapping):gps=r.load_gps(path,r.sha(original),P)
  self.assertEqual(gps,{'POLE1':(34.0,135.0)})
 def test_stale_pyc_never_executed(self):self.helper_bytes_fixture('pyc')
 def test_source_swap_after_hash_never_executed(self):self.helper_bytes_fixture('swap')
 def test_reparse_path_rejected(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  with patch.object(r.os,'lstat',return_value=SimpleNamespace(st_mode=0o100644,st_file_attributes=0x400)):
   with self.assertRaises(ValueError):r.no_reparse(ROOT/'synthetic-reparse')
 def test_import_cache_module_rejected(self):
  from unittest.mock import patch
  with patch.dict(sys.modules,{'generate_portal':object()}):
   with self.assertRaises(ValueError):r.load_dependencies(REPO/'scripts',MAN['helpers'])
 def test_symlink_path_rejected(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  with patch.object(r.os,'lstat',return_value=SimpleNamespace(st_mode=0o120777,st_file_attributes=0)):
   with self.assertRaises(ValueError):r.no_reparse(ROOT/'synthetic-symlink')

 def test_success_real_28(self):self.assertTrue(repaired('261028')[1]['business_bytes_equal'])
 def test_success_real_30(self):self.assertTrue(repaired()[1]['business_bytes_equal'])
 def test_current_other_date(self):fail(a=FIX['261030'][0].replace(b'261030',b'261029'))
 def test_source_other_date(self):fail(b=FIX['261030'][1].replace('2026年10月30日'.encode(),'2026年10月29日'.encode()))
 def test_other_identity(self):fail(b=FIX['261030'][1].replace(b'51409511',b'51409512'))
 def test_other_span(self):fail(b=FIX['261030'][1].replace('鹿場20S1'.encode(),'鹿場20S9'.encode()))
 def test_duplicate_card(self):
  a=FIX['261030'][0];card=C.CARD.search(a.decode())[0].encode();fail(a=a.replace(b'</main>',card+b'</main>'))
 def test_invalid_url(self):fail(b=FIX['261030'][1].replace(b'https://www.google.com/maps?',b'https://evil.example/maps?'))
 def test_javascript_url(self):fail(b=FIX['261030'][1].replace(b'https://www.google.com/maps?',b'javascript:alert?'))
 def test_bad_gps(self):
  g=dict(G);k=P._share_gps_lookup_key('鹿場20S1');g[k]=(34.1,135.2);fail(g=g)
 def test_absent_gps(self):
  g=dict(G);del g[P._share_gps_lookup_key('鹿場20S1')];fail(g=g)
 def test_malformed_dom(self):fail(a=FIX['261030'][0].replace(b'</article>',b'</section>',1))
 def test_duplicate_dom_id(self):fail(a=FIX['261030'][0].replace(b'<main>',b'<main id="map-heading">'))
 def test_unknown_template(self):fail(a=FIX['261030'][0].replace(b'map-section map-empty',b'map-section strange-map'))
 def test_missing_handler(self):fail(a=FIX['261030'][0].replace(b'var twoMaps',b'var noHandler'))
 def test_mutated_handler(self):fail(a=FIX['261030'][0].replace(b'JSON.parse(jsonEl.textContent',b'JSON.parse(brokenRef.textContent'))
 def test_duplicate_scope_role(self):
  roles=copy.deepcopy(FIX['261030'][2]);roles['51409511'].append('start');fail(roles=roles)
 def test_unknown_card_script(self):fail(a=FIX['261030'][0].replace(b'<article class="card card-planned-incomplete" data-planned-index="0">',b'<article class="card card-planned-incomplete" data-planned-index="0"><script>alert(1)</script>'))
 def test_duplicate_control(self):
  a=FIX['261030'][0];m=re.search(rb'<button[^>]+btn-map-single.*?</button>',a,re.S);fail(a=a[:m.start()]+m[0]+a[m.start():])
 def test_no_source(self):fail(b=b'')
 def test_missing_role_scope(self):fail(roles={})
 def test_unknown_scope_role(self):fail(roles={'51409511':['bogus']})
 def test_overwrite_retained_role(self):
  roles=copy.deepcopy(FIX['261028'][2]);roles['51406421']=['representative'];fail(date='261028',roles=roles)
 def test_alias(self):
  a=b'<title>'+('離隔表'.encode())+b'</title><article class="ledger-view" data-management-no="51409511" data-final-ledger-identity="x"></article>';fail(a=a)
 def test_repaired_idempotent_read(self):
  a,report=repaired();b,report2=repaired(a=a,roles={});self.assertEqual(a,b)
 def test_snapshot_hash(self):
  m=copy.deepcopy(MAN);m['pages'][0]['working_sha256']='0'*64
  with self.assertRaises(ValueError):r.run(m,REPO,REPO/'scripts',GPS,ROOT/'must-not-exist-hash')
  self.assertFalse((ROOT/'must-not-exist-hash').exists())
 def test_atomic_batch_failure(self):
  m=copy.deepcopy(MAN);m['pages'][1]['source']['blob']='0'*40
  with self.assertRaises(ValueError):r.run(m,REPO,REPO/'scripts',GPS,ROOT/'must-not-exist-batch')
  self.assertFalse((ROOT/'must-not-exist-batch').exists())
 def test_unknown_helper_hash(self):
  m=copy.deepcopy(MAN);m['helpers']['archive_map_contract.py']='0'*64
  with self.assertRaises(ValueError):r.run(m,REPO,REPO/'scripts',GPS,ROOT/'must-not-exist-helper')
 def test_output_inside_repo(self):
  with self.assertRaises(ValueError):r.run(MAN,REPO,REPO/'scripts',GPS,REPO/'forbidden-map-output')
 def test_preserved_guard_not_weakened(self):
  a,b,roles=FIX['261028'];source=C.parse_page(b.decode(),'261028')
  with self.assertRaises(ValueError):C.verify_preserved(a.decode(),'261028',[source])

if __name__=='__main__':
 before=snapshot();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);result=unittest.TextTestRunner(verbosity=2).run(suite)
 reports=[]
 for date,(a,b,roles) in FIX.items():
  data,rep=repaired(date);rep['independent']=independent_check(date,a,data);reports.append(rep)
  assert data==(ROOT/'candidate/portal/archive'/date/'index.html').read_bytes()
 (ROOT/'INDEPENDENT-VERIFICATION.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
 after=snapshot();assert before==after,'Source repo files changed'
 summary={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'source_repo_file_count':len(before),'source_repo_all_files_unchanged':True,'browser':'NOT EXECUTED: connection unavailable','candidate_files':[str(p.relative_to(ROOT/'candidate')) for p in (ROOT/'candidate').rglob('*') if p.is_file()]}
 (ROOT/'TEST-RESULTS.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary));sys.exit(not result.wasSuccessful())
