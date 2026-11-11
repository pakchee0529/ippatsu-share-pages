"""Private fixture test driver; paths supplied explicitly through environment."""
import sys
sys.dont_write_bytecode=True
import os,json,re,copy,traceback
from pathlib import Path
import repair_legacy_archive_maps as a
root=Path(os.environ['LEGACY_TEST_ROOT']);repo=Path(os.environ['LEGACY_TEST_REPO']);modern=Path(os.environ['LEGACY_TEST_MODERN']);gpspath=Path(os.environ['LEGACY_TEST_GPS']);manifest=json.loads(Path(os.environ['LEGACY_TEST_MANIFEST']).read_text(encoding='utf-8'))
root.mkdir(parents=True,exist_ok=True)
m,p,c=a.dependencies(modern,repo/'scripts',manifest['helpers']);gps=m.load_gps(gpspath,manifest['gps_sha256'],p)
results=[]
def test(name,fn):
 try:fn();results.append(dict(name=name,status='PASS'));print(name+' PASS',flush=True)
 except Exception as e:results.append(dict(name=name,status='FAIL',reason=str(e)));traceback.print_exc()
def reject(fn):
 try:fn()
 except Exception:return
 raise AssertionError('Expected rejection')
def inventory(path):
 return {str(f.relative_to(path)):a.sha(f.read_bytes()) for f in path.rglob('*') if f.is_file() and '.git' not in f.parts}
before=inventory(repo);helper_hash=a.sha(modern.read_bytes());gps_hash=a.sha(gpspath.read_bytes());fixtures={}
def promote_control(text,role):
 match=re.search(r'class="([^"]*)"',text);target='btn-map-'+role
 if target in match[1].split():return text
 return text[:match.end(1)]+' '+target+text[match.end(1):]
for row in manifest['pages']:
 date=row['date'];current=m.proof_bytes(repo,row['current'],date,'current');source=m.proof_bytes(repo,row['source'],date,'source');fixtures[date]=(current,source,row)
 def check(cur=current,src=source,r=row):
  out,report=a.repair(cur,src,r['date'],gps,m,p,c,r);old=a.parse(cur.decode(),r['date'],m,c);new=a.parse(out.decode(),r['date'],m,c)
  assert a.business(old,m)==a.business(new,m)
  assert c.parse_page(out.decode(),r['date'])==new['views']
  for pattern in [r'<table\b.*?</table>',r'<h2\b.*?</h2>',r'<p class="archive-status-line">.*?</p>',r'<a\b[^>]*href="[^"]*(?:forms|saved-forms)[^"]*"[^>]*>.*?</a>']:
   assert re.findall(pattern,cur.decode(),re.S)==re.findall(pattern,out.decode(),re.S)
  # Whole runtime unchanged except the one overall-points array.
  def runtime(text):
   s=m.one([s for s in re.findall(r'<script\b[^>]*>.*?</script>',text,re.S) if 'var twoMaps' in s],'runtime');x,y=m.point_range(s);return s[:x]+s[y:]
  assert runtime(cur.decode())==runtime(out.decode())
  for key,v in old['views'].items():
   ns=new['slots'][key];os=old['slots'][key]
   if v.single_url:assert promote_control(old['dom'].content(os[1]),'single')==new['dom'].content(ns[1])
   if v.start and v.end:assert promote_control(old['dom'].content(os[2]),'two')==new['dom'].content(ns[2]) and old['dom'].content(os[4][0])==new['dom'].content(ns[4][0])
   if v.representative:
    # Full old point serialized object must remain verbatim somewhere in output.
    raw=old['text'][old['pr'][0]:old['pr'][1]]
    for obj in re.findall(r'\{[^{}]*\}',raw):
     if c.identity(json.loads(obj)['management_no'])==key:assert obj in out.decode()
  assert a.repair(cur,src,r['date'],gps,m,p,c,r)[0]==out
 test('real_'+date,check)
cur,src,row=fixtures['260615'];date=row['date']
def repair(cur_=cur,src_=src,row_=row,gps_=gps):return a.repair(cur_,src_,date,gps_,m,p,c,row_)
mutations={
 'wrong_current_date':lambda:repair(cur.replace(b'260615',b'260616',1)),
 'unknown_runtime':lambda:repair(cur.replace(b'var twoMaps',b'var unknownMaps',1)),
 'malformed_current_dom':lambda:repair(cur.replace(b'</h1>',b'</h2>',1)),
 'duplicate_card':lambda:repair(cur.replace(b'</body>',re.search(br'<article\b.*?</article>',cur,re.S)[0]+b'</body>',1)),
 'duplicate_id':lambda:repair(cur.replace(b'id="two-geo-1"',b'id="two-geo-0"',1)),
 'broken_canvas_binding':lambda:repair(cur.replace(b'data-two-map="share-two-map-0"',b'data-two-map="missing-map"',1)),
 'invalid_map_url':lambda:repair(src_=src.replace(b'https://www.google.com/maps?',b'https://evil.invalid/maps?',1)),
 'source_wrong_title':lambda:repair(src_=src.replace('2026年06月15日'.encode(),'2026年06月16日'.encode(),1)),
 'unknown_source_card':lambda:repair(src_=src.replace(b'<article class="card"',b'<article class="unknown"',1)),
 'duplicate_source_id':lambda:repair(src_=src.replace(b'id="two-geo-1"',b'id="two-geo-0"',1)),
 'source_coordinate_conflict':lambda:repair(src_=src.replace(b'34.40742',b'34.40743',1)),
 'missing_gps':lambda:repair(gps_={}),
 'unknown_endpoint_coordinate':lambda:repair(cur.replace(b'"lat": 0.0',b'"lat": 1.0',1)),
 'wrong_current_identity':lambda:repair(cur.replace(b'515 06487',b'515 99999',1)),
 'source_missing_evidence':lambda:repair(src_=src.replace(b'<article class="card"',b'<article class="not-card"',1)),
}
def span_panel_mutation():
 original=re.search(br'<div class="two-map-wrap"[^>]*>.*?</div></div>',cur,re.S)[0]
 altered=original.replace(b'<div class="two-map-wrap"',b'<span class="two-map-wrap"',1)
 altered=altered[:-6]+b'</span>'
 return repair(cur.replace(original,altered,1))
mutations.update({
 'hidden_overall_canvas':lambda:repair(cur.replace(b'id="share-map"',b'id="share-map" hidden',1)),
 'hidden_enabled_two_style':lambda:repair(cur.replace(b'data-two-open',b'style="display:none" data-two-open',1)),
 'wrong_panel_tag':span_panel_mutation,
 'handler_target_outside_cards':lambda:repair(cur.replace(b'</body>',b'<button data-two-open></button></body>',1)),
 'hidden_card_ancestor':lambda:repair(cur.replace(b'<article ',b'<article hidden ',1)),
 'canvas_extra_attribute':lambda:repair(cur.replace(b'class="share-two-map-canvas"',b'class="share-two-map-canvas" style="display:none"',1)),
 'boolean_zero_sentinel':lambda:repair(cur.replace(b'"lat": 0.0',b'"lat": false',1)),
 'invalid_nearby_payload':lambda:repair(cur.replace(b'{"a": {',b'{"nearby": "wrong", "a": {',1)),
})
for name,fn in mutations.items():test(name,lambda fn=fn:reject(fn))
for field,value in [('repair_roles',{}),('source_exclusions',{'x':{'label':'x','reason':'ignored'}}),('unavailable_roles',{}),('full_span_join',{})]:
 r=copy.deepcopy(row);r[field]=value;test('bad_manifest_'+field,lambda r=r:reject(lambda:repair(row_=r)))
# Extension contracts are tested with real historical fixtures, not invented positive maps.
def actual_repair(date,current=None,source=None,row_override=None):
 x,y,z=fixtures[date];return a.repair(current if current is not None else x,source if source is not None else y,date,gps,m,p,c,row_override or z)
def mutate_source(date,old,new):
 x,y,z=fixtures[date];assert old in y;return actual_repair(date,source=y.replace(old,new,1))
if '260629' in fixtures:
 test('whitespace_does_not_change_pole_number',lambda:reject(lambda:mutate_source('260629','湯塩　14N5～14N6'.encode(),'湯塩　14N5～14N7'.encode())))
 test('whitespace_does_not_change_direction',lambda:reject(lambda:mutate_source('260629','湯塩　14N5～14N6'.encode(),'湯塩　14S5～14N6'.encode())))
 test('whitespace_does_not_change_separator',lambda:reject(lambda:mutate_source('260629','湯塩　14N5～14N6'.encode(),'湯塩　14N5?14N6'.encode())))
if '260714' in fixtures:
 x,y,z=fixtures['260714'];bad=copy.deepcopy(z);bad['retained_url_differences']={}
 test('retained_url_policy_explicit',lambda:reject(lambda:actual_repair('260714',row_override=bad)))
 test('retained_url_wrong_coordinate_rejected',lambda:reject(lambda:actual_repair('260714',current=x.replace(b'https://www.google.com/maps?q=',b'https://www.google.com/maps?q=1',1))))
if '260722' in fixtures:
 test('source_off_by_two_rejected',lambda:reject(lambda:mutate_source('260722',b'data-two-wrap="two-wrap-0"',b'data-two-wrap="two-wrap-99"')))
 x,y,z=fixtures['260722'];bad=copy.deepcopy(z);bad['source_ui_anomalies']=[]
 test('source_ui_anomaly_explicit',lambda:reject(lambda:actual_repair('260722',row_override=bad)))
 test('output_binding_not_relaxed',lambda:reject(lambda:actual_repair('260722',current=x.replace(b'data-two-wrap="two-wrap-1"',b'data-two-wrap="two-wrap-0"',1))))
if '260529' in fixtures:
 x,y,z=fixtures['260529'];test('card_tail_unknown_date_rejected',lambda:reject(lambda:a.parse(x.decode().replace('260529','260530'),'260530',m,c)))
saved_template_bytes=p.__verified_source_bytes__;p.__verified_source_bytes__+=b'\n# changed'
test('overall_template_provenance_rejected',lambda:reject(lambda:a.parse(cur.decode(),date,m,c)))
p.__verified_source_bytes__=saved_template_bytes
bad_modern=root/'wrong-modern.py';bad_modern.write_bytes(modern.read_bytes()+b'\n# changed')
test('modern_hash_rejected',lambda:reject(lambda:a.dependencies(bad_modern,repo/'scripts',manifest['helpers'])))
original=sys.modules['_pinned_legacy_map_base'];sys.modules['_pinned_legacy_map_base']=object()
test('modern_import_provenance_rejected',lambda:reject(lambda:a.dependencies(modern,repo/'scripts',manifest['helpers'])))
sys.modules['_pinned_legacy_map_base']=original
saved_file=original.__file__;original.__file__='WRONG METADATA'
test('modern_file_metadata_rejected',lambda:reject(lambda:a.dependencies(modern,repo/'scripts',manifest['helpers'])))
original.__file__=saved_file
saved_bytes=original.__verified_source_bytes__;original.__verified_source_bytes__=b'wrong'
test('modern_verified_bytes_rejected',lambda:reject(lambda:a.dependencies(modern,repo/'scripts',manifest['helpers'])))
original.__verified_source_bytes__=saved_bytes
bad_lock=dict(manifest['helpers']);bad_lock['archive_map_contract.py']='0'*64
test('helper_hash_rejected',lambda:reject(lambda:a.dependencies(modern,repo/'scripts',bad_lock)))
test('out_inside_repo',lambda:reject(lambda:a.run(manifest,repo,repo/'scripts',gpspath,modern,repo/'bad-output')))
bad=copy.deepcopy(manifest);bad['pages'][-1]['current']['sha256']='0'*64
out=root/'must-not-exist'
test('batch_all_preflight_no_output',lambda:reject(lambda:a.run(bad,repo,repo/'scripts',gpspath,modern,out)))
assert not out.exists()
test('repeat_generation',lambda:a.run(manifest,repo,repo/'scripts',gpspath,modern,root/'candidate-a'))
test('repeat_generation_again',lambda:a.run(manifest,repo,repo/'scripts',gpspath,modern,root/'candidate-b'))
assert inventory(root/'candidate-a')==inventory(root/'candidate-b')
test('existing_output_refused',lambda:reject(lambda:a.run(manifest,repo,repo/'scripts',gpspath,modern,root/'candidate-a')))
if os.environ.get('LEGACY_PREVIOUS_FREEZE'):
 previous=json.loads(Path(os.environ['LEGACY_PREVIOUS_FREEZE']).read_text(encoding='utf-8'))
 for path,digest in previous['candidate_files'].items():
  baseline=Path(previous['candidate_directory'])/path;assert a.sha(baseline.read_bytes())==digest
  date=Path(path).parent.name;promoted,receipt=a.semantic_classes(baseline.read_text(encoding='utf-8'),date,m,c)
  assert promoted.encode()==(root/'candidate-a'/path).read_bytes(),'Change beyond approved semantic class '+path
 results.append(dict(name='prior_11_only_semantic_class_exceptions',status='PASS'))
assert before==inventory(repo),'Source repository changed'
assert helper_hash==a.sha(modern.read_bytes()) and gps_hash==a.sha(gpspath.read_bytes())
results += [dict(name=x,status='PASS') for x in ['all_source_repository_files_unchanged','modern_unchanged','gps_unchanged','repeat_output_byte_equal','failure_no_partial_output']]
report=dict(tests=results,passed=sum(x['status']=='PASS' for x in results),failed=sum(x['status']=='FAIL' for x in results),source_files_checked=len(before),candidate_hashes=inventory(root/'candidate-a'),browser='NOT RUN; connection unavailable')
(root/'TEST-REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['tests','candidate_hashes']},indent=2));sys.exit(bool(report['failed']))
