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
before=inventory(repo);(root/'SOURCE-BEFORE.json').write_text(json.dumps(before,indent=2),encoding='utf-8');helper_hash=a.sha(modern.read_bytes());gps_hash=a.sha(gpspath.read_bytes());fixtures={}
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
# Fixed-exception semantic tests rebind only the test-memory byte lock. No output is written.
def exceptional_reject(date,mutate_current=None,mutate_source=None,gps_override=None):
 current,source,row=fixtures[date];current=mutate_current(current) if mutate_current else current;source=mutate_source(source) if mutate_source else source
 saved=a.EXCEPTION_LOCKS[date];a.EXCEPTION_LOCKS[date]=dict(current=a.sha(current),source=a.sha(source))
 try:reject(lambda:a.source_projection(current,source,date,gps_override if gps_override is not None else gps,m,p,c))
 finally:a.EXCEPTION_LOCKS[date]=saved
if '260709' in fixtures:
 for name,old,new in [('wrong_corrupt_name',b'???6S5W6?6S5W6N1',b'OTHER6S5W6?6S5W6N1'),('wrong_point_coord',b'34.39576',b'34.39577'),('wrong_management',b'515 13023',b'515 99999')]:
  test('fixed709_'+name,lambda old=old,new=new:exceptional_reject('260709',mutate_source=lambda b:b.replace(old,new)))
 test('fixed709_duplicate_card',lambda:exceptional_reject('260709',mutate_source=lambda b:b.replace(b'</body>',re.search(br'<article\b.*?</article>',b,re.S)[0]+b'</body>')))
 test('fixed709_gps_conflict',lambda:exceptional_reject('260709',gps_override={**gps,'吉野平6S5W6':(34.39577,135.78926)}))
 test('fixed709_current_label_change',lambda:exceptional_reject('260709',mutate_current=lambda b:b.replace('吉野平6S5W6～6S5W6N1'.encode(),'吉野平6S5W6～6S5W6N2'.encode())))
 x,y,z=fixtures['260709'];generated,_=actual_repair('260709');old=a.parse(x.decode(),'260709',m,c);new=a.parse(generated.decode(),'260709',m,c)
 assert new['views']['51513023'].start is None and new['views']['51513023'].end is None
 assert promote_control(old['dom'].content(old['slots']['51513023'][2]),'two')==new['dom'].content(new['slots']['51513023'][2])
 results.append(dict(name='709_disabled_two_no_endpoints_created',status='PASS'))
if '260722' in fixtures:
 x,y,z=fixtures['260722'];old=a.parse(x.decode(),'260722',m,c);generated,_=actual_repair('260722');new=a.parse(generated.decode(),'260722',m,c);key='51407415'
 assert old['dom'].content(old['slots'][key][0])==new['dom'].content(new['slots'][key][0]) and new['views'][key]==old['views'][key]
 assert key not in new['points'] and len(old['points'])==6 and len(new['points'])==5
 results.append(dict(name='722_zero_only_removed_disabled_case_byte_equal',status='PASS'))
 def alter_point(b,field,value):
  text=b.decode();page=a.parse(text,'260722',m,c);lo,hi=page['pr'];points=json.loads(text[lo:hi]);points[0][field]=value;return (text[:lo]+json.dumps(points,ensure_ascii=False)+text[hi:]).encode()
 test('fixed722_nonzero_point_not_removed',lambda:exceptional_reject('260722',mutate_current=lambda b:alter_point(b,'lat',34.0)))
 test('fixed722_wrong_label_not_removed',lambda:exceptional_reject('260722',mutate_current=lambda b:alter_point(b,'name','別区間')))
 test('fixed722_wrong_case_not_removed',lambda:exceptional_reject('260722',mutate_current=lambda b:alter_point(b,'management_no','51407434')))
 test('fixed722_repeated_sentinel_removal_rejected',lambda:reject(lambda:a.remove_zero_sentinel(generated.decode(),'260722',m,c)))
 test('fixed722_source_identity_change',lambda:exceptional_reject('260722',mutate_source=lambda b:b.replace(b'51407415',b'51409999')))
def partial_reject(mutate_current=None,mutate_source=None):
 current,source,row=fixtures['260630'];current=mutate_current(current) if mutate_current else current;source=mutate_source(source) if mutate_source else source;saved=a.PARTIAL_LOCK;a.PARTIAL_LOCK=dict(current=a.sha(current),source=a.sha(source))
 try:reject(lambda:a.partial_plan(current,source,'260630',gps,m,p,c))
 finally:a.PARTIAL_LOCK=saved
def change_unknown_payload(b):
 text=b.decode();page=a.parse(text,'260630',m,c);n=page['slots']['51410138'][4][0];chunk=page['dom'].content(n);return text.replace(chunk,chunk.replace('"lat": 0.0','"lat": 34.31689',1),1).encode()
def change_unknown_point(b,field,value):
 text=b.decode();page=a.parse(text,'260630',m,c);lo,hi=page['pr'];points=json.loads(text[lo:hi]);q=next(x for x in points if c.identity(x['management_no'])=='51410138');q[field]=value;return (text[:lo]+json.dumps(points,ensure_ascii=False)+text[hi:]).encode()
test('partial_nonzero_endpoint_rejected',lambda:partial_reject(mutate_current=change_unknown_payload))
test('partial_nonzero_overall_rejected',lambda:partial_reject(mutate_current=lambda b:change_unknown_point(b,'lat',34.31689)))
test('partial_other_case_rejected',lambda:partial_reject(mutate_current=lambda b:b.replace(b'514 10138',b'514 10139')))
test('partial_other_current_label_rejected',lambda:partial_reject(mutate_current=lambda b:b.replace('田殿71E3N1～引込'.encode(),'田殿71E3N1～別柱'.encode())))
test('partial_source_word_not_equated',lambda:partial_reject(mutate_source=lambda b:b.replace('引き込み'.encode(),'引込'.encode())))
test('partial_single_url_change_rejected',lambda:partial_reject(mutate_current=lambda b:b.replace(b'q=34.31689,135.67107',b'q=34.31690,135.67107')))
x,y,z=fixtures['260630'];out,report=actual_repair('260630');old=a.parse(x.decode(),'260630',m,c);new=a.parse(out.decode(),'260630',m,c);key='51410138'
assert new['views'][key]==old['views'][key] and key not in new['points'] and 'disabled' in new['slots'][key][2].attrs and not new['slots'][key][4] and not new['slots'][key][5]
assert report['partial_date'] and report['unresolved_case']['source_case_used'] is False and report['map_roles'][key]==[]
assert set(k for k,r in report['map_roles'].items() if r)=={'51401633','51401634'}
kept='51409716';before_card=old['dom'].content(old['slots'][kept][0])
for role,n in [('single',old['slots'][kept][1]),('two',old['slots'][kept][2])]:before_card=before_card.replace(old['dom'].content(n),promote_control(old['dom'].content(n),role),1)
assert before_card==new['dom'].content(new['slots'][kept][0])
results.extend(dict(name=n,status='PASS') for n in ['partial_unresolved_case_no_values_copied','partial_exact_six_roles_only','partial_complete_case_preserved_except_semantic_classes'])
bad=copy.deepcopy(z);bad['unresolved_case']['source_case_used']=True
test('partial_manifest_scope_rejected',lambda:reject(lambda:actual_repair('260630',row_override=bad)))
def duplicate_reject(mutate_source=None,mutate_current=None,gps_override=None):
 current,source,row=fixtures['260716'];source=mutate_source(source) if mutate_source else source;current=mutate_current(current) if mutate_current else current;saved=a.DUPLICATE_LOCK;a.DUPLICATE_LOCK=dict(current=a.sha(current),source=a.sha(source))
 try:reject(lambda:a.source_projection(current,source,'260716',gps_override if gps_override is not None else gps,m,p,c))
 finally:a.DUPLICATE_LOCK=saved
def duplicate_cards_edit(b,mode):
 text=b.decode();match=next(c.CARD.finditer(text));block=match[0];dom=m.DOM(block);nodes=[n for n in dom.nodes if n.tag=='a' and n.cls('btn-map')]
 first,second=[dom.content(n) for n in nodes]
 if mode=='swap':changed=m.edits_apply(block,[(nodes[0].start,nodes[0].end,second),(nodes[1].start,nodes[1].end,first)])
 else:changed=block[:nodes[1].end]+first+block[nodes[1].end:]
 return (text[:match.start()]+changed+text[match.end():]).encode()
def duplicate_points_edit(b,mode):
 text=b.decode();pm=re.search(r'var\s+POINTS\s*=\s*',text);points,used=json.JSONDecoder().raw_decode(text[pm.end():]);raw=text[pm.end():pm.end()+used]
 if mode=='tiny':raw=re.sub(r'("lat"\s*:\s*)34\.303805(?!\d)',r'\g<1>34.303805000000000001',raw,count=1)
 else:
  if mode=='coordinate':points[0]['lat']=34.4
  elif mode=='duplicate':points.append(dict(points[0]))
  elif mode=='case':points[0]['management_no']=points[1]['management_no']
  raw=json.dumps(points,ensure_ascii=False)
 return (text[:pm.end()]+raw+text[pm.end()+used:]).encode()
test('duplicate_count_rejected',lambda:duplicate_reject(mutate_source=lambda b:duplicate_cards_edit(b,'extra')))
test('duplicate_order_rejected',lambda:duplicate_reject(mutate_source=lambda b:duplicate_cards_edit(b,'swap')))
test('duplicate_caption_rejected',lambda:duplicate_reject(mutate_source=lambda b:b.replace('現場地図を開く'.encode(),'地図を開く'.encode(),1)))
test('duplicate_other_case_rejected',lambda:duplicate_reject(mutate_source=lambda b:re.sub(rb'(<[^>]*class="item-mgmt"[^>]*>)[^<]+',rb'\g<1>51409999',b,count=1)))
test('duplicate_other_label_rejected',lambda:duplicate_reject(mutate_source=lambda b:b.replace('湯塩14N12～14N13'.encode(),'湯塩14N12～14N14'.encode(),1)))
for mode in ['coordinate','duplicate','case','tiny']:test('duplicate_points_'+mode+'_rejected',lambda mode=mode:duplicate_reject(mutate_source=lambda b:duplicate_points_edit(b,mode)))
test('duplicate_gps_decimal_mismatch_rejected',lambda:duplicate_reject(gps_override={**gps,'湯塩14N12':(34.303551,135.72712)}))
test('duplicate_current_url_replacement_rejected',lambda:duplicate_reject(mutate_current=lambda b:b.replace(b'q=34.303309999999996,135.73045000000002',b'q=34.30331,135.73045')))
x,y,z=fixtures['260716'];out,report=actual_repair('260716');old=a.parse(x.decode(),'260716',m,c);new=a.parse(out.decode(),'260716',m,c)
assert len(report['exception_receipt'])==5
for key in old['views']:
 assert old['views'][key].single_url==new['views'][key].single_url
 assert promote_control(old['dom'].content(old['slots'][key][1]),'single')==new['dom'].content(new['slots'][key][1])
 assert report['map_roles'][key] and 'single_url' not in report['map_roles'][key]
results.append(dict(name='duplicate_all_five_current_single_literals_preserved',status='PASS'))
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
 results.append(dict(name='prior_frozen_15_outputs_unchanged',status='PASS'))
after_inventory=inventory(repo);(root/'SOURCE-AFTER.json').write_text(json.dumps(after_inventory,indent=2),encoding='utf-8');assert before==after_inventory,'Source repository changed'
assert helper_hash==a.sha(modern.read_bytes()) and gps_hash==a.sha(gpspath.read_bytes())
results += [dict(name=x,status='PASS') for x in ['all_source_repository_files_unchanged','modern_unchanged','gps_unchanged','repeat_output_byte_equal','failure_no_partial_output']]
report=dict(tests=results,passed=sum(x['status']=='PASS' for x in results),failed=sum(x['status']=='FAIL' for x in results),source_files_checked=len(before),candidate_hashes=inventory(root/'candidate-a'),browser='NOT RUN; connection unavailable')
(root/'TEST-REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['tests','candidate_hashes']},indent=2));sys.exit(bool(report['failed']))
