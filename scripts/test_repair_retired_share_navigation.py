"""Synthetic guards for the bounded retired-page navigation adapter."""
from pathlib import Path
import argparse, json, shutil, tempfile, re
import repair_retired_share_navigation as repair
p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--temp-root',type=Path);a=p.parse_args();repo=a.repo_root.resolve();count=0

def check(ok):
    global count
    assert ok
    count+=1

def refused(fn):
    global count
    try:fn()
    except (ValueError,KeyError):count+=1
    else:raise AssertionError('Expected guard rejection')

for rel, expected in repair.PLAN.items():
    _,day,mode,_=rel.split('/');current=(repo/rel).read_bytes()
    old_label='当日の共有ページへ戻る' if mode=='daily' else '共有ページに戻る'
    new_label='当日の完了アーカイブへ' if mode=='daily' else '当日の保存指示書へ'
    href=f'../../../portal/archive/{day}/view.html'+('?document=instructions' if mode=='instructions' else '')
    old=f'<a href="../">{old_label}</a>'.encode();new=f'<a href="{href}">{new_label}</a>'.encode()
    baseline=current.replace(new,old,1) if new in current else current
    check(repair.sha(baseline.replace(b'\r\n',b'\n'))==expected)
    result,record=repair.repair_bytes(baseline,day,mode,expected)
    check(result.replace(new,old,1)==baseline)
    check(repair.config(result.decode())==repair.config(baseline.decode()))
    check(repair.repair_bytes(result,day,mode,expected)[0]==result)
    check(repair.repair_bytes(result,day,mode,expected)[1]['status']=='already_aligned')
    crlf=baseline.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
    check(repair.repair_bytes(crlf,day,mode,expected)[0].replace(new,old,1)==crlf)
    refused(lambda:repair.repair_bytes(baseline+b' ',day,mode,expected))
    refused(lambda:repair.repair_bytes(baseline,day,'wrong-mode',expected))
    refused(lambda:repair.repair_bytes(baseline,'990101',mode,expected))
    refused(lambda:repair.repair_bytes(baseline.replace(old,old+old),day,mode,expected))
    refused(lambda:repair.repair_bytes(baseline.replace(old,b''),day,mode,expected))
    proof=repair.verify_archive(repo,day,record['cases']);check(bool(proof['immutable_sources']))
    refused(lambda:repair.verify_archive(repo,day,record['cases']+['99999999']))
with tempfile.TemporaryDirectory(prefix='retired-navigation-',dir=a.temp_root) as td:
    root=Path(td).resolve();fixture=root/'repo';fixture.mkdir()
    for rel in repair.PLAN:
        dest=fixture/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/rel,dest)
    for day in ('261028','261029'):
        shutil.copytree(repo/'portal/archive'/day,fixture/'portal/archive'/day)
    original={x.relative_to(fixture).as_posix():repair.sha(x.read_bytes()) for x in fixture.rglob('*') if x.is_file()}
    repair.generate(fixture,root/'one',root/'e1');repair.generate(fixture,root/'two',root/'e2')
    check(all((root/'one'/rel).read_bytes()==(root/'two'/rel).read_bytes() for rel in repair.PLAN))
    check(original=={x.relative_to(fixture).as_posix():repair.sha(x.read_bytes()) for x in fixture.rglob('*') if x.is_file()})
    refused(lambda:repair.generate(fixture,fixture/'bad',root/'e3'))
    refused(lambda:repair.generate(fixture,root/'one',root/'e3'))
    target=fixture/'share/261028/index.html';target.write_text('retired index must stay absent')
    refused(lambda:repair.generate(fixture,root/'bad-index',root/'e4'));check(not (root/'bad-index').exists());target.unlink()
    target=fixture/'portal/archive/261028/view.html';original_view=target.read_bytes();target.write_text('missing frozen data')
    refused(lambda:repair.generate(fixture,root/'bad-view',root/'e5'));check(not (root/'bad-view').exists());target.write_bytes(original_view)
    data=json.loads(re.search(r'id="archive-snapshot-data">(.*?)</script>',original_view.decode(),re.S)[1]);source=fixture/data['cases'][0]['daily_source_href'].split('/ippatsu-share-pages/',1)[1];saved=source.read_bytes();source.unlink()
    refused(lambda:repair.generate(fixture,root/'bad-source',root/'e6'));check(not (root/'bad-source').exists());source.write_bytes(saved)
print(json.dumps({'synthetic_and_public_fixture_checks':count,'production_writes':0,'immutable_preserved':True}))
