"""Common normal shared-card / instruction / new-ledger / daily generation.

Called by generate_portal.py after the existing quantity/map guards, for the
requested date only. No network access, business state changes or trial inputs.
"""
from pathlib import Path
from html import escape,unescape
import re,json

CODES=['E10','E20','E30','E40','E50','E60','N10','N20','N30','N40','N50','N60','SB','TK','TR']
ASSET_VERSION='20261026-carry1'
FIELDS=['branch_cut_under_10','branch_cut_10_20','branch_cut_20_30','branch_cut_30_40','branch_cut_40_50','branch_cut_over_50','root_cut_under_10','root_cut_10_20','root_cut_20_30','root_cut_30_40','root_cut_40_50','root_cut_over_50','brush_area_m2','bamboo_count','vine_locations']
def validate_asset_generation(root):
    assets=root/'portal'/'shared-ledger'
    html=(assets/'input.html').read_text(encoding='utf-8')
    if 'input-bootstrap.mjs?v='+ASSET_VERSION not in html:raise ValueError('Ledger input generation mismatch')
    worker=(assets/'sw.js').read_text(encoding='utf-8')
    if "ippatsu-shared-ledger-"+ASSET_VERSION not in worker:raise ValueError('Offline cache generation mismatch')
    names=json.loads(re.search(r'const ASSETS=(\[.*?\]);',worker,re.S)[1])
    for name in names:
        if not (assets/name.split('?')[0]).is_file():raise ValueError('Missing offline shell asset: '+name)
        if name.endswith('.mjs') or '.mjs?' in name or '.css?' in name:
            if '?v='+ASSET_VERSION not in name:raise ValueError('Offline asset generation mismatch: '+name)
    for path in assets.glob('*.mjs'):
        if re.search(r'[?&]ui=\d',path.read_text(encoding='utf-8')):raise ValueError('Hardcoded input-link generation: '+path.name)
        for target in re.findall(r"['\"](\./[^'\"]+\.mjs(?:\?[^'\"]*)?)['\"]",path.read_text(encoding='utf-8')):
            if not target.endswith('?v='+ASSET_VERSION):raise ValueError('Mixed ledger module generation: '+target)

def transform(root:Path,date:str,text:str)->str:
    validate_asset_generation(root)
    if not re.fullmatch(r'\d{6}',date):raise ValueError('Invalid shared date')
    entries=[]
    def card_replace(m):
        card=m.group();number=re.search(r'<p class="item-mgmt">([^<]+)</p>',card)
        if not number:return card
        cs=re.sub(r'\D','',unescape(number[1]));assert len(cs)==8,'ambiguous management number'
        title=re.search(r'<h2 class="card-title">(.*?)</h2>',card,re.S);assert title
        base={}
        for code,field in zip(CODES,FIELDS):
            value=re.search(r'<td[^>]*data-quantity-field="'+field+r'"[^>]*data-quantity-state="([^"]+)"[^>]*>([^<]+)</td>',card)
            assert value,cs+' '+field
            if value[1] not in {'confirmed','unknown'}:raise ValueError(cs+' '+field+': invalid quantity state')
            base[code]=float(re.sub(r'(㎡|本|箇所)$','',value[2])) if value[1]=='confirmed' else None
            if base[code] is not None and base[code].is_integer():base[code]=int(base[code])
        entries.append({'cs':cs,'label':unescape(re.sub('<[^>]+>','',title[1])),'base':base})
        target='../../portal/shared-ledger/input.html?date='+date+'&amp;management_no='+cs+'&amp;ui='+ASSET_VERSION
        footer=f'<div class="photo-ledger-input-footer"><a class="btn btn-photo-ledger-input" href="instructions/?management_no={cs}">指示書</a><a class="btn btn-photo-ledger-input" href="{target}" style="margin-top:6px">台帳入力</a></div>'
        card,n=re.subn(r'<div class="photo-ledger-input-footer">.*?</div>(?:<div class="detail-edit-footer">.*?</div>)?',lambda _:footer,card,count=1,flags=re.S)
        if not n:card=card.replace('</article>',footer+'</article>')
        card=re.sub(r'^<article\b[^>]*>',lambda t:re.sub(r'\s+id="case-\d{8}"','',t[0]),card,count=1)
        card=re.sub(r'(<article\b[^>]*)(>)',r'\1 id="case-'+cs+r'"\2',card,count=1)
        return card
    text=re.sub(r'<article\b[^>]*>.*?</article>',card_replace,text,flags=re.S)
    if len({e['cs'] for e in entries})!=len(entries):raise ValueError('Duplicate current CS; cannot bind ledger automatically')
    if not entries:return text
    config={'date':date,'api':'https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/photo-ledger-v2','cases':entries}
    text=re.sub(r'<script id="shared-ledger-config" type="application/json">.*?</script>\s*','',text,flags=re.S)
    text=re.sub(r'<script type="module" src="(?:assets/views.mjs|../../portal/shared-ledger/views.mjs)(?:\?[^"]*)?"></script>\s*','',text)
    encoded=json.dumps(config,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    text=text.replace('</body>','<script id="shared-ledger-config" type="application/json">'+encoded+'</script>\n<script type="module" src="../../portal/shared-ledger/views.mjs?v='+ASSET_VERSION+'"></script>\n</body>')
    if 'data-daily-clearance' not in text:text=text.replace('<main>','<main>\n<p data-daily-clearance><a class="btn" href="daily/">日次離隔表</a></p>',1)
    text=re.sub(r'(<!-- share-page-readability:end -->)\s*(</head>)',r'\1\n\n\2',text)
    templates(root,date,encoded)
    return text

def templates(root,date,encoded):
    style='body{font-family:system-ui,sans-serif;margin:0;background:#f1f5f9;color:#172534}main,header{max-width:1050px;margin:auto;padding:16px}a{color:#0755a1}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #cbd5e1;padding:9px;text-align:left;overflow-wrap:anywhere}.scroll{overflow-x:auto}.saved-ledger-status{font-size:.85rem;color:#475569}.card{width:auto!important}h1{font-size:1.3rem}.view-help{font-size:.9rem}.view-nav{display:flex;gap:8px;flex-wrap:wrap}.view-nav>a{display:inline-flex;padding:10px 14px;border:1px solid #93c5fd;border-radius:8px;background:white;color:#0755a1;text-decoration:none}'
    for folder,mode,title,content in [('instructions','instructions','指示書','<div id="content"></div>'),('daily','daily','日次離隔表','<div id="content"></div>')]:
        out=root/'share'/date/folder;out.mkdir(exist_ok=True)
        nav='<nav class="view-nav"><a href="../">共有ページに戻る</a><a id="ledger-input-top" href="#">台帳入力</a></nav>' if mode=='instructions' else '<a href="../">当日の共有ページへ戻る</a>'
        html=f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{date} {title}</title><style>{style}</style></head><body data-share-view="{mode}"><header>{nav}<h1>{title}</h1><p>閲覧用。変更・追加は新版台帳で入力し、ポータル保存後に反映します。</p></header><main><div id="error" role="alert"></div>{content}</main><script id="shared-ledger-config" type="application/json">{encoded}</script><script type="module" src="../../../portal/shared-ledger/views.mjs?v={ASSET_VERSION}"></script></body></html>'
        target=out/'index.html'
        if not target.exists() or target.read_text(encoding='utf-8')!=html:target.write_text(html,encoding='utf-8',newline='\n')
