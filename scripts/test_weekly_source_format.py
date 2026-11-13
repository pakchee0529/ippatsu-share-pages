"""Semantic and fail-closed acceptance for the isolated weekly format revision."""
import argparse,hashlib,json,re,sys,unittest,tempfile,shutil
from pathlib import Path
from collections import Counter
from generate_weekly_source_format import DAYS,source,extract
from apply_saved_ledger_views import FIELDS,CODES,validate_asset_generation
import weekly_readonly_guard as guard

parser=argparse.ArgumentParser()
parser.add_argument('--source-repo',type=Path,required=True)
parser.add_argument('--output-root',type=Path,required=True)
parser.add_argument('--repeat-a',type=Path,required=True)
parser.add_argument('--repeat-b',type=Path,required=True)
if __name__ == '__main__':
    args,sys.argv[1:]=parser.parse_known_args()
else:
    args=argparse.Namespace(source_repo=None,output_root=None,repeat_a=None,repeat_b=None)

@unittest.skipIf(args.output_root is None, 'Requires explicit isolated acceptance roots')
class WeeklyFormat(unittest.TestCase):
    root=args.output_root
    repo=args.source_repo
    def test_repeat(self):
        a=args.repeat_a;b=args.repeat_b
        for file in a.rglob('*'):
            if file.is_file():self.assertEqual(file.read_bytes(),(b/file.relative_to(a)).read_bytes())
    def test_source_projection(self):
        states=Counter()
        for day,n in DAYS.items():
            original=extract(source(self.repo,f'share/{day}/index.html'),FIELDS)
            share=(self.root/f'share/{day}/index.html').read_text()
            self.assertEqual(re.findall(r'data-management-no-key="(\d+)"',share),[e['cs'] for e in original])
            for field in FIELDS:
                old=[q for e in original for q in e['quantities'] if q['field']==field]
                matches=re.findall(r'<td data-quantity-field="'+field+r'" data-evidence-state="([^"]+)">(.*?)</td>',share)
                self.assertEqual(matches,[(q['state'],q['text']) for q in old])
            for folder in ['daily','instructions']:
                t=(self.root/f'share/{day}/{folder}/index.html').read_text()
                c=json.loads(re.search(r'<script id="weekly-source-config" type="application/json">(.*?)</script>',t,re.S)[1])
                self.assertEqual([x['cs'] for x in c['cases']],[x['cs'] for x in original])
                for before,after in zip(original,c['cases']):
                    self.assertEqual(before['geo'],after['geo']);self.assertEqual(before['mapLink'],after['mapLink']);self.assertEqual(before['notes'],after['notes'])
                    self.assertEqual(before['quantities'],[{k:v for k,v in q.items() if k!='code'} for q in after['quantities']])
                    if before['conditions']:self.assertEqual(before['conditions'],after['conditions'])
            for e in original:states.update(q['state'] for q in e['quantities'])
            self.assertEqual(share.count('class="card-head"'),n);self.assertEqual(share.count('class="card-actions"'),n)
            self.assertEqual(share.count('class="instr-table instr-cut"'),n)
            # Whole-map representative points are preserved, separately from endpoints.
            self.assertEqual(json.loads(re.search(r'var POINTS = (\[.*?\]);',share,re.S)[1]),json.loads(re.search(r'var POINTS = (\[.*?\]);',source(self.repo,f'share/{day}/index.html'),re.S)[1]))
        self.assertEqual(states['nonapplicable_candidate'],108)
        print('Source quantity states:',dict(states))
    def test_integrity(self):
        accepted=guard.manifest()
        self.assertEqual(len(accepted),19)
        for rel,digest in accepted.items():
            self.assertEqual(hashlib.sha256((self.root/rel).read_bytes()).hexdigest(),digest)
            if rel.endswith('.html'):
                text=(self.root/rel).read_text();self.assertEqual(guard.text_path(text),rel)
                with self.assertRaises(ValueError):guard.text_path(text+'changed')
                with self.assertRaises(ValueError):guard.text_path(text,'999999')
                with self.assertRaises(ValueError):guard.text_path(source(self.repo,rel))
        guard.validate_top_sources(self.root,list(DAYS))
        validate_asset_generation(self.root)
    def test_missing_and_changed_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for rel in guard.manifest():
                target=root/rel;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(self.root/rel,target)
            for rel in guard.manifest():
                target=root/rel;data=target.read_bytes()
                target.write_bytes(data+b'changed')
                with self.assertRaises(ValueError):guard.validate_top_sources(root,list(DAYS))
                target.unlink()
                with self.assertRaises(ValueError):guard.validate_top_sources(root,list(DAYS))
                target.write_bytes(data)

    def test_print_asset_scope_and_static_maps(self):
        css='portal/shared-ledger/weekly-source-print.css'
        self.assertIn(css,guard.manifest())
        for day,n in DAYS.items():
            for suffix in ['index.html','daily/index.html','instructions/index.html']:
                text=(self.root/f'share/{day}/{suffix}').read_text()
                self.assertEqual(text.count('weekly-source-print.css?v=20261113-print-r1'),1)
            text=(self.root/f'share/{day}/index.html').read_text()
            ids=re.findall(r'\bid="([^"]+)"',text)
            self.assertEqual(len(ids),len(set(ids)))
            for i in range(n):
                for key in [f'two-geo-{i}',f'two-wrap-{i}',f'share-two-map-{i}']:
                    self.assertIn(key,ids)
            old=source(self.repo,f'share/{day}/index.html')
            for ext in ['css','js']:
                url='https://unpkg.com/leaflet@1.9.4/dist/leaflet.'+ext
                pattern=re.escape(url)+r'"\s+integrity="([^"]+)"'
                self.assertEqual(re.search(pattern,text)[1],re.search(pattern,old)[1])
        for file in (self.repo/'share').rglob('*.html'):
            if file.relative_to(self.repo).as_posix() not in guard.manifest():
                self.assertNotIn('weekly-source-print.css',file.read_text())

    def test_top(self):
        text=(self.root/'portal/index.html').read_text()
        self.assertEqual(guard.top_link_failures(text,list(DAYS)),[])
        for day in DAYS:
            self.assertTrue(guard.top_link_failures(text.replace(f'../share/{day}/','missing/'),list(DAYS)))
            bad=text.replace(f'href="../share/{day}/"',f'href="../share/{day}/"><a href="../share/{day}/daily/"')
            self.assertTrue(guard.top_link_failures(bad,list(DAYS)))
    def test_scope(self):
        allowed=set(guard.manifest())|{'portal/index.html','scripts/weekly_readonly_outputs.json'}
        for f in self.repo.rglob('*'):
            rel=f.relative_to(self.repo).as_posix()
            if not f.is_file() or '.git/' in rel or '__pycache__/' in rel or rel in allowed:continue
            # Isolated source scripts were copied before this test was added.
            if rel=='scripts/test_weekly_source_format.py':continue
            self.assertEqual(f.read_bytes(),(self.root/rel).read_bytes(),rel)

if __name__=='__main__':unittest.main()
