"""26-only post-generation display adapter. Run after the official shared-page generator.

No API access or database writes. Refuses changed source quantities. Existing
view assets remain source files; this adapter restores their entry points after
the normal generator regenerates share/261026/index.html.
"""
from pathlib import Path
import json,re,argparse
from html import escape,unescape

def apply(root):
    target=root/'share/261026/index.html'
    config_text=(target.parent/'assets/config.mjs').read_text(encoding='utf-8')
    config=json.loads(config_text.removeprefix('export const config=').strip().removesuffix(';'))
    assert config['date']=='261026' and len(config['cases'])==5
    codes=['E10','E20','E30','E40','E50','E60','N10','N20','N30','N40','N50','N60','SB','TK','TR']
    fields=['branch_cut_under_10','branch_cut_10_20','branch_cut_20_30','branch_cut_30_40','branch_cut_40_50','branch_cut_over_50','root_cut_under_10','root_cut_10_20','root_cut_20_30','root_cut_30_40','root_cut_40_50','root_cut_over_50','brush_area_m2','bamboo_count','vine_locations']
    text=target.read_text(encoding='utf-8');assert len(re.findall(r'<article\b',text))==5
    for entry in config['cases']:
        cs=entry['cs'];article=re.search(r'<article\b[^>]*data-management-no-key="'+cs+r'"[^>]*>.*?</article>',text,re.S);assert article,cs
        card=article.group()
        for code,field in zip(codes,fields):
            m=re.search(r'<td[^>]*data-quantity-field="'+field+r'"[^>]*data-quantity-state="confirmed"[^>]*>([^<]+)</td>',card)
            assert m and float(re.sub(r'(㎡|本|箇所)$','',m[1]))==entry['base'][code],f'{cs} {code}: baseline changed; reconcile before display'
        link=unescape(re.search(r'href="([^"]*/ledger-v2/[^"]*)"',card)[1])
        footer=f'<div class="photo-ledger-input-footer"><a class="btn btn-photo-ledger-input" href="instructions/?management_no={cs}">指示書</a><a class="btn btn-photo-ledger-input" href="{escape(link,quote=True)}" style="margin-top:6px">台帳入力</a></div>'
        updated,n=re.subn(r'<div class="photo-ledger-input-footer">.*?</div>(?:<div class="detail-edit-footer">.*?</div>)?',lambda m:footer,card,count=1,flags=re.S);assert n==1
        updated=re.sub(r'(<article\b)(?![^>]*\bid=)',r'\1 id="case-'+cs+'"',updated,count=1)
        text=text[:article.start()]+updated+text[article.end():]
    if 'data-daily-clearance' not in text:text=text.replace('<main>','<main>\n<p data-daily-clearance><a class="btn" href="daily/">日次離隔表</a></p>',1)
    if 'assets/views.mjs' not in text:text=text.replace('</body>','<script type="module" src="assets/views.mjs"></script>\n</body>')
    target.write_text(text,encoding='utf-8',newline='\n')
    return text

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();apply(args.root)
