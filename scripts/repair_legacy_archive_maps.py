"""Candidate-only legacy DOM adapter. No business renderer, DB, exports or publication."""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import ast, argparse, hashlib, json, os, re, stat, tempfile, types
from pathlib import Path
from dataclasses import replace, asdict
from html import escape, unescape
MODERN_SHA='9e95a7674e201488ca35263a7111d0535d3e50b1e59779226373991f28b50d7a'
RUNTIME_SHA='b49cbfd1df0faf35b9874b7fed0d634cf45daeeea605f89be42f350aafab2027'
def span_key(label):return re.sub(r'\s+','',label)
ROLES=('single_url','start','end','representative')
DATES=set('260529 260615 260616 260617 260618 260619 260622 260623 260624 260625 260629 260630 260701 260703 260709 260714 260716 260721 260722'.split())
def require(ok,msg):
 if not ok: raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def no_reparse(path):
 for p in (Path(os.path.abspath(path)),*Path(os.path.abspath(path)).parents):
  try:s=os.lstat(p)
  except FileNotFoundError:continue
  require(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'Reparse path forbidden')
_MODERN=None
def dependencies(modern,scripts,locks):
 global _MODERN
 no_reparse(modern); verified=modern.read_bytes();require(sha(verified)==MODERN_SHA,'Modern helper hash mismatch')
 if _MODERN is None:
  require('_pinned_legacy_map_base' not in sys.modules,'Untracked modern import')
  m=types.ModuleType('_pinned_legacy_map_base');m.__file__=str(modern.resolve());m.__verified_source_bytes__=verified;sys.modules[m.__name__]=m;exec(compile(verified,str(modern),'exec'),m.__dict__);_MODERN=(modern.resolve(),m)
 else:
  path,m=_MODERN;require(path==modern.resolve() and sys.modules.get('_pinned_legacy_map_base') is m,'Modern import provenance changed')
 require(Path(m.__file__).resolve()==modern.resolve() and m.__verified_source_bytes__==verified,'Modern metadata/verified bytes changed')
 p,c=m.load_dependencies(scripts,locks);return m,p,c

def json_unique(text):
 def pairs(xs):
  d={}
  for k,v in xs:require(k not in d,'Duplicate JSON key');d[k]=v
  return d
 return json.loads(text,object_pairs_hook=pairs)

def map_node(tag,attrs):
 classes=set(attrs.get('class','').split())
 return bool(classes & {'btn-map','btn-map-single','btn-map-two','two-map-wrap','share-two-map-canvas'} or any(k in attrs for k in ('data-two-open','data-two-wrap','data-two-map','data-two-json')) or re.fullmatch(r'(?:planned-)?two-geo-\d+',attrs.get('id','')))

def visible_ancestors(node,allow_hidden=None):
 while node is not None:
  require(not any(k in node.attrs for k in ('style','inert','aria-hidden')),'Unknown visibility attributes')
  require('hidden' not in node.attrs or node is allow_hidden,'Unexpected hidden map ancestor')
  node=node.parent

def exact_control(node,kind,dom):
 if node is None:return
 cls=set(node.attrs.get('class','').split());a=node.attrs
 visible_ancestors(node)
 if node.tag=='a':
  require(kind=='single' and cls in ({'btn','btn-map'},{'btn','btn-map','btn-map-single'}),'Unknown single control classes')
  require(set(a)=={'class','href','target','rel'} and a['target']=='_blank' and a['rel']=='noopener noreferrer','Unknown single attributes')
  require(re.sub('<[^>]*>','',dom.content(node)) in {'地図を開く','現場地図を開く'},'Unknown single caption')
 elif 'disabled' in a:
  allowed=[{'btn','btn-map','btn-map-disabled','btn-map-'+kind}]
  if kind=='two':allowed.append({'btn','btn-map','btn-map-disabled'})
  require(node.tag=='button' and cls in allowed and set(a)=={'type','class','disabled','aria-disabled','title'} and a['type']=='button' and a['disabled'] is None and a['aria-disabled']=='true','Unknown disabled map attributes')
  titles={'若番・老番の座標がありません'} if kind=='single' else {'若番・老番の両方の座標が必要です','2点のうち片側だけ座標があります'}
  require(a['title'] in titles,'Unknown disabled map reason')
 else:
  require(kind=='two' and node.tag=='button' and cls in ({'btn','btn-map'},{'btn','btn-map','btn-map-two'}),'Unknown enabled two classes')
  require(set(a)=={'type','class','data-two-open','data-two-wrap','data-two-map','data-two-json','aria-expanded','aria-controls'} and a['type']=='button' and a['data-two-open'] is None and a['aria-expanded']=='false','Unknown enabled two attributes')
 if kind=='two':require(re.sub('<[^>]*>','',dom.content(node))=='2点地図を開く','Unknown two caption')
 require(not any(n.parent is node for n in dom.nodes),'Nested map control content')

def exact_payload(script,panel,canvas,dom):
 require(script.tag=='script' and set(script.attrs)=={'type','id'} and script.attrs['type']=='application/json' and re.fullmatch(r'(?:planned-)?two-geo-\d+',script.attrs['id']),'Unknown payload node')
 require(panel.tag=='div' and set(panel.attrs)=={'class','id','hidden'} and panel.attrs['class']=='two-map-wrap' and panel.attrs['hidden'] is None and re.fullmatch(r'(?:planned-)?two-wrap-\d+',panel.attrs['id']),'Unknown panel node')
 require(canvas.tag=='div' and set(canvas.attrs)=={'id','class','role','aria-label'} and canvas.attrs['class']=='share-two-map-canvas' and canvas.attrs['role']=='application' and canvas.attrs['aria-label']=='2点地図' and re.fullmatch(r'(?:share-two-map|planned-two-map)-\d+',canvas.attrs['id']),'Unknown canvas node')
 require([n for n in dom.nodes if dom.inside(n,panel)]==[canvas] and not re.sub('<[^>]*>','',dom.content(panel)).strip(),'Unknown panel content')
 visible_ancestors(script);visible_ancestors(canvas,allow_hidden=panel)

_OVERALL_CACHE=None
def exact_overall(section,dom):
 global _OVERALL_CACHE
 portal=sys.modules.get('generate_portal');require(portal is not None and hasattr(portal,'__verified_source_bytes__'),'Missing verified renderer source')
 verified=portal.__verified_source_bytes__
 if _OVERALL_CACHE is None:
  tree=ast.parse(verified.decode('utf-8-sig'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_archive_detail_html')
  blocks=tuple(n.value.strip() for n in ast.walk(fn) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.lstrip().startswith('<section class="map-section'))
  require(len(blocks)==2,'Unknown renderer overall templates');_OVERALL_CACHE=(portal,verified,blocks)
 else:
  known_portal,known_bytes,blocks=_OVERALL_CACHE;require(portal is known_portal and verified==known_bytes,'Overall template provenance changed')
 require(dom.content(section).strip() in blocks,'Unknown overall map DOM');visible_ancestors(section)

def parse(text,date,m,c,source=False):
 require(date in DATES,'Unsupported legacy date')
 require('data-final-ledger-identity=' not in text,'Fixed-form alias forbidden')
 original_map_nodes=sum(map_node(t,a) for t,a in c.Tags(text).tags)
 title=m.one(re.findall(r'<title>(.*?)</title>',text,re.S),'date title')
 if source:
  q=re.fullmatch(r'(\d{4})年(\d{1,2})月(\d{1,2})日',title)
  require(q and tuple(map(int,q.groups()))==(2000+int(date[:2]),int(date[2:4]),int(date[4:])), 'Source date mismatch')
 else:require(title==date+' · アーカイブ詳細','Current date mismatch')
 if source:
  # Source business chrome is not a map input. Parse complete card fragments strictly,
  # plus the sole points assignment. No repair or normalization of source business HTML.
  fragments=c.CARD.findall(text)
  require(len(fragments)==len(re.findall(r'<article\b',text)), 'Unrecognized source article')
  ids=[a['id'] for _,a in c.Tags(text).tags if 'id' in a];require(len(ids)==len(set(ids)),'Duplicate source DOM id')
  pm=m.one(list(re.finditer(r'\bvar\s+(?:points|POINTS)\s*=\s*',text)),'source points')
  raw,used=json.JSONDecoder().raw_decode(text[pm.end():]);point_text=text[pm.start():pm.end()+used]
  text=''.join(fragments)+'<script>'+point_text+';</script>'
 dom=m.DOM(text);cards=[n for n in dom.nodes if n.tag=='article' and n.cls('card')]
 require(cards and len(cards)==len(c.CARD.findall(text)),'Unknown cards')
 views={};slots={};ui_anomalies=[];declared_map_nodes=[]
 for card in cards:
  block=dom.content(card);key=c.identity(c.text_class(block,'item-mgmt'));label=c.text_class(block,'card-title')
  require(key not in views,'Duplicate identity '+key)
  for attr in ('data-management-no','data-management-no-key'):
   if attr in card.attrs:require(c.identity(card.attrs[attr])==key,'Card identity mismatch')
  require(card.attrs.get('data-date',date)==date,'Card date mismatch')
  ns=[n for n in dom.nodes if dom.inside(n,card)];actions=m.one([n for n in ns if n.cls('card-actions')],'card actions')
  controls=[n for n in ns if n.cls('btn-map')];single=[];two=[]
  for n in controls:
   cls=set(n.attrs.get('class','').split());require(cls<={'btn','btn-map','btn-map-single','btn-map-two','btn-map-disabled'},'Unknown map class')
   require(n.parent is actions,'Map control outside actions')
   if 'data-two-open' in n.attrs or n.cls('btn-map-two') or (n.tag=='button' and n.cls('btn-map-disabled') and 'disabled' in n.attrs and re.sub('<[^>]*>','',dom.content(n))=='2点地図を開く'):two.append(n)
   elif n.tag=='a' or n.cls('btn-map-single'):single.append(n)
   else:raise ValueError('Unknown map control '+key+' source='+str(source))
  require(len(single)<=1 and len(two)<=1,'Duplicate/missing map controls '+key+' source='+str(source))
  single=single[0] if single else None;two=two[0] if two else None;url=''
  exact_control(single,'single',dom);exact_control(two,'two',dom)
  declared_map_nodes.extend(n for n in (single,two) if n is not None)
  if single:
   if single.tag=='a':
    require('disabled' not in single.attrs and not single.cls('btn-map-disabled') and single.attrs.get('aria-disabled')!='true','Disabled single link');url=single.attrs.get('href','');m.checked_url(url,c)
   else:require(single.tag=='button' and 'disabled' in single.attrs and single.cls('btn-map-disabled'),'Unknown disabled single')
  notes=[n for n in ns if n.cls('note-panel')];require(len(notes)==1 or not notes and not source and date=='260529','Unknown note layout '+key);note=notes[0] if notes else None;scripts=[n for n in ns if n.tag=='script'];panels=[n for n in ns if n.cls('two-map-wrap')]
  require(len(scripts)==len(panels)<=1,'Unknown map payload layout');a=b=None
  if two and 'data-two-open' in two.attrs:
   require(two.tag=='button' and 'disabled' not in two.attrs and not two.cls('btn-map-disabled') and two.attrs.get('aria-disabled')!='true','Invalid two control')
   script=m.one(scripts,'two payload');panel=m.one(panels,'two panel')
   require(script.attrs.get('id')==two.attrs.get('data-two-json') and script.attrs.get('type')=='application/json','Wrong payload binding')
   binding=panel.attrs.get('id')==two.attrs.get('data-two-wrap')==two.attrs.get('aria-controls')
   if not binding:
    # One fixed historical source renderer used an index offset after its disabled card.
    # Read the own-card payload as evidence; do not claim that its original UI worked.
    i=card.attrs.get('data-card-index','');require(source and date=='260722' and i.isdigit() and int(i)>0,'Wrong panel binding')
    i=int(i);require(script.attrs.get('id')==f'two-geo-{i}' and panel.attrs.get('id')==f'two-wrap-{i}' and two.attrs.get('data-two-wrap')==two.attrs.get('aria-controls')==f'two-wrap-{i-1}' and two.attrs.get('data-two-map')==f'share-two-map-{i-1}','Unknown source misbinding')
    canvas=m.one([n for n in ns if n.attrs.get('id')==f'share-two-map-{i}'],'own source canvas')
    ui_anomalies.append(dict(key=key,type='known-260722-off-by-one-ui-binding',payload_id=script.attrs['id'],own_panel=panel.attrs['id'],incorrect_control_panel=two.attrs['data-two-wrap']))
   else:canvas=m.one([n for n in ns if n.attrs.get('id')==two.attrs.get('data-two-map')],'two canvas')
   require(canvas.parent is panel and canvas.cls('share-two-map-canvas'),'Wrong canvas binding')
   exact_payload(script,panel,canvas,dom);declared_map_nodes.extend([script,panel,canvas])
   raw=json_unique(text[script.head_end:text.rfind('</script',script.start,script.end)])
   require(isinstance(raw,dict) and set(raw)<={'a','b','nearby'},'Unknown payload schema')
   if 'nearby' in raw:
    require(isinstance(raw['nearby'],list),'Unknown nearby schema')
    for near in raw['nearby']:
     require(isinstance(near,dict) and set(near)=={'name','lat','lng','distance_m'} and isinstance(near['name'],str) and near['name'] and type(near['lat']) in (int,float) and type(near['lng']) in (int,float) and c.point(near['name'],near['lat'],near['lng']) is not None and type(near['distance_m']) in (int,float) and __import__('math').isfinite(near['distance_m']) and near['distance_m']>=0,'Invalid nearby point')
   endpoints=[]
   for role in ('a','b'):
    q=raw.get(role);require(isinstance(q,dict) and set(q)=={'name','lat','lng'},'Unknown endpoint schema')
    require(type(q['lat']) in (int,float) and type(q['lng']) in (int,float),'Non-numeric map coordinate');pt=c.point(q['name'],q['lat'],q['lng']);require(pt or not source and q['lat']==q['lng']==0,'Invalid endpoint coordinate')
    require(isinstance(q['name'],str) and q['name'],'Missing endpoint name');require(pt is not None or q['name']==label,'Unknown zero endpoint sentinel name');endpoints.append(pt)
   a,b=endpoints;require(not a or not b or not c.same(a,b),'Non-distinct endpoints')
  else:require((two is None or two.tag=='button' and 'disabled' in two.attrs and two.cls('btn-map-disabled')) and not scripts and not panels,'Invalid disabled two')
  require(note is not None or not source and date=='260529','Unrecognized card-tail payload')
  require(all(n.end<=(note.start if note else card.end-len('</article>')) for n in scripts+panels),'Payload placement mismatch')
  views[key]=c.MapView(label,a,b,url);slots[key]=(card,single,two,note,scripts,panels,actions)
 require(set(n for n in dom.nodes if map_node(n.tag,n.attrs))==set(declared_map_nodes) and original_map_nodes==len(declared_map_nodes),'Unaccounted map/handler nodes')
 labels=[v.label for v in views.values()];require(len({span_key(x) for x in labels})==len(labels),'Normalized span collision')
 matches=list(re.finditer(r'\bvar\s+(?:points|POINTS)\s*=\s*',text));pm=m.one(matches,'overall points')
 raw,used=json.JSONDecoder().raw_decode(text[pm.end():]);pr=(pm.end(),pm.end()+used);raw=json_unique(text[pr[0]:pr[1]])
 require(isinstance(raw,list),'Points not array');seen=set();point_rows={}
 for q in raw:
  require(isinstance(q,dict) and set(q)<={'name','lat','lng','management_no'} and {'name','lat','lng'}<=set(q),'Unknown point schema')
  if 'management_no' in q:key=c.identity(q['management_no'])
  else:
   require(source,'Missing current point identity');key=m.one([k for k,v in views.items() if span_key(v.label)==span_key(q['name'])],'unique exact source point span')
  require(key in views and key not in seen and span_key(q['name'])==span_key(views[key].label),'Point identity/full span mismatch');seen.add(key)
  require(type(q['lat']) in (int,float) and type(q['lng']) in (int,float),'Non-numeric map coordinate');pt=c.point(q['name'],q['lat'],q['lng']);require(pt or not source and q['lat']==q['lng']==0,'Invalid point coordinate')
  views[key]=replace(views[key],representative=pt);point_rows[key]=q
 section=m.one([n for n in dom.nodes if n.tag=='section' and n.cls('map-section')],'map section') if not source else None
 if not source:
  exact_overall(section,dom)
  runtime=m.one([s for s in re.findall(r'<script\b[^>]*>.*?</script>',text,re.S) if 'var twoMaps' in s],'map runtime');ra,rb=m.point_range(runtime)
  require(sha((runtime[:ra]+runtime[rb:]).encode())==RUNTIME_SHA,'Unknown map runtime')
  require(len([n for n in dom.nodes if n.attrs.get('id')=='share-map'])==1,'Missing overall container')
 return dict(text=text,dom=dom,views=views,slots=slots,points=point_rows,pr=pr,section=section,source_ui_anomalies=ui_anomalies)

def business(page,m):
 edits=[(*page['pr'],'')]
 if page['section']:edits.append((page['section'].start,page['section'].end,''))
 for card,single,two,note,scripts,panels,actions in page['slots'].values():
  for n in ([single] if single else [])+([two] if two else [])+scripts+panels:edits.append((n.start,n.end,''))
 return m.edits_apply(page['text'],edits).encode()

def strict_projection(page,date,m,p,c):
 # Validation-only adaptation. Never written, never passed to a business renderer.
 edits=[]
 for key,(card,single,two,note,scripts,panels,actions) in page['slots'].items():
  v=page['views'][key]
  s=p._archive_single_map_button(v)
  edits.append((single.start,single.end,s) if single else (actions.head_end,actions.head_end,s))
  if v.start and v.end:
   head=page['text'][two.start:two.head_end];head=re.sub(r'class="([^"]*)"',lambda q:'class="'+q[1]+' btn-map-two"' if 'btn-map-two' not in q[1].split() else q[0],head)
   edits.append((two.start,two.head_end,head))
  else:
   disabled='<button class="btn btn-map btn-map-two btn-map-disabled" disabled></button>'
   edits.append((two.start,two.end,disabled) if two else (actions.head_end,actions.head_end,disabled))
   for n in scripts+panels:edits.append((n.start,n.end,''))
 points=[dict(name=v.label,lat=v.representative[1],lng=v.representative[2],management_no=k) for k,v in page['views'].items() if v.representative]
 edits.append((*page['pr'],p.json_for_script_tag(points)))
 result=m.edits_apply(page['text'],edits);c.verify_rendered(result,date,page['views']);return result

def semantic_classes(text,date,m,c):
 page=parse(text,date,m,c);edits=[];receipt=[]
 for key,slot in page['slots'].items():
  for role,node in [('single',slot[1]),('two',slot[2])]:
   target='btn-map-'+role
   if node is not None and not node.cls(target):
    head=text[node.start:node.head_end];match=m.one(list(re.finditer(r'class="([^"]*)"',head)),'map class attribute')
    replacement=head[:match.end(1)]+' '+target+head[match.end(1):]
    edits.append((node.start,node.head_end,replacement));receipt.append(dict(key=key,role=role,before_class=node.attrs['class'],after_class=node.attrs['class']+' '+target,exception='Append only the semantic map-role class; preserve every other byte'))
 result=m.edits_apply(text,edits);require(parse(result,date,m,c)['views']==page['views'],'Semantic class changed MapView')
 return result,receipt

def repair(current,source,date,gps,m,p,c,row):
 require(date!='260722','Paused: source-less overall zero sentinel needs separate reviewed specification')
 old=parse(current.decode(),date,m,c);src=parse(source.decode(),date,m,c,True);actual=old['views'];sv=src['views']
 extras={k:dict(label=v.label,reason='Not present in the pinned current archive; excluded from map-only repair') for k,v in sv.items() if k not in actual}
 require(row['source_exclusions']==extras,'Source exclusions mismatch')
 require(row['source_reader']=='strict-card-map-payload-v2','Unknown source reader')
 require(row['source_ui_anomalies']==src['source_ui_anomalies'],'Source UI anomaly scope mismatch')
 differences={k:dict(current_url=v.single_url,source_url=sv[k].single_url) for k,v in actual.items() if k in sv and v.single_url and sv[k].single_url and not c.same_url(v.single_url,sv[k].single_url)}
 require(row['retained_url_differences']==differences,'URL policy scope mismatch')
 require(set(actual)<=set(sv),'Missing original card identity')
 require(row['full_span_join']=={k:dict(date=date,label=v.label,source_label=sv[k].label) for k,v in actual.items()},'Full span join mismatch')
 expected={};computed={};unavailable={}
 for key,v in actual.items():
  w=sv[key];require(span_key(v.label)==span_key(w.label),'Non-whitespace source span mismatch: '+key)
  roles=[role for role in ROLES if not getattr(v,role) and getattr(w,role)];computed[key]=roles
  unavailable[key]=[role for role in ROLES if not getattr(v,role) and not getattr(w,role)]
  expected[key]=replace(v,**{role:((v.label,*w.representative[1:]) if role=='representative' else getattr(w,role)) for role in roles})
  if not any(getattr(w,r) or getattr(v,r) for r in ROLES):continue
  parts=p._share_split_span_label(w.label);require(parts,'Unsupported span '+key)
  names=(parts[0],p._share_complete_span_end_label(parts[0],parts[1],gps));ends=[]
  for role,name in zip(('start','end'),names):
   pole=p._share_resolve_gps_pole_label(name,gps);require(pole,'Missing GPS '+key+' '+name);g=(pole,*gps[pole]);ends.append(g)
   for which,view in [('source',w),('current',v)]:
    pt=getattr(view,role)
    if pt:
     require(c.same(pt,g),'GPS/'+which+' conflict '+key+' '+role)
     allowed={c.norm(name),c.norm(parts[0] if role=='start' else parts[1])}
     if which=='current':allowed.add(c.norm(v.label))
     require(c.norm(pt[0]) in allowed,'Endpoint name conflict '+key+' '+role)
  midpoint=(w.label,(ends[0][1]+ends[1][1])/2,(ends[0][2]+ends[1][2])/2)
  for which,view in [('source',w),('current',v)]:
   for role,pt in [('single_url',c.url_point(view.single_url,v.label) if view.single_url else None),('representative',view.representative)]:
    if pt:require(any(c.same(pt,x) for x in [*ends,midpoint]),'GPS/'+which+' '+role+' conflict '+key)
  # Retain a GPS-validated current endpoint URL even when original evidence used its midpoint.
  # Both URLs were validated independently above; no existing URL is replaced.
 require(row['repair_roles']==computed,'Missing-role scope mismatch')
 require(row['unavailable_roles']==unavailable,'Unavailable source scope mismatch')
 require(any(computed.values()),'No evidenced lost roles')
 edits=[]
 for idx,(key,slot) in enumerate(old['slots'].items()):
  card,single,two,note,scripts,panels,actions=slot;v=expected[key];roles=computed[key]
  if 'single_url' in roles:
   html=p._archive_single_map_button(v);edits.append((single.start,single.end,html) if single else (actions.head_end,actions.head_end,html))
  endpoint_roles=set(roles)&{'start','end'}
  if endpoint_roles:
   require(v.start and v.end,'Partial evidence cannot enable two map')
   if scripts:
    script=scripts[0];raw=json_unique(old['text'][script.head_end:old['text'].rfind('</script',script.start,script.end)])
    # Preserve each retained endpoint object byte-for-byte. Change only missing object.
    txt=old['text'][script.head_end:old['text'].rfind('</script',script.start,script.end)];replacements=[]
    for role,letter in [('start','a'),('end','b')]:
     if role in endpoint_roles:
      match=m.one(list(re.finditer('"'+letter+'"\\s*:\\s*',txt)),'endpoint token');val,used=json.JSONDecoder().raw_decode(txt[match.end():]);pt=getattr(v,role);replacements.append((match.end(),match.end()+used,p.json_for_script_tag(dict(name=pt[0],lat=pt[1],lng=pt[2]))))
    edits.append((script.head_end,old['text'].rfind('</script',script.start,script.end),m.edits_apply(txt,replacements)))
   else:
    ident=f'two-geo-{idx}';payload=p.build_two_geo_payload(a_name=v.start[0],a_lat=v.start[1],a_lng=v.start[2],b_name=v.end[0],b_lat=v.end[1],b_lng=v.end[2],gps_poles=None)
    control=p._share_two_map_button(ident,idx);edits.append((two.start,two.end,control) if two else ((single.end if single else actions.head_end),(single.end if single else actions.head_end),control));anchor=note.start if note else card.end-len('</article>');edits.append((anchor,anchor,p.format_two_geo_script(ident,payload)+p._share_two_map_panel(idx)))
 # Keep existing overall point object bytes; only replace zero sentinel or append missing.
 a,b=old['pr'];raw=old['text'][a:b];pos=1;point_edits=[];existing=set()
 dec=json.JSONDecoder()
 while pos<len(raw)-1:
  while pos<len(raw) and raw[pos] in ' \r\n\t,':pos+=1
  if raw[pos]==']':break
  q,used=dec.raw_decode(raw[pos:]);key=c.identity(q['management_no']);existing.add(key)
  if 'representative' in computed[key]:
   pt=expected[key].representative;v=dict(q);v.update(lat=pt[1],lng=pt[2]);point_edits.append((pos,pos+used,p.json_for_script_tag(v)))
  pos+=used
 extra=[dict(name=v.label,lat=v.representative[1],lng=v.representative[2],management_no=k) for k,v in expected.items() if k not in existing and 'representative' in computed[k]]
 if extra:point_edits.append((len(raw)-1,len(raw)-1,(',' if existing else '')+','.join(p.json_for_script_tag(v) for v in extra)))
 if point_edits:edits.append((a,b,m.edits_apply(raw,point_edits)))
 result=m.edits_apply(old['text'],edits);result,class_receipt=semantic_classes(result,date,m,c);after=parse(result,date,m,c)
 require(after['views']==expected,'Repaired projection mismatch');require(c.parse_page(result,date)==expected,'Ordinary parse_page MapView mismatch');strict=strict_projection(after,date,m,p,c);c.verify_preserved(strict,date,[actual])
 require(business(old,m)==business(after,m),'NON-MAP BYTE CHANGE')
 for key,slot in old['slots'].items():
  for role in ROLES:
   if getattr(actual[key],role):require(getattr(after['views'][key],role)==getattr(actual[key],role),'Retained role changed')
 return result.encode(),dict(date=date,before_sha256=sha(current),after_sha256=sha(result.encode()),business_sha256=sha(business(old,m)),business_bytes_equal=True,map_roles=computed,unavailable_roles=unavailable,semantic_class_exceptions=class_receipt,ordinary_parse_page_equal=True,ordinary_prepare_archive_maps='Not claimed compatible: unchanged representative/GPS-end conflict fails closed',source_exclusions=extras,source_ui_anomalies=src['source_ui_anomalies'],retained_url_differences=differences,whitespace_equivalence={k:dict(current_label=v.label,source_label=sv[k].label) for k,v in actual.items() if v.label!=sv[k].label},expected={k:asdict(v) for k,v in expected.items()},retained={k:asdict(v) for k,v in actual.items()})

def run(manifest,repo,scripts,gps_path,modern,out):
 for path in (repo,scripts,gps_path,modern,out):no_reparse(path)
 require(manifest['schema']=='legacy-map-only-v4','Unknown manifest');require(not out.exists(),'Output must be new')
 require(all(not out.resolve().is_relative_to(x.resolve()) for x in (repo,scripts,gps_path.parent)),'Output inside source')
 m,p,c=dependencies(modern,scripts,manifest['helpers']);gps=m.load_gps(gps_path,manifest['gps_sha256'],p);prepared=[];seen=set()
 for row in manifest['pages']:
  date=row['date'];require(date in DATES and date not in seen,'Duplicate/unsupported date');seen.add(date)
  current=m.proof_bytes(repo,row['current'],date,'current');source=m.proof_bytes(repo,row['source'],date,'source');work=(repo/row['current']['path']).read_bytes()
  require(sha(work)==row['working_sha256'],'Working bytes changed');require(work.replace(b'\r\n',b'\n')==current.replace(b'\r\n',b'\n'),'Working/pinned mismatch')
  data,report=repair(current,source,date,gps,m,p,c,row);report['proof']=row;prepared.append((date,data,report))
 require(prepared,'Empty batch');out.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.legacy-stage-',dir=out.parent))
 for date,data,_ in prepared:
  dest=stage/'portal/archive'/date/'index.html';dest.parent.mkdir(parents=True);dest.write_bytes(data)
 (stage/'PRIVATE-REPORT.json').write_text(json.dumps([r for _,_,r in prepared],ensure_ascii=False,indent=2),encoding='utf-8');os.rename(stage,out)
 return [r for _,_,r in prepared]

if __name__=='__main__':
 ap=argparse.ArgumentParser()
 for key in ['manifest','repo','scripts','gps','modern','output']:ap.add_argument('--'+key,type=Path,required=True)
 a=ap.parse_args();no_reparse(a.manifest);print(json.dumps(run(json_unique(a.manifest.read_text(encoding='utf-8')),a.repo,a.scripts,a.gps,a.modern,a.output),ensure_ascii=True,indent=2))
