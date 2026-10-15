"""Preserve explicit known/unknown HTML quantities in local JSON-input links."""
from html.parser import HTMLParser
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
import re
QUERY_FIELDS={**{f'E{n}':key for n,key in zip((10,20,30,40,50,60),('branch_cut_under_10','branch_cut_10_20','branch_cut_20_30','branch_cut_30_40','branch_cut_40_50','branch_cut_over_50'))},**{f'N{n}':key for n,key in zip((10,20,30,40,50,60),('root_cut_under_10','root_cut_10_20','root_cut_20_30','root_cut_30_40','root_cut_40_50','root_cut_over_50'))},'TK':'bamboo_count','SB':'bush_area_m2','TR':'vine_count'}

# Units belong to the field's presentation, never to its numeric value.
# Counts require integers; only area accepts a decimal fraction.
def _confirmed_quantity_text(field, raw):
 if field == 'bush_area_m2':
  pattern = r'([0-9]+(?:\.[0-9]+)?)(?:㎡|m²)?'
 elif field == 'vine_count':
  pattern = r'([0-9]+)(?:箇所)?'
 else:
  pattern = r'([0-9]+)(?:本)?'
 match = re.fullmatch(pattern, raw)
 if match is None:raise ValueError('Invalid confirmed quantity text')
 return match.group(1)

def html_quantities(card):
 class Parser(HTMLParser):
  def __init__(self):super().__init__();self.active=None;self.data=[];self.values={}
  def handle_starttag(self,tag,attrs):
   a=dict(attrs);field=a.get('data-quantity-field');state=a.get('data-quantity-state')
   field={'brush_area_m2':'bush_area_m2','vine_locations':'vine_count'}.get(field,field)
   if field in QUERY_FIELDS.values() and state in ('unknown','value','confirmed'):
    self.active=(tag,field,state);self.data=[]
  def handle_data(self,text):
   if self.active:self.data.append(text)
  def handle_endtag(self,tag):
   if not self.active or tag!=self.active[0]:return
   _,field,state=self.active;raw=''.join(self.data).strip()
   value=None
   if state!='unknown':
    value=_confirmed_quantity_text(field,raw)
   if field in self.values and self.values[field]!=value:raise ValueError('Conflicting quantity confirmation states')
   self.values[field]=value;self.active=None;self.data=[]
 p=Parser();p.feed(card)
 return {key:p.values[field] for key,field in QUERY_FIELDS.items() if field in p.values}
def preserve_quantity_query(href,card):
 if not href:return href
 values=html_quantities(card)
 if not values:return href # Legacy cards retain their existing contract.
 parts=urlsplit(href);params=parse_qsl(parts.query,keep_blank_values=True)
 params=[(key,values.get(key,value)) for key,value in params if not(key in values and values[key] is None)]
 present={key for key,value in params}
 params.extend((key,value) for key,value in values.items() if value is not None and key not in present)
 return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(params),parts.fragment))
