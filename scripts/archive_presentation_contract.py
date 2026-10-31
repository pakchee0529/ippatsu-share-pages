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

def attach_contract(document,text,*,completion_snapshot=False):
 published=published_contract(text,str(document['date']))
 for group in ('items','planned_but_incomplete'):
  rows=document.get(group) or []
  for snapshot_rank,row in enumerate(rows):
   item=row.get('source_item') if isinstance(row.get('source_item'),dict) else row
   key=str(row.get('management_no') or item.get('management_no') or '')
   c=published.get(key)
   if c is None:continue
   c={**c,'quantities':dict(c['quantities'])}
   for field,value in c['quantities'].items():
    # A stale published value is not provenance for a newly changed value.
    raw=item.get(field)
    if isinstance(raw,bool) or raw is None or value is None or str(raw)!=value and not (isinstance(raw,(int,float)) and float(value)==raw):c['quantities'][field]=None
   if completion_snapshot and row.get('completion_status')=='completed':
    c['rank']=snapshot_rank
    c['quantity_source']='completion-report-snapshot/v1'
    c['quantities']=_snapshot_quantities(item)
    c['snapshot_sha256']=_snapshot_hash(item,str(document['date']),key)
   item['_archive_presentation']=c
  if not completion_snapshot:rows.sort(key=lambda r:(r.get('source_item',r).get('_archive_presentation') or {}).get('rank',10**9))
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

def apply_archive_contract(text,document,*,snapshot_renderer=None):
 by_key={str(r.get('management_no')):r.get('source_item',r).get('_archive_presentation') for g in ('items','planned_but_incomplete') for r in (document.get(g) or [])}
 for m,p in reversed(cards(text)):
  c=by_key.get(p.number)
  if not c:continue # Historical exports keep their legacy rendering.
  if c.get('schema')!='ippatsu-archive-presentation/v1':raise ValueError('Unknown archive contract')
  item=next(r.get('source_item',r) for group in ('items','planned_but_incomplete') for r in (document.get(group) or []) if str(r.get('management_no'))==p.number)
  if c.get('quantity_source') not in (None,'completion-report-snapshot/v1'):raise ValueError('Unknown archive quantity source')
  if c.get('quantity_source')=='completion-report-snapshot/v1':
   card=_replace_snapshot_tables(m[0],_snapshot_tables(item,c,str(document['date']),p.number,snapshot_renderer))
  else:card=quantity_tables(m[0],c['quantities'])
  # Archive input links never create a business-detail/plan-edit route.
  card=re.sub(r'<a\b[^>]*class="[^"]*\bbtn-detail-edit\b[^>]*>.*?</a>','',card,flags=re.S)
  card=card.replace('</article>',ledger_links(c,str(document['date']))+'</article>')
  text=text[:m.start()]+card+text[m.end():]
 return text

def verify_archive_contract(document,text,*,snapshot_renderer=None):
 expected=[str(r['management_no']) for g in ('items','planned_but_incomplete') for r in (document.get(g) or [])]
 parsed=cards(text)
 if [p.number for m,p in parsed]!=expected:raise ValueError('Archive display order differs')
 source={str(r['management_no']):r.get('source_item',r).get('_archive_presentation') for g in ('items','planned_but_incomplete') for r in (document.get(g) or [])}
 for m,p in parsed:
  c=source.get(p.number)
  if not c:continue
  if c.get('quantity_source') not in (None,'completion-report-snapshot/v1'):raise ValueError('Unknown archive quantity source')
  if c.get('quantity_source')=='completion-report-snapshot/v1':
   capture_tables=_quantity_display().capture_tables
   item=next(r.get('source_item',r) for group in ('items','planned_but_incomplete') for r in (document.get(group) or []) if str(r.get('management_no'))==p.number)
   _verify_snapshot_cells(m[0],item,c,str(document['date']),p.number)
   if snapshot_renderer is not None and capture_tables(m[0])!=_snapshot_tables(item,c,str(document['date']),p.number,snapshot_renderer):raise ValueError('Completion snapshot display differs')
  elif p.quantity!=c['quantities']:raise ValueError('Archive quantity state differs')
  expected_links=CardParser();expected_links.feed(ledger_links(c,str(document['date'])))
  actual=[a for a in p.links if '/ledger-input/' in a['href'] or '/ledger-v2/' in a['href']]
  if actual!=expected_links.links:raise ValueError('Archive photo ledger links differ')
  if any('edit_plan' in a['href'] for a in p.links):raise ValueError('Archive plan edit URL forbidden')


_display_original_apply = apply_archive_contract
def apply_archive_contract(text,document,*,snapshot_renderer=None):
    from quantity_display_contract import display_html
    return display_html(_display_original_apply(text,document,snapshot_renderer=snapshot_renderer))

def _snapshot_quantities(item):
 from decimal import Decimal,InvalidOperation
 states=item.get('_quantity_html_states') or {}
 if not isinstance(states,dict) or any(k in FIELDS and v not in ('unknown','confirmed') for k,v in states.items()):raise ValueError('Invalid snapshot quantity state')
 values={}
 for field in FIELDS:
  if field not in item:raise ValueError('Completion snapshot field missing')
  raw=item[field]
  if raw is None or states.get(field)=='unknown':values[field]=None;continue
  if isinstance(raw,bool) or not isinstance(raw,(int,float)):raise ValueError('Invalid completion snapshot quantity')
  number=Decimal(str(raw))
  if not number.is_finite() or number<0:raise ValueError('Invalid completion snapshot quantity')
  values[field]=format(number,'f').rstrip('0').rstrip('.') if '.' in format(number,'f') else format(number,'f')
 for field,formula in (item.get('_completion_felling_formula') or {}).items():
  if field not in FIELDS or not isinstance(formula,dict):raise ValueError('Invalid completion formula')
  before,added=formula.get('before'),formula.get('added')
  if any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in (before,added)):raise ValueError('Invalid completion formula')
  a,b=Decimal(str(before)),Decimal(str(added))
  declared=(item.get('_completion_felling_added') or {}).get(field,added)
  if isinstance(declared,bool) or not isinstance(declared,(int,float)) or Decimal(str(declared))!=b:raise ValueError('Completion added amount differs')
  raw=item[field]
  if not a.is_finite() or a<0 or not b.is_finite() or isinstance(raw,bool) or not isinstance(raw,(int,float)) or a+b!=Decimal(str(raw)):raise ValueError('Completion formula differs from final snapshot')
 return values

def _snapshot_hash(item,date,number):
 import hashlib,json
 value={'date':date,'management_no':number,'quantities':{f:item.get(f) for f in FIELDS},'states':item.get('_quantity_html_states') or {},'formula':item.get('_completion_felling_formula') or {},'added':item.get('_completion_felling_added') or {}}
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def _snapshot_tables(item,contract,date,number,renderer):
 from copy import deepcopy
 display=_quantity_display();capture_tables,annotate_tables=display.capture_tables,display.annotate_tables
 if renderer is None:raise ValueError('Completion snapshot renderer required')
 if contract.get('snapshot_sha256')!=_snapshot_hash(item,date,number) or contract['quantities']!=_snapshot_quantities(item):raise ValueError('Completion snapshot changed')
 display=deepcopy(item);unknown={f:'unknown' for f,v in contract['quantities'].items() if v is None}
 for field in unknown:
  display[field]=None
  for name in ('_completion_felling_formula','_completion_felling_added'):
   display.get(name,{}).pop(field,None)
 # Reuse the adopted source renderer and existing unknown-display policy.
 fragment=annotate_tables(renderer(display),unknown)
 _verify_snapshot_cells(fragment,item,contract,date,number)
 tables=capture_tables(fragment)
 if len(tables)!=2:raise ValueError('Completion snapshot table shape differs')
 return tables

def _replace_snapshot_tables(card,tables):
 TABLE=_quantity_display().TABLE
 matches=list(TABLE.finditer(card))
 if len(matches)!=len(tables):raise ValueError('Completion snapshot table shape differs')
 for m,body in reversed(list(zip(matches,tables))):card=card[:m.start()]+body+card[m.end():]
 return card


def _quantity_display():
 if __package__=='app.share':
  from app.share import quantity_display_contract as display
 else:
  import quantity_display_contract as display
 return display

def _verify_snapshot_cells(card,item,contract,date,number):
 from decimal import Decimal
 display=_quantity_display()
 if contract.get('snapshot_sha256')!=_snapshot_hash(item,date,number) or contract['quantities']!=_snapshot_quantities(item):raise ValueError('Completion snapshot changed')
 tables=display.capture_tables(card)
 if len(tables)!=2:raise ValueError('Completion snapshot table shape differs')
 cut,other=tables
 cells=lambda table:list(re.finditer(r'(<td\b[^>]*>)(.*?)(</td>)',table,re.S))
 cutcells,othercells=cells(cut),cells(other)
 if len(cutcells)!=14 or len(othercells)!=3:raise ValueError('Completion snapshot cell count differs')
 def terms(cell,unit=''):
  raw=unescape(cell[2]).strip()
  if '<' in raw:raise ValueError('Unexpected snapshot quantity markup')
  if unit:
   # Exact legacy brush-unit bytes emitted by the adopted added-area formatter.
   # Read compatibility only: no output/table/source-value rewriting.
   allowed=(unit,'\u7dd5\uff61') if unit=='\u33a1' else (unit,)
   suffix=next((u for u in allowed if raw.endswith(u)),None)
   if suffix is None:raise ValueError('Snapshot quantity unit differs')
   raw=raw[:-len(suffix)].strip()
  match=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)(?:\s*\+\s*(-?[0-9]+(?:\.[0-9]+)?))?',raw)
  if not match:raise ValueError('Snapshot quantity expression differs')
  return tuple(Decimal(v) for v in match.groups() if v is not None)
 def expected(field):
  value=contract['quantities'][field]
  if value is None:return (Decimal(0),)
  formula=(item.get('_completion_felling_formula') or {}).get(field)
  if formula and Decimal(str(formula['added']))>0:return (Decimal(str(formula['before'])),Decimal(str(formula['added'])))
  return (Decimal(value),)
 fields=[field for pair in zip(FIELDS[:6],FIELDS[6:12]) for field in pair]
 for field,cell in zip(fields,cutcells[:12]):
  state=display.attr(cell[1],'data-quantity-state');declared=display.attr(cell[1],'data-quantity-field')
  if declared not in (None,field):raise ValueError('Snapshot quantity field differs')
  if contract['quantities'][field] is None:
   if state!='unknown' or declared!=field:raise ValueError('Unknown snapshot quantity lost its state')
  elif state not in (None,'confirmed'):raise ValueError('Confirmed snapshot quantity state differs')
  if terms(cell)!=expected(field):raise ValueError('Snapshot original/additional/final quantity differs')
 for field,unit,cell in zip(FIELDS[12:],('㎡','本','箇所'),othercells):
  state=display.attr(cell[1],'data-quantity-state');declared=display.attr(cell[1],'data-quantity-field')
  if declared not in (None,field):raise ValueError('Snapshot quantity field differs')
  if contract['quantities'][field] is None:
   if state!='unknown' or declared!=field:raise ValueError('Unknown snapshot quantity lost its state')
  elif state not in (None,'confirmed'):raise ValueError('Confirmed snapshot quantity state differs')
  if terms(cell,unit)!=expected(field):raise ValueError('Snapshot original/additional/final quantity differs')
 for group,cell in zip((FIELDS[:6],FIELDS[6:12]),cutcells[12:]):
  final=sum((Decimal(contract['quantities'][f]) for f in group if contract['quantities'][f] is not None),Decimal(0))
  added=sum((Decimal(str((item.get('_completion_felling_formula') or {}).get(f,{}).get('added',0))) for f in group if contract['quantities'][f] is not None),Decimal(0))
  expected_total=(final-added,added) if added else (final,)
  if terms(cell)!=expected_total:raise ValueError('Snapshot cut total differs')

