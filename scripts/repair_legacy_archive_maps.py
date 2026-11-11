"""Candidate-only legacy DOM adapter. No business renderer, DB, exports or publication."""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
from decimal import Decimal
from urllib.parse import urlsplit, parse_qs
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

EXCEPTION_LOCKS={'260709': {'current': 'b7d4c17604350152e2a3d3bd26435a18263f492f92bd048fd7a4c4ae4674eebf', 'source': '3e77f4e35dde10253d4acab3a7ab385bef8475f6d92675f5269cd3ccc90e80fd'}, '260722': {'current': 'da32dfa3e7c5b4afc6c957c479f2f26111cdd44272e29fa8b1cb7f8d901523c6', 'source': '133e0827fe778e5227a7af0ab66bb87dec93ce78a96c7d3bee7d02fee2248232'}}
def known_source_projection(current,source,date,gps,m,p,c):
 receipt=[]
 if date not in EXCEPTION_LOCKS:return source,receipt
 require(sha(current)==EXCEPTION_LOCKS[date]['current'] and sha(source)==EXCEPTION_LOCKS[date]['source'],'Exceptional evidence byte lock mismatch')
 old=parse(current.decode(),date,m,c)
 if date=='260722':
  key='51407415';view=old['views'][key];slot=old['slots'][key]
  require(view.label=='二津野4～果無8N20' and not any(getattr(view,r) for r in ROLES) and all('disabled' in n.attrs for n in (slot[1],slot[2])) and not slot[4] and not slot[5],'Unknown source-less case state')
  original=parse(source.decode(),date,m,c,True);original_view=original['views'][key];original_slot=original['slots'][key]
  require(set(original['views'])==set(old['views']) and len(original['views'])==6 and original_view.label==view.label and not any(getattr(original_view,r) for r in ROLES) and key not in original['points'] and len(original['points'])==5 and all('disabled' in n.attrs for n in (original_slot[1],original_slot[2])) and not original_slot[4] and not original_slot[5],'Original source-less case changed')
  q=old['points'].get(key);require(q==dict(name=view.label,lat=0.0,lng=0.0,management_no=key),'Unknown zero representative sentinel')
  receipt.append(dict(type='remove-only-invalid-overall-zero-sentinel',key=key,label=view.label,single='disabled',two='disabled',coords_created=False,point=q))
  return source,receipt
 key='51513023';label='吉野平6S5W6～6S5W6N1';broken='???6S5W6?6S5W6N1';lat,lng=34.39576,135.78926;url='https://www.google.com/maps?q=34.39576,135.78926'
 require(set(old['views'])=={'51509108','51511204',key} and old['views'][key].label==label and old['views'][key].single_url==url and old['views'][key].start is None and old['views'][key].end is None,'Exceptional current identity/roles changed')
 t=source.decode();blocks=c.CARD.findall(t);require(len(blocks)==3,'Exceptional source card count changed');block=m.one([b for b in blocks if c.identity(c.text_class(b,'item-mgmt'))==key],'exception source card');require(c.text_class(block,'card-title')==label,'Exceptional source span changed')
 dom=m.DOM(block);anchors=[n for n in dom.nodes if n.tag=='a' and n.cls('btn-map')];require(len(anchors)==1 and anchors[0].attrs.get('href')==url,'Exceptional source single changed');require(not [n for n in dom.nodes if n.tag=='script'],'Unexpected source endpoints');twos=[n for n in dom.nodes if n.tag=='button' and n.cls('btn-map')];require(len(twos)==1 and 'disabled' in twos[0].attrs,'Exceptional source two control changed');exact_control(anchors[0],'single',dom);exact_control(twos[0],'two',dom)
 require(gps.get('吉野平6S5W6')==(lat,lng) and c.url_point(url,label)==(label,lat,lng),'Exceptional source/GPS/single mismatch')
 pm=m.one(list(re.finditer(r'\bvar\s+POINTS\s*=\s*',t)),'exception POINTS');points,used=json.JSONDecoder().raw_decode(t[pm.end():]);require(len(points)==3,'Exceptional source point count changed')
 q=m.one([q for q in points if c.identity(q.get('management_no',''))==key],'exception point identity')
 require(q==dict(name=broken,lat=lat,lng=lng,management_no='515 13023'),'Exceptional damaged point changed')
 raw=t[pm.end():pm.end()+used];token=json.dumps(broken);require(raw.count(token)==1,'Damaged label token not unique');projected=raw.replace(token,p.json_for_script_tag(label),1)
 receipt.append(dict(type='fixed-corrupt-point-name-identity-join',key=key,source_name=broken,current_label=label,point_coords=[lat,lng],single_url=url,gps_exact_pole='吉野平6S5W6',endpoints_created=False))
 return (t[:pm.end()]+projected+t[pm.end()+used:]).encode(),receipt

def remove_zero_sentinel(text,date,m,c):
 if date!='260722':return text
 page=parse(text,date,m,c);a,b=page['pr'];raw=text[a:b];pos=1
 while raw[pos].isspace():pos+=1
 q,used=json.JSONDecoder().raw_decode(raw[pos:]);require(q==dict(name='二津野4～果無8N20',lat=0.0,lng=0.0,management_no='51407415'),'Only the locked first zero sentinel may be removed')
 end=pos+used
 while raw[end].isspace():end+=1
 require(raw[end]==',' and len(page['points'])==6,'Sentinel array shape changed')
 return text[:a]+raw[:pos]+raw[end+1:]+text[b:]

PARTIAL_LOCK={'current': '265dd95deba23ec968d31af439c7ce03eda0a31e625b5c166d2ff40d3b39288d', 'source': '8288e603f8bdca556331e09e0db9b2329b3d1b143c0336e15b261842ee3d79a5'}
def partial_plan(current,source,date,gps,m,p,c):
 if date!='260630':return None
 require(sha(current)==PARTIAL_LOCK['current'] and sha(source)==PARTIAL_LOCK['source'],'Partial-date evidence lock mismatch')
 old=parse(current.decode(),date,m,c);src=parse(source.decode(),date,m,c,True);key='51410138';label='田殿71E3N1～引込';url='https://www.google.com/maps?q=34.31689,135.67107'
 require(set(old['views'])==set(src['views'])=={'51401633','51401634','51409716',key},'Partial-date identity set changed')
 v=old['views'][key];require(v.label==label and v.single_url==url and v.start is None and v.end is None and v.representative is None,'Unresolved current role changed')
 require(src['views'][key].label=='田殿　71E3N1～引き込み','Unknown unresolved source label')
 require(gps.get('田殿71E3N1')==(34.31689,135.67107) and c.url_point(url,label)==(label,34.31689,135.67107),'Retained single/GPS mismatch')
 slot=old['slots'][key];require('data-two-open' in slot[2].attrs and len(slot[4])==len(slot[5])==1,'Unknown invalid-two layout')
 script=slot[4][0];raw=json_unique(old['text'][script.head_end:old['text'].rfind('</script',script.start,script.end)]);zero=dict(name=label,lat=0.0,lng=0.0)
 require(raw==dict(a=zero,b=zero),'Nonzero/unknown endpoints must not be removed')
 q=old['points'].get(key);require(q==dict(name=label,lat=0.0,lng=0.0,management_no='514 10138'),'Nonzero/unknown representative must not be removed')
 return dict(key=key,current_label=label,source_label=src['views'][key].label,source_case_used=False,restored_roles=[],retained_single_url=url,removed_invalid_endpoints=raw,removed_invalid_representative=q,status='Unresolved end label; no map values copied from this source case')

def clean_partial_invalid_maps(text,date,m,p,c):
 if date!='260630':return text
 page=parse(text,date,m,c);slot=page['slots']['51410138'];edits=[(slot[2].start,slot[2].end,p._share_disabled_two_map_button())]
 for n in slot[4]+slot[5]:edits.append((n.start,n.end,''))
 text=m.edits_apply(text,edits);page=parse(text,date,m,c);a,b=page['pr'];raw=text[a:b];pos=1;spans=[]
 while True:
  while raw[pos] in ' \r\n\t,':pos+=1
  if raw[pos]==']':break
  q,used=json.JSONDecoder().raw_decode(raw[pos:]);spans.append((pos,pos+used,q));pos+=used
 require(len(spans)==4 and c.identity(spans[-1][2]['management_no'])=='51410138','Unresolved point position changed')
 q=spans[-1][2];require(q==dict(name='田殿71E3N1～引込',lat=0.0,lng=0.0,management_no='514 10138'),'Only exact invalid sentinel may be removed')
 comma=spans[-2][1]
 while raw[comma].isspace():comma+=1
 require(raw[comma]==',','Unknown point separator')
 return text[:a]+raw[:comma]+raw[spans[-1][1]:]+text[b:]

DUPLICATE_LOCK={'current': '80a2ffac69a343ee16808844d201da7b1a45c107ca60df1ffde4213216f5a127', 'source': '5d465731909217a327504ac6aae59d1ae9d6b3ed1b4b062331d1b0a9fc666028'}
DUPLICATE_GPS_SHA='8be7d23903c17b5d13a467a34b05ebe86563476fe5411702153ccdff9ecb1dce'
DUPLICATE_CASES={'51408052': {'label': '湯塩14N12～14N13', 'urls': ['https://www.google.com/maps?q=34.303805,135.727255', 'https://www.google.com/maps?q=34.303805,135.727255'], 'current_url': 'https://www.google.com/maps?q=34.303805,135.727255', 'gps_names': ['湯塩14N12', '湯塩14N13'], 'gps_decimal_pairs': [('34.30355', '135.72712'), ('34.30406', '135.72739')]}, '51408020': {'label': '湯塩29～30', 'urls': ['https://www.google.com/maps?q=34.30331,135.73045', 'https://www.google.com/maps?q=34.303309999999996,135.73045000000002'], 'current_url': 'https://www.google.com/maps?q=34.303309999999996,135.73045000000002', 'gps_names': ['湯塩29', '湯塩30'], 'gps_decimal_pairs': [('34.30321', '135.73068'), ('34.30341', '135.73022')]}, '51408022': {'label': '湯塩31～32', 'urls': ['https://www.google.com/maps?q=34.30391,135.729965', 'https://www.google.com/maps?q=34.30391,135.729965'], 'current_url': 'https://www.google.com/maps?q=34.30391,135.729965', 'gps_names': ['湯塩31', '湯塩32'], 'gps_decimal_pairs': [('34.30371', '135.73006'), ('34.30411', '135.72987')]}, '51408067': {'label': '湯塩35G2～35G3', 'urls': ['https://www.google.com/maps?q=34.305175,135.729095', 'https://www.google.com/maps?q=34.305175000000006,135.729095'], 'current_url': 'https://www.google.com/maps?q=34.305175000000006,135.729095', 'gps_names': ['湯塩35G2', '湯塩35G3'], 'gps_decimal_pairs': [('34.30525', '135.72907'), ('34.3051', '135.72912')]}, '51409807': {'label': '湯塩35N1～35N2', 'urls': ['https://www.google.com/maps?q=34.305655,135.72879', 'https://www.google.com/maps?q=34.305655,135.72879'], 'current_url': 'https://www.google.com/maps?q=34.305655,135.72879', 'gps_names': ['湯塩35N1', '湯塩35N2'], 'gps_decimal_pairs': [('34.30565', '135.72866'), ('34.30566', '135.72892')]}}
def source_projection(current,source,date,gps,m,p,c):
 if date!='260716':return known_source_projection(current,source,date,gps,m,p,c)
 require(sha(current)==DUPLICATE_LOCK['current'] and sha(source)==DUPLICATE_LOCK['source'],'Duplicate evidence byte lock mismatch')
 old=parse(current.decode(),date,m,c);require(set(old['views'])==set(DUPLICATE_CASES),'Duplicate current case set changed')
 text=source.decode();cards=list(c.CARD.finditer(text));require([c.identity(c.text_class(x[0],'item-mgmt')) for x in cards]==list(DUPLICATE_CASES),'Duplicate source card order/count changed')
 pm=m.one(list(re.finditer(r'\bvar\s+POINTS\s*=\s*',text)),'duplicate POINTS');_,used=json.JSONDecoder().raw_decode(text[pm.end():]);raw=text[pm.end():pm.end()+used];json_unique(raw);points=json.loads(raw,parse_float=Decimal,parse_int=Decimal)
 require(len(points)==5 and len({c.identity(q.get('management_no','')) for q in points})==5,'Duplicate POINTS identity/count changed')
 edits=[];receipt=[]
 for match in cards:
  block=match[0];key=c.identity(c.text_class(block,'item-mgmt'));expected=DUPLICATE_CASES[key];dom=m.DOM(block);require(c.text_class(block,'card-title')==expected['label']==old['views'][key].label,'Duplicate full span changed')
  singles=[n for n in dom.nodes if n.tag=='a' and n.cls('btn-map')];twos=[n for n in dom.nodes if n.tag=='button' and 'data-two-open' in n.attrs]
  require(len(singles)==2 and len(twos)==1 and singles[0].parent is singles[1].parent is twos[0].parent and singles[0].parent.cls('card-actions'),'Duplicate control structure changed')
  require(singles[0].start<singles[1].start<twos[0].start and not block[singles[0].end:singles[1].start].strip() and not block[singles[1].end:twos[0].start].strip(),'Duplicate control order/gaps changed')
  for i,node in enumerate(singles):
   exact_control(node,'single',dom);require(node.attrs=={'class':'btn btn-map','href':expected['urls'][i],'target':'_blank','rel':'noopener noreferrer'},'Duplicate attributes/URL changed');m.checked_url(node.attrs['href'],c)
  require([re.sub('<[^>]*>','',dom.content(n)) for n in singles]==['現場地図を開く','地図を開く'],'Duplicate caption order changed')
  q=m.one([q for q in points if c.identity(q.get('management_no',''))==key],'duplicate representative join');require(q['name']==expected['label'] and set(q)=={'name','lat','lng','management_no'},'Duplicate representative span/schema changed')
  decimal_pairs=[tuple(Decimal(x) for x in pair) for pair in expected['gps_decimal_pairs']]
  for name,pair in zip(expected['gps_names'],decimal_pairs):require(name in gps and tuple(Decimal(str(x)) for x in gps[name])==pair,'Duplicate exact GPS changed')
  midpoint=tuple((decimal_pairs[0][i]+decimal_pairs[1][i])/2 for i in range(2));point=(q['lat'],q['lng']);url_point=tuple(Decimal(x) for x in parse_qs(urlsplit(singles[0].attrs['href']).query)['q'][0].split(','))
  require(all(isinstance(x,Decimal) and x.is_finite() for x in point) and point==midpoint==url_point,'First URL/POINTS/GPS exact-decimal join failed')
  require(old['views'][key].single_url==expected['current_url'],'Retained current single literal changed')
  edits.append((match.start()+singles[1].start,match.start()+singles[1].end,''));receipt.append(dict(type='fixed-duplicate-source-read-only',key=key,label=expected['label'],selected_source_url=singles[0].attrs['href'],excluded_source_url=singles[1].attrs['href'],captions=['現場地図を開く','地図を開く'],source_control_count=2,output_control_count=1,point_decimal=[str(x) for x in point],gps_midpoint_decimal=[str(x) for x in midpoint],retained_current_url=old['views'][key].single_url,current_url_replaced=False))
 return m.edits_apply(text,edits).encode(),receipt

def repair(current,source,date,gps,m,p,c,row):
 unresolved=partial_plan(current,source,date,gps,m,p,c)
 require(row.get('unresolved_case')==unresolved,'Partial-date unresolved scope mismatch')
 source,exception_receipt=source_projection(current,source,date,gps,m,p,c)
 require(row.get('exception_receipt',[])==exception_receipt,'Exceptional source plan mismatch')
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
  if unresolved and key==unresolved['key']:
   expected[key]=v;computed[key]=[];unavailable[key]=[r for r in ROLES if not getattr(v,r)];continue
  w=sv[key];require(span_key(v.label)==span_key(w.label),'Non-whitespace source span mismatch: '+key)
  roles=[role for role in ROLES if not getattr(v,role) and getattr(w,role)];computed[key]=roles
  unavailable[key]=[role for role in ROLES if not getattr(v,role) and not getattr(w,role)]
  expected[key]=replace(v,**{role:((v.label,*w.representative[1:]) if role=='representative' else getattr(w,role)) for role in roles})
  if not any(getattr(w,r) or getattr(v,r) for r in ROLES):continue
  parts=p._share_split_span_label(w.label);require(parts,'Unsupported span '+key)
  names=(parts[0],p._share_complete_span_end_label(parts[0],parts[1],gps));ends=[]
  for role,name in zip(('start','end'),names):
   pole=p._share_resolve_gps_pole_label(name,gps)
   if not pole and date=='260709' and key=='51513023' and role=='end':
    require(v.start is None and v.end is None and w.start is None and w.end is None,'No endpoints may be invented');ends.append(None);continue
   require(pole,'Missing GPS '+key+' '+name);g=(pole,*gps[pole]);ends.append(g)
   for which,view in [('source',w),('current',v)]:
    pt=getattr(view,role)
    if pt:
     require(c.same(pt,g),'GPS/'+which+' conflict '+key+' '+role)
     allowed={c.norm(name),c.norm(parts[0] if role=='start' else parts[1])}
     if which=='current':allowed.add(c.norm(v.label))
     require(c.norm(pt[0]) in allowed,'Endpoint name conflict '+key+' '+role)
  midpoint=(w.label,(ends[0][1]+ends[1][1])/2,(ends[0][2]+ends[1][2])/2) if all(ends) else None
  for which,view in [('source',w),('current',v)]:
   for role,pt in [('single_url',c.url_point(view.single_url,v.label) if view.single_url else None),('representative',view.representative)]:
    if pt:require(any(c.same(pt,x) for x in [*ends,midpoint] if x is not None),'GPS/'+which+' '+role+' conflict '+key)
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
 result=m.edits_apply(old['text'],edits);result=clean_partial_invalid_maps(result,date,m,p,c);result=remove_zero_sentinel(result,date,m,c);result,class_receipt=semantic_classes(result,date,m,c);after=parse(result,date,m,c)
 require(after['views']==expected,'Repaired projection mismatch');require(c.parse_page(result,date)==expected,'Ordinary parse_page MapView mismatch');strict=strict_projection(after,date,m,p,c);c.verify_preserved(strict,date,[actual])
 require(business(old,m)==business(after,m),'NON-MAP BYTE CHANGE')
 for key,slot in old['slots'].items():
  for role in ROLES:
   if getattr(actual[key],role):require(getattr(after['views'][key],role)==getattr(actual[key],role),'Retained role changed')
 return result.encode(),dict(date=date,before_sha256=sha(current),after_sha256=sha(result.encode()),business_sha256=sha(business(old,m)),business_bytes_equal=True,map_roles=computed,unavailable_roles=unavailable,exception_receipt=exception_receipt,unresolved_case=unresolved,partial_date=bool(unresolved),semantic_class_exceptions=class_receipt,ordinary_parse_page_equal=True,ordinary_prepare_archive_maps='Not claimed compatible: unchanged representative/GPS-end conflict fails closed',source_exclusions=extras,source_ui_anomalies=src['source_ui_anomalies'],retained_url_differences=differences,whitespace_equivalence={k:dict(current_label=v.label,source_label=sv[k].label) for k,v in actual.items() if v.label!=sv[k].label},expected={k:asdict(v) for k,v in expected.items()},retained={k:asdict(v) for k,v in actual.items()})

def run(manifest,repo,scripts,gps_path,modern,out):
 for path in (repo,scripts,gps_path,modern,out):no_reparse(path)
 require(manifest['schema']=='legacy-map-only-v7','Unknown manifest');require(not out.exists(),'Output must be new')
 require(all(not out.resolve().is_relative_to(x.resolve()) for x in (repo,scripts,gps_path.parent)),'Output inside source')
 require(not any(r['date']=='260716' for r in manifest['pages']) or manifest['gps_sha256']==DUPLICATE_GPS_SHA,'Duplicate case requires exact GPS byte lock');m,p,c=dependencies(modern,scripts,manifest['helpers']);gps=m.load_gps(gps_path,manifest['gps_sha256'],p);prepared=[];seen=set()
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
