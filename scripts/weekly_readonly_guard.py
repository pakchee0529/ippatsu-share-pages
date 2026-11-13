"""Exact five-day read-only output guard; normal callers retain their original path."""
from pathlib import Path
import json,hashlib,os,tempfile
def manifest():return json.loads((Path(__file__).parent/'weekly_readonly_outputs.json').read_text('utf8'))
def readonly(text):return 'data-provisional-mode="' in text
def text_path(text,date=None):
 digest=hashlib.sha256(text.replace('\r\n','\n').replace('\r','\n').encode()).hexdigest();matches=[r for r,h in manifest().items() if r.endswith('.html') and h==digest]
 if len(matches)!=1:raise ValueError('Readonly output is not an accepted five-day revision')
 rel=matches[0]
 if date is not None and not rel.startswith('share/'+date+'/'):raise ValueError('Readonly day mismatch')
 return rel
def paths(root,items,legacy):
 root=Path(root).resolve()
 for rel in items:
  p=(root/rel).resolve()
  if not p.is_relative_to(root):raise ValueError('Output path escaped root')
  if p.is_file() and p.suffix.lower()=='.html' and (readonly(p.read_text('utf8')) or p.relative_to(root).as_posix() in manifest()):
   wanted=text_path(p.read_text('utf8'))
   if p.relative_to(root).as_posix()!=wanted:raise ValueError('Readonly path/day mismatch')
   if '/261118/' in wanted:
    for asset,h in manifest().items():
     if asset.endswith('.mjs') and hashlib.sha256((root/asset).read_bytes()).hexdigest()!=h:raise ValueError('Readonly asset revision differs')
  elif p.is_file() and p.relative_to(root).as_posix() in manifest():
   if hashlib.sha256(p.read_bytes()).hexdigest()!=manifest()[p.relative_to(root).as_posix()]:raise ValueError('Readonly asset revision differs')
  else:legacy(root,[rel])
def copy(source,destination,legacy):
 source,destination=Path(source),Path(destination);data=source.read_bytes();text=data.decode('utf8')
 protected=[r for r in manifest() if r.endswith('.html') and destination.as_posix().endswith('/'+r)]
 if protected and text_path(text)!=protected[0]:raise ValueError('Protected readonly destination cannot be replaced with normal or unverified content')
 if not readonly(text):return legacy(source,destination)
 rel=text_path(text)
 if not destination.as_posix().endswith('/'+rel):raise ValueError('Readonly destination mismatch')
 destination.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix=destination.name+'.',suffix='.tmp',dir=destination.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data)
  os.replace(name,destination)
 finally:
  if os.path.exists(name):os.unlink(name)
def portal(before,after,top,date,legacy):
 if readonly(after) or 'share/'+date+'/index.html' in manifest():
  try:
   if text_path(after,date)!='share/'+date+'/index.html':raise ValueError('Expected share view')
   return []
  except ValueError as e:return [str(e)]
 if readonly(before):return ['Explicit provisional retirement/adoption plan required']
 return legacy(before,after,top,date)
