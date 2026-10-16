"""Display-only contract. Never infer confirmation from a rendered number."""
from __future__ import annotations
from pathlib import Path
from html import unescape
import re,os,tempfile
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
from html import escape
import json

FIELDS=tuple(f'{k}_cut_{b}' for k in ('branch','root') for b in ('under_10','10_20','20_30','30_40','40_50','over_50'))+('brush_area_m2','bamboo_count','vine_locations')
TABLE=re.compile(r'<table\b[^>]*class="[^"]*\binstr-(?:cut|other)\b[^"]*"[^>]*>.*?</table>',re.S)
CELL=re.compile(r'(<td\b[^>]*>)(.*?)(</td>)',re.S)
def attr(tag,name):
 m=re.search(r'\b'+re.escape(name)+r'\s*=\s*([\"\x27])(.*?)\1',tag,re.S)
 return unescape(m[2]) if m else None
def _numeric(text):
 plain=unescape(text).strip()
 m=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(?:本|箇所|m²|㎡)?',plain)
 if not m:raise ValueError('Confirmed quantity must be a finite nonnegative number')
 return Decimal(m[1])
def _zero(inner):
 if '<' in inner:raise ValueError('Unknown quantity has unsupported nested markup')
 unit=re.search(r'(m²|㎡|本|箇所)\s*$',unescape(inner))
 return '0'+(unit[1] if unit else '')
def _format(value):return format(value,'f').rstrip('0').rstrip('.') if '.' in format(value,'f') else format(value,'f')
def _table(table):
 seen={}
 def replace(m):
  field,state=attr(m[1],'data-quantity-field'),attr(m[1],'data-quantity-state')
  if field not in FIELDS or state is None:return m[0]
  if state not in {'unknown','confirmed'}:raise ValueError('Invalid explicit quantity state')
  if field in seen:raise ValueError('Duplicate explicit quantity field')
  if state=='unknown':inner=_zero(m[2]);seen[field]=Decimal(0)
  else:inner=m[2];seen[field]=_numeric(inner)
  return m[1]+inner+m[3]
 table=CELL.sub(replace,table)
 # Only a complete, explicit 12-cell cut table can redefine its totals.
 if set(FIELDS[:12])<=set(seen):
  sums=[sum((seen[f] for f in FIELDS[i:i+6]),Decimal(0)) for i in (0,6)]
  total=re.compile(r'(<tr\b[^>]*class="[^"]*\binstr-cut-total\b[^"]*"[^>]*>)(.*?)(</tr>)',re.S)
  def totals(m):
   cells=list(CELL.finditer(m[2]));assert len(cells)==2,'Invalid cut total cells'
   body=m[2]
   for cell,value in reversed(list(zip(cells,sums))):body=body[:cell.start()]+cell[1]+_format(value)+cell[3]+body[cell.end():]
   return m[1]+body+m[3]
  table=total.sub(totals,table)
 return table
def display_html(text):return TABLE.sub(lambda m:_table(m[0]),text)
def validate_display_html(text):
 if display_html(text)!=text:raise ValueError('Quantity display contract violated')
def validate_publish_paths(repo,paths):
 root=Path(repo).resolve()
 for rel in paths:
  p=(root/rel).resolve()
  if not p.is_relative_to(root):raise ValueError('Publish path escaped repository')
  if p.is_file() and p.suffix.lower()=='.html':validate_display_html(p.read_bytes().decode('utf-8'))
def copy_share_html(source,destination):
 source,destination=Path(source),Path(destination)
 data=source.read_bytes();converted=display_html(data.decode('utf-8')).encode('utf-8')
 validate_display_html(converted.decode('utf-8'))
 destination.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(prefix=destination.name+'.',suffix='.tmp',dir=destination.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(converted)
  os.replace(name,destination)
 finally:
  if os.path.exists(name):os.unlink(name)
def source_states(raw):
 states=dict(raw.get('_quantity_html_states') or {})
 for f in FIELDS:
  if f in raw and raw[f] is None:states[f]='unknown'
 for kind,fields in [('branch',FIELDS[:6]),('root',FIELDS[6:12])]:
  values=raw.get(kind+'_cuts')
  if isinstance(values,(list,tuple)):
   for field,value in zip(fields,values):
    if field not in raw and value is None:states[field]='unknown'
 return {f:s for f,s in states.items() if f in FIELDS}
def read_states(tables):
 states={};values={}
 for table in tables:
  for m in CELL.finditer(table):
   field,state=attr(m[1],'data-quantity-field'),attr(m[1],'data-quantity-state')
   if field not in FIELDS or state is None:continue
   if state not in {'unknown','confirmed'} or field in states:raise ValueError('Invalid readback quantity state')
   states[field]=state;values[field]=None if state=='unknown' else float(_numeric(m[2]))
 return states,values
def capture_tables(text):
 # Preserve legacy cells/units/totals verbatim on a subsequent regeneration.
 return [m[0] for m in TABLE.finditer(text)]
def annotate_tables(fragment,states):
 def annotate(m):
  table=m[0];cut='instr-cut' in table.split('>',1)[0]
  order=[x for pair in zip(FIELDS[:6],FIELDS[6:12]) for x in pair] if cut else list(FIELDS[12:])
  cells=list(CELL.finditer(table))
  for i,cell in reversed(list(enumerate(cells[:len(order)]))):
   field=order[i];state=states.get(field)
   if state is None or attr(cell[1],'data-quantity-state') is not None:continue
   if state not in {'unknown','confirmed'}:raise ValueError('Invalid explicit quantity state')
   opening=cell[1][:-1]+f' data-quantity-field="{field}" data-quantity-state="{state}">'
   table=table[:cell.start()]+opening+cell[2]+cell[3]+table[cell.end():]
  return table
 return display_html(TABLE.sub(annotate,fragment))
def restore_tables(fragment,tables):
 originals=list(tables or [])
 if not originals:return fragment
 actual=list(TABLE.finditer(fragment))
 if len(originals)!=len(actual):raise ValueError('Quantity table shape changed on readback')
 for m,prior in reversed(list(zip(actual,originals))):fragment=fragment[:m.start()]+display_html(prior)+fragment[m.end():]
 return fragment

def preserve_ledger_quantities_and_valid_maps(before,after):
 """A display-only ensure must not rewrite existing ledger inputs or valid maps."""
 cards=re.compile(r'<article\b[^>]*class="[^"]*\bcard\b[^"]*"[^>]*>.*?</article>',re.S)
 old=list(cards.finditer(before));new=list(cards.finditer(after))
 if len(old)!=len(new):raise ValueError('Display ensure changed card count')
 names=dict(zip(['E10','E20','E30','E40','E50','E60','N10','N20','N30','N40','N50','N60','SB','TK','TR'],FIELDS))
 anchor=re.compile(r'<a\b[^>]*>',re.S)
 def identity(card):
  m=re.search(r'<p\b[^>]*class="[^"]*\bitem-mgmt\b[^"]*"[^>]*>(.*?)</p>',card,re.S)
  return re.sub(r'\s+','',unescape(m[1])) if m else ''
 def role(href):
  u=urlsplit(href);q=dict(parse_qsl(u.query,keep_blank_values=True))
  if u.path.endswith(('/ledger-input/','/ledger-v2/')):return (u.path.rsplit('/',2)[-2],q.get('edit_plan')=='1')
  return None
 geo=re.compile(r'(<script\s+type="application/json"\s+id="two-geo-\d+"[^>]*>)(.*?)(</script>)',re.S)
 for om,nm in reversed(list(zip(old,new))):
  prior,current=om[0],nm[0]
  if not identity(prior) or identity(prior)!=identity(current):raise ValueError('Display ensure changed card identity')
  states,_=read_states(capture_tables(prior));saved={}
  for a in anchor.finditer(prior):
   href=attr(a[0],'href');key=role(href) if href else None
   if key:
    if key in saved:raise ValueError('Duplicate existing ledger role')
    saved[key]=[(k,v) for k,v in parse_qsl(urlsplit(href).query,keep_blank_values=True) if k in names and states.get(names[k])!='unknown']
  def preserve(a):
   href=attr(a[0],'href');key=role(href) if href else None
   if key is None:return a[0]
   quantity=saved.get(key)
   if quantity is None and key in {('ledger-v2',False),('ledger-input',True)}:quantity=saved.get(('ledger-input',False))
   if quantity is None:return a[0]
   u=urlsplit(href);query=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if k not in names]+quantity
   value=urlunsplit((u.scheme,u.netloc,u.path,urlencode(query),u.fragment))
   return re.sub(r'(\bhref\s*=\s*)([\"\x27]).*?\2',lambda m:m[1]+m[2]+escape(value,quote=True)+m[2],a[0],count=1,flags=re.S)
  current=anchor.sub(preserve,current)
  oldgeo=geo.search(prior)
  if oldgeo:
   try:
    data=json.loads(oldgeo[2]);valid=all(isinstance(data.get(k),dict) and 20<=float(data[k]['lat'])<=46.5 and 122<=float(data[k]['lng'])<=154.5 for k in ('a','b'))
   except (ValueError,TypeError,KeyError):valid=False
   if valid:
    current=geo.sub(lambda m:m[1]+oldgeo[2]+m[3],current,count=1)
  oldmap=next((attr(a[0],'href') for a in anchor.finditer(prior) if 'btn-map-single' in (attr(a[0],'class') or '').split()),None)
  match=re.search(r'[?&]q=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)(?:$|&)',oldmap or '')
  if match and 20<=float(match[1])<=46.5 and 122<=float(match[2])<=154.5:
   def restore_map(a):
    if 'btn-map-single' not in (attr(a[0],'class') or '').split():return a[0]
    return re.sub(r'(\bhref\s*=\s*)([\"\x27]).*?\2',lambda m:m[1]+m[2]+escape(oldmap,quote=True)+m[2],a[0],count=1,flags=re.S)
   current=anchor.sub(restore_map,current)
  after=after[:nm.start()]+current+after[nm.end():]
 return after
