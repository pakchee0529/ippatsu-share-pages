"""Index existing public immutable forms only. No DB/API/credentials."""
from pathlib import Path
from html import unescape
from urllib.parse import urljoin,urlsplit
import json,re,unicodedata,hashlib,shutil,datetime,argparse
P=Path(__file__).parent.resolve()
args=argparse.ArgumentParser();args.add_argument('--repo-root',type=Path,required=True);args.add_argument('--output-root',type=Path,required=True);args.add_argument('--evidence-root',type=Path,required=True);args.add_argument('--assets-root',type=Path,default=P/'archive_snapshot_assets');args.add_argument('--view-path',default='portal/archive');args.add_argument('--date');args.add_argument('--test-fixtures',action='store_true');args=args.parse_args()
if args.date and not re.fullmatch(r'[0-9]{6}',args.date):raise ValueError('Invalid target date')
EVIDENCE=args.evidence_root.resolve();EVIDENCE.mkdir(parents=True,exist_ok=True);SOURCE_ASSETS=args.assets_root.resolve()
REPO=args.repo_root.resolve();OUT=args.output_root.resolve()
assert OUT!=REPO and not OUT.is_relative_to(REPO),'Build in a separate staging root'
OUT.mkdir(parents=True,exist_ok=True)
VIEW=args.view_path.strip('/');assert VIEW in ('portal/archive','portal/archive/completed');WEB='/ippatsu-share-pages/'+VIEW+'/';SOURCE_WEB='/ippatsu-share-pages/portal/archive/';PUBLIC=OUT/VIEW;ASSETS=PUBLIC/'archive-v2-r1';ASSETS.mkdir(parents=True,exist_ok=True)
def design_key(raw):
 text=re.sub(r'\s+','',unicodedata.normalize('NFKC',raw or '')).upper()
 match=re.fullmatch(r'B?([0-9]{4})',text)
 return match[1] if match else None
def text(s):return unescape(re.sub('<[^>]+>','',s)).strip()
def articles(s):return re.findall(r'<article\b[^>]*class="[^"]*\bledger-view\b[^"]*"[^>]*>.*?</article>',s,re.S)
def tables(s):return re.findall(r'<table\b.*?</table>',s,re.S)
manifest=json.loads((REPO/'portal/archive_manifest.json').read_text('utf-8'));days=[];cases=[];proof=[];ledger_styles=[];unverified_dates=[]
prior_catalog=REPO/'portal/archive/archive-v2-r1/catalog.json'
prior=json.loads(prior_catalog.read_text('utf-8')) if prior_catalog.exists() else {'cases':[]}
for entry in manifest['entries']:
 day=entry['date'];assert isinstance(day,str) and re.fullmatch(r'[0-9]{6}',day),'Invalid manifest date';index=REPO/'portal/archive'/day/'index.html'
 count=entry.get('completed_count')
 if type(count) is not int or count<0:unverified_dates.append(day);continue
 days.append({'date':day,'completed':count,'legacy_href':SOURCE_WEB+day+'/','available':False})
 if not count or not index.exists():continue
 body=index.read_text('utf-8');section=re.search(r'<section id="final-ledger-forms">.*?</section>',body,re.S)
 if section:
  hrefs=re.findall(r'href="([^"]+)"',section[0]);pair={Path(urlsplit(h).path).name:h for h in hrefs}
 else:
  # A redesigned alias is not the immutable source. Reuse the prior explicit
  # pair references, never a newest-directory guess or a DB lookup.
  old=[x for x in prior.get('cases',[]) if x['date']==day]
  references={(x.get('daily_source_href'),x.get('instructions_href','').split('#')[0]) for x in old}
  if not references:continue
  assert len(references)==1,'Ambiguous prior saved pair'
  daily_href,instruction_href=references.pop();assert daily_href and instruction_href
  pair={}
  for name,href in [('daily.html',daily_href),('instructions.html',instruction_href)]:
   assert re.fullmatch(r'/portal/archive/'+day+r'/saved-forms/final-ledger-[0-9a-f]{20}(?:-repair-[0-9a-f]{12})?/'+name,href)
   pair[name]=(REPO/href.lstrip('/')).relative_to(index.parent).as_posix()
 if set(pair)!={'daily.html','instructions.html'}:raise ValueError('Ambiguous saved pair')
 files={name:(index.parent/href).resolve() for name,href in pair.items()}
 assert all(f.is_relative_to(index.parent.resolve()) and f.is_file() for f in files.values())
 saved={name:f.read_text('utf-8') for name,f in files.items()}
 for css in re.findall(r'<style[^>]*>(.*?)</style>',saved['daily.html'],re.S):
  if ('.ledger-view' in css or '.compact-summary' in css) and css not in ledger_styles:ledger_styles.append(css)
 dailies=articles(saved['daily.html']);instructions=articles(saved['instructions.html'])
 bynumber=lambda xs:{re.search(r'data-management-no="(\d{8})"',s)[1]:s for s in xs}
 daily_by=bynumber(dailies);instruction_by=bynumber(instructions)
 assert len(daily_by)==len(instruction_by)==count and daily_by.keys()==instruction_by.keys()
 for number,original in daily_by.items():
  instruction=instruction_by[number]
  dm=re.search(r'<p class="design-number"[^>]*>.*?<span>(.*?)</span>.*?</p>',instruction,re.S)
  raw=unescape(re.sub('<[^>]+>','',dm[1])) if dm else ''
  identity=re.search(r'<p data-final-ledger-identity="'+number+r'">(.*?)</p>',original,re.S)
  assert identity
  match=re.search(r'受付回\s*(\d+)\s*/\s*台帳保存版\s*(\d+)',text(identity[1]));assert match
  episode,revision=match.groups();anchor='span-'+day+'-'+number+'-e'+episode+'-r'+revision
  label=text(re.search(r'<h2>(.*?)</h2>',original,re.S)[1])
  instruction_url=urljoin('/portal/archive/'+day+'/',pair['instructions.html'])+'#case-'+number
  assert ('id="case-'+number+'"') in instruction
  # The immutable table markup is copied verbatim. Photo-number-only sections
  # are not the archive's main view; the source saved documents remain intact.
  photo=re.search(r'<h3>写真番号と本数</h3>',original)
  content=(original[:photo.start()]+'</article>') if photo else original
  content=re.sub(r'\bid="case-'+number+r'"','id="'+anchor+'"',content,count=1)
  if 'id="'+anchor+'"' not in content:content=content.replace('<article ','<article id="'+anchor+'" ',1)
  base=urljoin('/portal/archive/'+day+'/',pair['daily.html'])
  content=re.sub(r'href="([^"]+)"',lambda m:'href="'+'/ippatsu-share-pages'+urljoin(base,unescape(m[1]))+'"',content)
  assert not re.search(r'<(?:script|img|iframe|link)\b|\bon\w+\s*=',content,re.I)
  assert tables(content)==tables(original),number
  instruction_content=re.sub(r'\bid="case-'+number+r'"','id="'+anchor+'"',instruction,count=1)
  assert tables(instruction_content)==tables(instruction)
  assert not re.search(r'<(?:script|img|iframe|link)\b|\bon\w+\s*=',instruction_content,re.I)
  cases.append({'date':day,'management_no':number,'label':label,'episode':episode,'revision':revision,'anchor':anchor,'completion_status':'completed','design_original':raw,'design_key':design_key(raw),'clearance_html':content,'instructions_html':instruction_content,'instructions_href':'/ippatsu-share-pages'+instruction_url,'daily_source_href':'/ippatsu-share-pages'+base,'reference_href':SOURCE_WEB+day+'/'})
  proof.append({'date':day,'management_no':number,'daily_source':str(files['daily.html'].relative_to(REPO)),'instructions_source':str(files['instructions.html'].relative_to(REPO)),'daily_sha256':hashlib.sha256(files['daily.html'].read_bytes()).hexdigest(),'instructions_sha256':hashlib.sha256(files['instructions.html'].read_bytes()).hexdigest(),'table_sha256':hashlib.sha256(''.join(tables(content)).encode()).hexdigest()})
 days[-1]['available']=True
 # Unchanged fixtures for local browser link verification, not publication targets.
 if args.test_fixtures:
  for f in files.values():
   dest=OUT/f.relative_to(REPO);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
catalog={'schema':'public-archive-snapshots/v1','days':sorted(days,key=lambda x:x['date'],reverse=True),'cases':cases,'unverified_dates':unverified_dates}
(ASSETS/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')),'utf-8')
for name in ['app.js','style.css']:
 value=(SOURCE_ASSETS/name).read_text('utf-8')
 if name=='app.js':value=value.replace('/portal/archive/',WEB).replace('https://pakchee0529.github.io/ippatsu-share-pages','https://pakchee0529.github.io').replace('https://pakchee0529.github.io/portal/','https://pakchee0529.github.io/ippatsu-share-pages/portal/')
 (ASSETS/name).write_text(value,'utf-8')
(ASSETS/'ledger.css').write_text('\n'.join(ledger_styles),'utf-8')
def shell(initial=''):
 css='<link rel="stylesheet" href="'+WEB+'archive-v2-r1/ledger.css"><link rel="stylesheet" href="'+WEB+'archive-v2-r1/style.css">'
 script='<script src="'+WEB+'archive-v2-r1/app.js" defer></script>'
 if initial:
  css='<style>'+ '\n'.join(ledger_styles)+(SOURCE_ASSETS/'style.css').read_text('utf-8')+'</style>'
  subset={**catalog,'days':[x for x in days if x['date']==initial],'cases':[x for x in cases if x['date']==initial],'scope':'saved-day'}
  encoded=json.dumps(subset,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
  script='<script type="application/json" id="archive-snapshot-data">'+encoded+'</script><script>'+(ASSETS/'app.js').read_text('utf-8')+'</script>'
 return '<!doctype html><html lang="ja" data-archive-snapshots="v1"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>完了アーカイブ</title>'+css+'<body data-catalog-version=\"'+hashlib.sha256((ASSETS/'catalog.json').read_bytes()).hexdigest()[:20]+'\" data-initial-date="'+initial+'"><header><a href="/ippatsu-share-pages/portal/">共有ポータル</a><h1>完了アーカイブ</h1><p>保存済みの離隔表・指示書</p></header><main><p id="scope-notice" role="status"></p><form id="filters"><label>設計番号<input id="design" type="search" inputmode="text" placeholder="例：6326" autocomplete="off"></label><button type="submit">設計番号で表示</button><label>作業日<input id="day" type="date"></label><button type="button" id="date-open">日付で表示</button><button type="button" id="reset">日付一覧</button><button type="button" id="unregistered">設計番号未登録</button></form><p id="message" role="status" aria-live="polite"></p><section id="results"></section><button id="older" type="button" hidden>以前の日付を10件表示</button></main>'+script+'</body></html>'
(PUBLIC/'index.html').write_text(shell(),'utf-8')
allow=[VIEW+'/index.html']+[VIEW+'/archive-v2-r1/'+x for x in ['app.js','style.css','ledger.css','catalog.json']]
for day in [d for d in days if d['available'] and (not args.date or d['date']==args.date)]:
 target=PUBLIC/day['date']/'view.html';target.parent.mkdir(exist_ok=True);target.write_text(shell(day['date']),'utf-8');allow.append(str(target.relative_to(OUT)).replace('\\','/'))
assert len({x['anchor'] for x in cases})==len(cases)
assert design_key(' Ｂ ０６３４ ')=='0634' and design_key('０６３４')=='0634' and design_key('634') is None and design_key('BB0634') is None
(EVIDENCE/'SOURCE-PROOF.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),'utf-8')
if args.test_fixtures:
 # Existing-page fixtures support local link acceptance; they are not new outputs.
 for entry in manifest['entries']:
  source=REPO/'portal/archive'/entry['date']/'index.html';target=OUT/source.relative_to(REPO)
  if source.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 source=REPO/'portal/index.html';target=OUT/'portal/index.html'
 if source.exists():shutil.copyfile(source,target)
 shutil.copyfile(REPO/'portal/archive_manifest.json',OUT/'portal/archive_manifest.json')
(EVIDENCE/'scope.json').write_text(json.dumps({'adopted':False,'files':{rel:hashlib.sha256((OUT/rel).read_bytes()).hexdigest() for rel in allow},'unchanged_fixture_files':'Saved forms copied for browser tests only; exclude from publication diff','source':'Existing public HTML only; no DB fields','completed_cards':len([d for d in days if d['completed']>0]),'indexed_cases':len(cases)},ensure_ascii=False,indent=2),'utf-8')
print('Archive snapshot generation: OK')
print(json.dumps({'candidate_only':True,'proposed_files':len(allow),'indexed_cases':len(cases),'designs':sorted({c['design_key'] for c in cases if c['design_key']}),'legacy_without_saved_forms':len([d for d in days if d['completed'] and not d['available']])},ensure_ascii=False))
