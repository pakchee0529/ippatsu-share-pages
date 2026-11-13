"""Isolated five-day format correction from an immutable, already-public revision.

No business database, receipts, private files, or save actions are consulted.
The ordinary PC HTML renderer and ordinary detail-page templates are reused.
"""
from pathlib import Path
from html import unescape
import argparse, hashlib, json, re, subprocess, sys

SOURCE_REF = '27d90ef9d6541be58c3410376c9e55e8a5c02956'
DAYS = dict(zip(['261116','261117','261118','261119','261120'], [3,3,5,6,6]))
VERSION = '20261110-transport-r1'

def source(repo, rel):
    return subprocess.check_output(['git','-C',str(repo),'show',SOURCE_REF+':'+rel]).decode('utf8').replace('\r\n','\n')

def extract(text, fields):
    entries=[]
    for card in re.findall(r'<article\b[^>]*>.*?</article>',text,re.S):
        cs=re.search(r'data-management-no-key="(\d{8})"',card)[1]
        label=unescape(re.sub('<[^>]+>','',re.search(r'<h2\b[^>]*>(.*?)</h2>',card,re.S)[1]))
        quantities=[]
        for field in fields:
            m=re.search(r'<td\b([^>]*data-quantity-field="'+field+r'"[^>]*)>(.*?)</td>',card,re.S)
            if not m:raise ValueError('Missing source quantity '+cs+' '+field)
            attrs,raw=m.groups(); value=unescape(re.sub('<[^>]+>','',raw))
            evidence=re.search(r'data-evidence-state="([^"]+)"',attrs)
            state=evidence[1] if evidence else ('unknown' if 'data-quantity-state="unknown"' in attrs else 'source_zero' if re.fullmatch(r'0(?:㎡|本|箇所)?',value) else 'source_positive')
            if state not in {'source_positive','source_zero','source_blank','formal_confirmed','unknown','nonapplicable_candidate'}:raise ValueError('Unexpected evidence')
            quantities.append({'field':field,'state':state,'text':value})
        geo=json.loads(re.search(r'<script type="application/json" id="two-geo-\d+">(.*?)</script>',card,re.S)[1])
        maplink=unescape(re.search(r'<a\b[^>]*href="(https://www.google.com/maps[^" ]+)"',card)[1])
        summary=re.search(r'<table class="instr-table instr-summary">.*?</table>',card,re.S)
        note=re.search(r'<section class="provisional-source">(.*?)</section>|(<p class="provisional-source">.*?</p>)',card,re.S)
        notes=(note[1] or note[2]) if note else ''
        totals=re.search(r'<p class="review-totals">.*?</p>',card,re.S)
        if totals:notes+=totals[0]
        entries.append(dict(cs=cs,label=label,quantities=quantities,geo=geo,mapLink=maplink,conditions=summary[0] if summary else None,notes=notes))
    return entries

def generate(repo,pc_root,out):
    sys.path.insert(0,str(pc_root));sys.path.insert(0,str(repo/'scripts'))
    from app.share.html_generator import ShareItem,SharePoint,SharePagePayload,generate_share_html
    from apply_saved_ledger_views import FIELDS,CODES,templates
    inventory={};semantic={}
    for day,count in DAYS.items():
        old=source(repo,f'share/{day}/index.html');entries=extract(old,FIELDS)
        if len(entries)!=count or len({x['cs'] for x in entries})!=count:raise ValueError('Day set mismatch')
        if any(x['cs']=='51407008' for x in entries) != (day=='261117'):raise ValueError('Tuesday-only case mismatch')
        items=[]
        for e in entries:
            points=tuple(SharePoint(x['name'],x['lat'],x['lng']) for x in e['geo'].values())
            # Quantity defaults are never displayed in this source projection.
            items.append(ShareItem(e['label'],e['mapLink'],'',management_no=e['cs'],two_point_span=points,source_quantities={q['field']:(q['state'],q['text']) for q in e['quantities']}))
        # Retain the already-public whole-map representative points exactly.
        points=json.loads(re.search(r'var POINTS = (\[.*?\]);',old,re.S)[1])
        payload=SharePagePayload('20'+day[:2]+'/'+day[2:4]+'/'+day[4:]+' 現場共有',tuple(items),tuple(SharePoint(**x) for x in points))
        text=generate_share_html(payload)
        def project(m):
            card=m[0];i=int(re.search(r'data-card-index="(\d+)"',card)[1]);e=entries[i]
            card=card.replace('data-card-index="'+str(i)+'"','data-card-index="'+str(i)+'" data-management-no-key="'+e['cs']+'"')
            if e['conditions']:
                card=re.sub(r'<table class="instr-table instr-summary">.*?</table>',lambda _:e['conditions'],card,count=1,flags=re.S)
            if not e['conditions']:
                card=card.replace('<td>未設定</td>', '<td>未確認</td>').replace('<td>—</td>', '<td>未確認</td>')
            e['conditions']=re.search(r'<table class="instr-table instr-summary">.*?</table>',card,re.S)[0]
            card=card.replace('</article>','<div class="instr-note">'+e['notes']+'</div><nav><a class="btn" href="instructions/?management_no='+e['cs']+'">指示書</a></nav></article>')
            # Preserve the public single-map target; the normal renderer otherwise uses the old pole.
            card=re.sub(r'(class="btn btn-map btn-map-single" href=")[^"]+',lambda m:m[1]+e['mapLink'].replace('&','&amp;'),card,count=1)
            return card
        text=re.sub(r'<article\b[^>]*>.*?</article>',project,text,flags=re.S)
        text=text.replace('<body>', '<body data-source-only="true">')
        text=text.replace('</head>', '<link rel="stylesheet" media="print" href="../../portal/shared-ledger/weekly-source-print.css?v=20261113-print-r1"></head>')
        text=text.replace('<main>','<main><p>原典参照・閲覧専用。正式保存情報は未確認です。入力・保存・完了処理はありません。</p><p><a class="btn" href="daily/">日次離隔表</a></p>',1)
        for e in entries:
            for code,q in zip(CODES,e['quantities']):q['code']=code
        config={'schema':'ippatsu-weekly-source-format/v1','date':day,'cases':entries}
        encoded=json.dumps(config,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
        root=out/'share'/day;root.mkdir(parents=True,exist_ok=True)
        text='\n'.join(line.rstrip() for line in text.splitlines())+'\n'
        (root/'index.html').write_text(text,encoding='utf8',newline='\n')
        templates(out,day,encoded,source_only=True)
        # The ordinary render module imports the configuration parser but never loadDay.
        for folder in ['daily','instructions']:
            file=root/folder/'index.html';t=file.read_text().replace('<body data-share-view=', '<body data-source-only="true" data-share-view=');t=t.replace('</body>','<script id="shared-ledger-config" type="application/json">'+encoded+'</script></body>');file.write_text(t,encoding='utf8',newline='\n')
        semantic[day]=entries
        inventory[day]=hashlib.sha256(old.encode()).hexdigest()
    # Source-only assets and common renderer are explicit dependencies of this revision.
    assets=['views-provisional.mjs','views-readonly.mjs','ledger-view-render.mjs','weekly-source-print.css']
    for name in assets:
        target=out/'portal/shared-ledger'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((repo/'portal/shared-ledger'/name).read_bytes())
    paths=[f'share/{day}/{suffix}' for day in DAYS for suffix in ['index.html','daily/index.html','instructions/index.html']]+['portal/shared-ledger/'+x for x in assets]
    manifest={rel:hashlib.sha256((out/rel).read_bytes()).hexdigest() for rel in paths}
    (out/'scripts').mkdir(exist_ok=True)
    (out/'scripts/weekly_readonly_outputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'weekly-format-evidence.json').write_text(json.dumps({'source_ref':SOURCE_REF,'inputs':inventory,'cases':semantic},ensure_ascii=False,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pc-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    repo=Path(__file__).resolve().parents[1]
    if args.output.resolve()==repo:raise SystemExit('Use a separate output root')
    generate(repo,args.pc_root.resolve(),args.output.resolve())
