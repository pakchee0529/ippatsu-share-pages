"""An empty moved-away date is not current; archived files remain archived."""
from pathlib import Path
import json,tempfile
from generate_portal import _build_portal_top_entries
with tempfile.TemporaryDirectory(prefix='weekly-top-') as name:
    root=Path(name)
    for day,body in [('261026','<main></main>'),('261027','<article class="card"><h2 class="card-title">合成1～2</h2></article>'),('260728','<article class="card"><h2 class="card-title">履歴1～2</h2></article>')]:
        f=root/'share'/day/'index.html';f.parent.mkdir(parents=True,exist_ok=True);f.write_text(body,'utf-8')
    manifest=root/'portal/archive_manifest.json';manifest.parent.mkdir(parents=True,exist_ok=True)
    manifest.write_text(json.dumps({'entries':[{'date':'260728','title':'履歴','item_count':1,'completed_count':1,'incomplete_count':0,'href':'./260728/'}]}),'utf-8')
    entries=_build_portal_top_entries(root,portal_min_date='260101')
    assert [x[0] for x in entries]==['261027'],entries
print(json.dumps({'passed':3,'empty_day_excluded':True,'archive_preserved':True,'active_day_retained':True}))
