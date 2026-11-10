"""Synthetic guards for adopted CSS alignment, with full template comparison."""
from pathlib import Path
import argparse, json, re, shutil, sys, tempfile
import align_published_negotiation_css as repair
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

source=(repo/'scripts/generate_portal.py').read_bytes();block=repair.source_block(source)
refused(lambda:repair.source_block(source+b' '))
sys.path.insert(0,str(repo/'scripts'));import generate_portal as g
expected=g.build_negotiation_html([],empty_note='',repo_root=repo,immediate_status=True)
style=lambda t:re.sub(r'\s+','',re.search(r'<style[^>]*>(.*?)</style>',t,re.S)[1])
for rel,oldhash in repair.PLAN.items():
    current=(repo/rel).read_bytes();result,row=repair.repair_bytes(current,rel,block)
    check(style(result.decode())==style(expected))
    check(repair.repair_bytes(result,rel,block)[0]==result)
    check(repair.repair_bytes(result,rel,block)[1]['status']=='already_aligned')
    newline='\r\n' if b'\r\n' in result else '\n';inserted=block.replace('\n',newline).encode();baseline=result.replace(inserted,b'',1)
    check(repair.sha(baseline.replace(b'\r\n',b'\n'))==oldhash)
    check(repair.repair_bytes(baseline,rel,block)[0]==result)
    strip=lambda b:re.sub(br'<style[^>]*>.*?</style>',b'<style/>',b,flags=re.S)
    check(strip(baseline)==strip(result))
    refused(lambda:repair.repair_bytes(baseline+b' ',rel,block))
    refused(lambda:repair.repair_bytes(baseline,'portal/survey/index.html',block))
    refused(lambda:repair.repair_bytes(result.replace(inserted,inserted+inserted),rel,block))
    refused(lambda:repair.repair_bytes(result.replace(b'#e5e7eb',b'#000000'),rel,block))
    refused(lambda:repair.repair_bytes(result+b' ',rel,block))
with tempfile.TemporaryDirectory(prefix='negotiation-css-',dir=a.temp_root) as td:
    root=Path(td).resolve();fixture=root/'repo';(fixture/'scripts').mkdir(parents=True);shutil.copyfile(repo/'scripts/generate_portal.py',fixture/'scripts/generate_portal.py')
    for rel in repair.PLAN:
        dst=fixture/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/rel,dst)
    original={x.relative_to(fixture).as_posix():repair.sha(x.read_bytes()) for x in fixture.rglob('*') if x.is_file()}
    repair.generate(fixture,root/'one',root/'e1');repair.generate(fixture,root/'two',root/'e2')
    check(all((root/'one'/rel).read_bytes()==(root/'two'/rel).read_bytes() for rel in repair.PLAN))
    check(original=={x.relative_to(fixture).as_posix():repair.sha(x.read_bytes()) for x in fixture.rglob('*') if x.is_file()})
    refused(lambda:repair.generate(fixture,fixture/'bad',root/'e3'))
    refused(lambda:repair.generate(fixture,root/'one',root/'e3'))
print(json.dumps({'synthetic_and_public_fixture_checks':count,'production_writes':0,'body_scripts_config_unchanged':True,'current_generator_css_exact':True}))
