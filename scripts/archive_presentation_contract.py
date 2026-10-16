"""Public archive display contract. No DB access or write/edit URL creation."""
from html.parser import HTMLParser
from html import escape,unescape
from urllib.parse import urlsplit,urlunsplit,urljoin,parse_qsl,urlencode
import re,posixpath
FIELDS=tuple([f'{k}_cut_{b}' for k in ('branch','root') for b in ('under_10','10_20','20_30','30_40','40_50','over_50')]+['brush_area_m2','bamboo_count','vine_locations'])
QUERY={**{f'E{n}':FIELDS[i] for i,n in enumerate((10,20,30,40,50,60))},**{f'N{n}':FIELDS[i+6] for i,n in enumerate((10,20,30,40,50,60))},'SB':'brush_area_m2','TK':'bamboo_count','TR':'vine_locations'}
CARD=re.compile(r'<article\b[^>]*class="[^"]*\bcard\b[^"]*"[^>]*>.*?</article>',re.S)

def cards(text):
 result=[]
 for m in CARD.finditer(text):
  p=CardParser();p.feed(m[0]);result.append((m,p))
 return result

class CardParser(HTMLParser):
 def __init__(self):
  super().__init__();self.number='';self.quantity={};self.links=[];self.capture=None;self.parts=[];self.anchor=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);cls=a.get('class','').split()
  if tag=='p' and 'item-mgmt' in cls:self.capture=('number',tag);self.parts=[]
  if tag=='td' and a.get('data-quantity-field') in FIELDS:
   self.capture=('quantity',tag,a['data-quantity-field'],a.get('data-quantity-state'));self.parts=[]
  if tag=='a':self.anchor=(a.get('href',''),[])
 def handle_data(self,text):
  if self.capture:self.parts.append(text)
  if self.anchor:self.anchor[1].append(text)
 def handle_endtag(self,tag):
  if self.capture and self.capture[1]==tag:
   t=''.join(self.parts).strip()
   if self.capture[0]=='number':self.number=t
   else:
    number=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(?:本|箇所|m²|㎡)?',t)
    self.quantity[self.capture[2]]=number[1] if self.capture[3]=='confirmed' and number else None
   self.capture=None
  if tag=='a' and self.anchor:
   href,parts=self.anchor;self.links.append({'href':href,'label':''.join(parts).strip()});self.anchor=None

def published_contract(text,date):
 out={}
 for rank,(_,p) in enumerate(cards(text)):
  if not re.fullmatch(r'\d{8}',p.number) or p.number in out:raise ValueError('Ambiguous published archive case number')
  links=[];omitted=0
  for a in p.links:
   u=urlsplit(a['href'])
   if u.scheme or u.netloc:continue
   resolved=urlsplit(urljoin('/share/'+date+'/index.html',a['href']))
   if resolved.path not in ('/portal/ledger-input/','/portal/ledger-v2/'):continue
   q=dict(parse_qsl(u.query,keep_blank_values=True))
   if q.get('management_no')!=p.number or q.get('date')!=date:raise ValueError('Published ledger identity mismatch')
   if 'edit_plan' in q:omitted+=1;continue
   links.append({'href':urlunsplit(('','',resolved.path,u.query,'')),'label':a['label'],'kind':'photo-ledger-draft'})
  out[p.number]={'schema':'ippatsu-archive-presentation/v1','rank':rank,'quantities':{f:p.quantity.get(f) for f in FIELDS},'links':links,'plan_edit_links_omitted':omitted}
 return out

def attach_contract(document,text):
 published=published_contract(text,str(document['date']))
 for group in ('items','planned_but_incomplete'):
  rows=document.get(group) or []
  for row in rows:
   item=row.get('source_item') if isinstance(row.get('source_item'),dict) else row
   key=str(row.get('management_no') or item.get('management_no') or '')
   c=published.get(key)
   if c is None:continue
   c={**c,'quantities':dict(c['quantities'])}
   for field,value in c['quantities'].items():
    # A stale published value is not provenance for a newly changed value.
    raw=item.get(field)
    if isinstance(raw,bool) or raw is None or value is None or str(raw)!=value and not (isinstance(raw,(int,float)) and float(value)==raw):c['quantities'][field]=None
   item['_archive_presentation']=c
  rows.sort(key=lambda r:(r.get('source_item',r).get('_archive_presentation') or {}).get('rank',10**9))
 return document

def _cell(field,values):
 value=values.get(field);known=value is not None
 if known and not re.fullmatch(r'\d+(?:\.\d+)?',str(value)):raise ValueError('Invalid archive quantity')
 return '<td data-quantity-field="'+field+'" data-quantity-state="'+('confirmed' if known else 'unknown')+'">'+(escape(str(value)) if known else '未確認')+'</td>'

def quantity_tables(card,values):
 labels=['〜10未満','〜20未満','〜30未満','〜40未満','〜50未満','50以上']
 rows=['<tr><th>'+label+'</th>'+_cell(FIELDS[i],values)+_cell(FIELDS[i+6],values)+'</tr>' for i,label in enumerate(labels)]
 totals=[]
 for fs in (FIELDS[:6],FIELDS[6:12]):totals.append(str(sum(float(values[f]) for f in fs)).removesuffix('.0') if all(values.get(f) is not None for f in fs) else '未確認')
 rows.append('<tr class="instr-cut-total"><th>合計</th><td>'+totals[0]+'</td><td>'+totals[1]+'</td></tr>')
 card,n=re.subn(r'(<table class="instr-table instr-cut">.*?<tbody>).*?(</tbody></table>)',lambda m:m[1]+''.join(rows)+m[2],card,count=1,flags=re.S)
 if n!=1:raise ValueError('Archive cut table missing')
 other=''.join('<tr><th>'+label+'</th>'+_cell(field,values)+'</tr>' for field,label in zip(FIELDS[12:],['柴伐採面積','竹伐採本数','つる伐採箇所数']))
 card,n=re.subn(r'(<table class="instr-table instr-other"><tbody>).*?(</tbody></table>)',lambda m:m[1]+other+m[2],card,count=1,flags=re.S)
 if n!=1:raise ValueError('Archive other table missing')
 return card

def ledger_links(contract,date):
 out=[]
 values=contract['quantities']
 for link in contract['links']:
  u=urlsplit(link['href']);q=parse_qsl(u.query,keep_blank_values=True)
  if u.scheme or u.netloc or u.path not in ('/portal/ledger-input/','/portal/ledger-v2/') or any(k=='edit_plan' for k,v in q):raise ValueError('Archive edit URL forbidden')
  q=[(k,v) for k,v in q if k not in QUERY]
  q.extend((k,values[f]) for k,f in QUERY.items() if values.get(f) is not None)
  href=posixpath.relpath(u.path,'/portal/archive/'+date)+'/?'+urlencode(q)
  out.append('<a class="btn archive-ledger-link" data-archive-link-kind="photo-ledger-draft" href="'+escape(href,quote=True)+'" target="_blank" rel="noopener noreferrer">'+escape(link['label'])+'</a>')
 return '<div class="archive-ledger-links">'+''.join(out)+'</div>' if out else ''

def apply_archive_contract(text,document):
 by_key={str(r.get('management_no')):r.get('source_item',r).get('_archive_presentation') for g in ('items','planned_but_incomplete') for r in (document.get(g) or [])}
 for m,p in reversed(cards(text)):
  c=by_key.get(p.number)
  if not c:continue # Historical exports keep their legacy rendering.
  if c.get('schema')!='ippatsu-archive-presentation/v1':raise ValueError('Unknown archive contract')
  card=quantity_tables(m[0],c['quantities'])
  # Archive input links never create a business-detail/plan-edit route.
  card=re.sub(r'<a\b[^>]*class="[^"]*\bbtn-detail-edit\b[^>]*>.*?</a>','',card,flags=re.S)
  card=card.replace('</article>',ledger_links(c,str(document['date']))+'</article>')
  text=text[:m.start()]+card+text[m.end():]
 return text

def verify_archive_contract(document,text):
 expected=[str(r['management_no']) for g in ('items','planned_but_incomplete') for r in (document.get(g) or [])]
 parsed=cards(text)
 if [p.number for m,p in parsed]!=expected:raise ValueError('Archive display order differs')
 source={str(r['management_no']):r.get('source_item',r).get('_archive_presentation') for g in ('items','planned_but_incomplete') for r in (document.get(g) or [])}
 for m,p in parsed:
  c=source.get(p.number)
  if not c:continue
  if p.quantity!=c['quantities']:raise ValueError('Archive quantity state differs')
  expected_links=CardParser();expected_links.feed(ledger_links(c,str(document['date'])))
  actual=[a for a in p.links if '/ledger-input/' in a['href'] or '/ledger-v2/' in a['href']]
  if actual!=expected_links.links:raise ValueError('Archive photo ledger links differ')
  if any('edit_plan' in a['href'] for a in p.links):raise ValueError('Archive plan edit URL forbidden')


_display_original_apply = apply_archive_contract
def apply_archive_contract(text,document):
    from quantity_display_contract import display_html
    return display_html(_display_original_apply(text,document))
