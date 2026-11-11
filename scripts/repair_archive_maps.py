"""Candidate-only legacy archive map repair. No business export or DB reader/writer.
Pinned published HTML supplies map evidence; the current HTML supplies immutable
business bytes. All pages preflight before the single new-directory rename.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse, ast, hashlib, json, os, re, stat, subprocess, tempfile, types
from dataclasses import asdict, replace
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

class ContractError(ValueError): pass
def require(ok, reason):
    if not ok: raise ContractError(reason)
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def no_reparse(path):
    # Refuse path redirection rather than following it into another resource.
    current=Path(os.path.abspath(path))
    for p in (current,*current.parents):
        try: info=os.lstat(p)
        except FileNotFoundError:continue
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info,'st_file_attributes',0)&0x400),'Symlink/reparse path forbidden: '+str(p))

def gitshow(repo, spec):
    return subprocess.check_output(['git','-C',str(repo),'show',spec],stderr=subprocess.PIPE)
def proof_bytes(repo, proof, date, kind):
    require(re.fullmatch('[0-9a-f]{40}',proof['commit']), 'Full commit required')
    require(proof['path']==(f'portal/archive/{date}/index.html' if kind=='current' else f'share/{date}/index.html'),'Wrong proof path/date')
    no_reparse(repo/proof['path'])
    data=gitshow(repo,proof['commit']+':'+proof['path'])
    require(blob(data)==proof['blob'] and sha(data)==proof['sha256'],'Proof bytes/hash mismatch')
    return data

class Node:
    def __init__(self,tag,attrs,start,head_end,parent):
        self.tag,self.attrs,self.start,self.head_end,self.parent=tag,dict(attrs),start,head_end,parent
        require(len(attrs)==len(self.attrs),'Duplicate DOM attributes')
        self.end=None
    def cls(self,c): return c in self.attrs.get('class','').split()

class DOM(HTMLParser):
    VOID=set('area base br col embed hr img input link meta param source track wbr'.split())
    def __init__(self,text):
        super().__init__(convert_charrefs=False);self.text=text;self.nodes=[];self.stack=[]
        self.lines=[0]+[m.end() for m in re.finditer('\n',text)];self.feed(text);self.close()
        require(not self.stack,'Unclosed DOM')
        ids=[n.attrs['id'] for n in self.nodes if 'id' in n.attrs]
        require(len(ids)==len(set(ids)),'Duplicate DOM id')
    def pos(self):
        row,col=self.getpos();return self.lines[row-1]+col
    def handle_starttag(self,tag,attrs):
        p=self.pos();n=Node(tag,attrs,p,p+len(self.get_starttag_text()),self.stack[-1] if self.stack else None);self.nodes.append(n)
        if tag in self.VOID:n.end=n.head_end
        else:self.stack.append(n)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID:self.stack.pop().end=self.pos()+len(self.get_starttag_text())
    def handle_endtag(self,tag):
        require(bool(self.stack) and self.stack[-1].tag==tag,'Malformed/unrecognized DOM close '+tag)
        n=self.stack.pop();n.end=self.text.index('>',self.pos())+1
    def inside(self,n,parent):return parent.start<n.start and n.end<parent.end
    def content(self,n):return self.text[n.start:n.end]

def one(nodes,label):
    require(len(nodes)==1,'Missing/duplicate '+label);return nodes[0]
def edits_apply(text,edits):
    edits=sorted(edits,key=lambda x:(x[0],x[1]));last=0;parts=[]
    for a,b,v in edits:
        require(last<=a<=b,'Overlapping edits');parts += [text[last:a],v];last=b
    return ''.join(parts)+text[last:]
def point_range(text):
    m=one(list(re.finditer(r'\bvar points = ',text)),'legacy overall points assignment')
    raw,end=json.JSONDecoder().raw_decode(text[m.end():]);require(isinstance(raw,list),'Points not array')
    return m.end(),m.end()+end

def slots(text,contract):
    require(not contract.is_fixed_form_alias(text) and 'data-final-ledger-identity=' not in text,'Fixed-form alias forbidden')
    dom=DOM(text);cards=[n for n in dom.nodes if n.tag=='article' and n.cls('card')]
    require(cards and len(cards)==len(list(contract.CARD.finditer(text))),'Unknown/nested card format')
    result=[]
    for card in cards:
        ns=[n for n in dom.nodes if dom.inside(n,card)]
        single=one([n for n in ns if n.cls('btn-map-single')],'single control')
        two=one([n for n in ns if n.cls('btn-map-two')],'two control')
        note=one([n for n in ns if n.cls('note-panel')],'note-panel')
        scripts=[n for n in ns if n.tag=='script']
        panels=[n for n in ns if n.cls('two-map-wrap')]
        require(len(scripts)==len(panels) and len(scripts)<=1,'Unknown map payload/panel layout')
        for n in scripts:require(n.attrs.get('type')=='application/json' and n.attrs.get('id','').startswith('two-geo-'),'Unknown card script')
        require(single.parent==two.parent and single.parent.cls('card-actions'),'Map controls not in actions')
        require(all(n.end<=note.start for n in scripts+panels),'Map payload outside designated position')
        result.append((card,single,two,note,scripts,panels))
    section=one([n for n in dom.nodes if n.tag=='section' and n.cls('map-section')],'overall map section')
    return dom,result,section,point_range(text)

def business_bytes(text,contract):
    dom,cs,section,pr=slots(text,contract);edits=[(section.start,section.end,''),(*pr,'')]
    for card,single,two,note,scripts,panels in cs:
        edits.extend((n.start,n.end,'') for n in [single,two]+scripts+panels)
    return edits_apply(text,edits).encode('utf-8')

def checked_url(url,contract):
    u=urlsplit(url)
    require(u.scheme=='https' and u.netloc=='www.google.com' and u.path=='/maps' and not u.fragment,'Unapproved map URL')
    require(set(parse_qs(u.query))=={'q'} and contract.url_point(url,'') is not None,'Non-coordinate map URL')

def repair(current,source,date,gps,portal,contract,repair_roles):
    # READ PHASE: parse actual controls, permit missing values but never conflicts.
    text=current.decode('utf-8');prior=source.decode('utf-8')
    dom,cs,section,pr=slots(text,contract)
    actual=contract.parse_page(text,date);source_views=contract.parse_page(prior,date)
    expected=dict(actual)
    require(set(repair_roles)<=set(actual),'Repair identity missing')
    require(all(isinstance(v,list) and len(v)==len(set(v)) and set(v)<={'single_url','start','end','representative'} for v in repair_roles.values()),'Invalid repair role list')
    for key,old in actual.items():
        missing={role for role in ('single_url','start','end','representative') if not getattr(old,role)}
        require(set(repair_roles.get(key,[]))==missing,'Repair scope must exactly describe missing roles: '+key)
        require(('start' in missing)==('end' in missing),'Partial endpoint repair unsupported')
        if missing:
            require(key in source_views,'Missing source identity')
            expected[key]=replace(old,**{role:getattr(source_views[key],role) for role in missing})
    require(actual and set(actual)==set(source_views),'Evidence/card identity set mismatch')
    for key,old in actual.items():
        want=source_views[key]
        require(old.label==want.label,'Exact identity/span mismatch: '+key)
        require(want.start and want.end and want.single_url and want.representative,'Incomplete original map evidence: '+key)
        checked_url(want.single_url,contract)
        require(any(contract.same(want.representative,x) for x in (want.start,want.end)),'Original overall not an endpoint: '+key)
        parts=portal._share_split_span_label(want.label);require(parts,'Unsupported span')
        names=[parts[0],portal._share_complete_span_end_label(parts[0],parts[1],gps)]
        for role,name in zip(('start','end'),names):
            pole=portal._share_resolve_gps_pole_label(name,gps);require(pole,'Missing canonical GPS: '+key)
            pt=getattr(want,role);require(contract.same(pt,(pole,*gps[pole])),'GPS/source conflict: '+key+' '+role)
            require(contract.norm(pt[0]) in {contract.norm(name),contract.norm(parts[0] if role=='start' else parts[1])},'Original endpoint label conflict')
            existing=getattr(old,role)
            if existing:
                require(contract.same(existing,pt),'Current/source coordinate conflict')
                require(existing[0] in (pt[0],old.label),'Unknown legacy endpoint name')
        if old.single_url:
            checked_url(old.single_url,contract);require(contract.same_url(old.single_url,want.single_url),'Current/source URL conflict')
        # Existing overall points are immutable. Original/current representative
        # policy may differ (start versus end); never rewrite a retained role.
        if old.representative:require(any(contract.same(old.representative,x) for x in (want.start,want.end)),'Existing overall/GPS conflict')
    # Reuse exact map-only renderer helpers, never invoke the business renderer.
    tree=ast.parse(portal.__verified_source_bytes__.decode('utf-8-sig'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_archive_detail_html')
    blocks=[n.value.strip() for n in ast.walk(fn) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.lstrip().startswith('<section class="map-section')]
    require(len(blocks)==2 and dom.content(section).strip() in blocks,'Unknown overall-map DOM template')
    full=one([b for b in blocks if 'map-empty' not in b],'renderer map section')
    require('twoMaps' in text and 'document.querySelectorAll("[data-two-open]")' in text and 'var map = L.map("share-map"' in text,'Missing established map runtime')
    runtime=[s for s in re.findall(r'<script\b[^>]*>.*?</script>',text,re.S) if 'var twoMaps' in s]
    require(len(runtime)==1,'Missing map handler runtime')
    ra,rb=point_range(runtime[0])
    require(sha((runtime[0][:ra]+runtime[0][rb:]).encode('utf-8')) in {'b49cbfd1df0faf35b9874b7fed0d634cf45daeeea605f89be42f350aafab2027'},'Unknown map handler runtime; adapter required')
    points=[];edits=[(section.start,section.end,full)]
    for idx,(card,single,two,note,scripts,panels) in enumerate(cs):
        key=contract.identity(contract.text_class(dom.content(card),'item-mgmt'));v=expected[key]
        ident=f'two-geo-{idx}';geo=portal.build_two_geo_payload(a_name=v.start[0],a_lat=v.start[1],a_lng=v.start[2],b_name=v.end[0],b_lat=v.end[1],b_lng=v.end[2],gps_poles=None)
        payload=portal.format_two_geo_script(ident,geo)+portal._share_two_map_panel(idx)
        roles=repair_roles.get(key,[])
        if 'single_url' in roles:edits.append((single.start,single.end,portal._archive_single_map_button(v)))
        if 'start' in roles:
            require(not scripts and not panels,'Missing roles with retained payload')
            edits.append((two.start,two.end,portal._share_two_map_button(ident,idx)))
            edits.append((note.start,note.start,payload))
        points.append(dict(name=v.label,lat=v.representative[1],lng=v.representative[2],management_no=key))
    edits.append((*pr,portal.json_for_script_tag(points)))
    result=edits_apply(text,edits)
    # STRICT PHASE: the existing guard is unchanged. No missing role permitted.
    contract.verify_rendered(result,date,expected)
    contract.verify_preserved(result,date,[expected])
    contract.verify_preserved(result,date,[actual])
    require(business_bytes(text,contract)==business_bytes(result,contract),'NON-MAP BYTE CHANGE')
    return result.encode('utf-8'),dict(date=date,cards=len(cs),business_sha256=sha(business_bytes(text,contract)),before_sha256=sha(current),after_sha256=sha(result.encode('utf-8')),map_roles=repair_roles,business_bytes_equal=True,expected_projection={k:asdict(v) for k,v in expected.items()},retained_projection={k:asdict(v) for k,v in actual.items()})

_LOADED_HELPERS = None

def load_dependencies(path,locks):
    global _LOADED_HELPERS
    require(set(locks)=={'generate_portal.py','archive_map_contract.py','portal_immediate_status_client.py'},'Incomplete helper lock')
    verified={}
    for name,digest in locks.items():
        no_reparse(path/name)
        data=(path/name).read_bytes()
        require(sha(data)==digest,'Helper hash mismatch: '+name)
        verified[name[:-3]]=data
    names=['portal_immediate_status_client','generate_portal','archive_map_contract']
    signature=(str(path.resolve()),tuple(sorted(locks.items())))
    if _LOADED_HELPERS is not None:
        old_signature,modules=_LOADED_HELPERS
        require(signature==old_signature and all(sys.modules.get(n) is modules[n] for n in names),'Helper import cache provenance changed')
        require(all(modules[n].__verified_source_bytes__==verified[n] for n in names),'Executed helper bytes differ')
    else:
        require(not any(n in sys.modules for n in names),'Untracked preloaded helper module; use a fresh process')
        modules={}
        try:
            for name in names:
                filename=str((path/(name+'.py')).resolve())
                module=types.ModuleType(name)
                module.__file__=filename
                module.__package__=''
                module.__verified_source_bytes__=verified[name]
                modules[name]=module
                sys.modules[name]=module
                # Execute exactly the verified bytes. Never consult timestamp pyc,
                # importlib filesystem loaders, or reread the source after hashing.
                exec(compile(verified[name],filename,'exec'),module.__dict__)
                require(module.__verified_source_bytes__==verified[name],'Helper source-byte binding changed')
        except BaseException:
            for name,module in modules.items():
                if sys.modules.get(name) is module:del sys.modules[name]
            raise
        _LOADED_HELPERS=(signature,modules)
    for name,module in modules.items():
        require(Path(module.__file__).resolve()==(path/(name+'.py')).resolve(),'Imported helper path mismatch')
    return modules['generate_portal'],modules['archive_map_contract']


def load_gps(path,digest,portal):
    no_reparse(path)
    data=path.read_bytes()
    require(sha(data)==digest,'GPS hash mismatch')
    # Match the adopted loader, but reject key collisions rather than last-wins.
    def pairs(values):
        result={}
        for k,v in values:
            require(k not in result,'Duplicate GPS JSON key');result[k]=v
        return result
    rows=json.loads(data.decode('utf-8'),object_pairs_hook=pairs);gps={}
    require(isinstance(rows,dict),'GPS schema mismatch')
    for raw_name,value in rows.items():
        name=portal._share_gps_lookup_key(raw_name)
        if not name or not isinstance(value,str):continue
        parts=value.split(',')
        if len(parts)!=2:continue
        try: pair=tuple(float(v.strip()) for v in parts)
        except (ValueError,TypeError):continue
        if name in gps:require(gps[name]==pair,'GPS duplicate coordinate conflict: '+name)
        gps[name]=pair
    require(gps,'Empty GPS');return gps

def run(manifest,repo,scripts,gps_path,out):
    for path in (repo,scripts,gps_path,out):no_reparse(path)
    require(manifest.get('schema')=='archive-map-only-v1','Unknown manifest')
    require(not out.exists(),'Output must be a NEW directory')
    require(not out.resolve().is_relative_to(repo.resolve()) and not out.resolve().is_relative_to(scripts.resolve()) and not out.resolve().is_relative_to(gps_path.parent.resolve()),'Output must be outside source repositories/resources')
    portal,contract=load_dependencies(scripts,manifest['helpers'])
    gps=load_gps(gps_path,manifest['gps_sha256'],portal)
    prepared=[];seen=set()
    for row in manifest['pages']:
        date=row['date'];require(re.fullmatch(r'\d{6}',date) and date not in seen,'Duplicate/invalid date');seen.add(date)
        before=proof_bytes(repo,row['current'],date,'current');source=proof_bytes(repo,row['source'],date,'source')
        working=(repo/row['current']['path']).read_bytes()
        require(sha(working)==row['working_sha256'],'Current working page changed')
        require(working.replace(b'\r\n',b'\n')==before.replace(b'\r\n',b'\n'),'Working page differs from pinned published blob')
        data,report=repair(before,source,date,gps,portal,contract,row['repair_roles']);report['proof']=row;prepared.append((date,data,report))
    require(prepared,'Empty batch')
    # All validations finish before any output. Failure leaves no publishable batch.
    out.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.map-only-staging-',dir=out.parent))
    for date,data,report in prepared:
        p=stage/'portal/archive'/date/'index.html';p.parent.mkdir(parents=True);p.write_bytes(data)
    (stage/'MAP-ONLY-REPORT.json').write_text(json.dumps([r for _,_,r in prepared],ensure_ascii=False,indent=2),encoding='utf-8')
    os.rename(stage,out)
    return [r for _,_,r in prepared]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--scripts',type=Path,required=True);p.add_argument('--gps',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(run(json.loads(a.manifest.read_text(encoding='utf-8')),a.repo,a.scripts,a.gps,a.output),ensure_ascii=True,indent=2))
