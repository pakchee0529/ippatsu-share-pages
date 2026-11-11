"""Regression coverage for date-scoped completion archive manifest count sync.

Run: python scripts/test_completion_archive_scope.py
Optional: --generator path/to/generate_portal.py --work-root temporary/test/root
Uses synthetic data only. No network, publication, database, or GUI launch.
"""
from pathlib import Path
import argparse, ast, copy, importlib.util, json, os, sys, tempfile, types, unittest
sys.dont_write_bytecode=True
parser=argparse.ArgumentParser();parser.add_argument('--generator',type=Path,default=Path(__file__).with_name('generate_portal.py'));parser.add_argument('--work-root',type=Path);args,remaining=parser.parse_known_args()
sys.path.insert(0,str(args.generator.parent))
spec=importlib.util.spec_from_file_location('scope_test_generator',args.generator);g=importlib.util.module_from_spec(spec);sys.modules[spec.name]=g;spec.loader.exec_module(g)

class ArchiveManifestScopeTests(unittest.TestCase):
    def setUp(self):
        if args.work_root:args.work_root.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=args.work_root);self.root=Path(self.temp.name);(self.root/'portal').mkdir();self.path=self.root/'portal/archive_manifest.json'
        self.original={'version':3,'metadata':{'keep':True},'entries':[
            {'date':'261029','item_count':1,'completed_count':1,'incomplete_count':0,'planned_incomplete_count':0,'title':'Untouched 1件','extra':{'items':[0,None,False]}},
            {'date':'261105','item_count':99,'completed_count':99,'incomplete_count':0,'title':'Other 99件'},
            {'date':'261110','item_count':99,'completed_count':99,'incomplete_count':0,'title':'Target 99件','extra':'retain'},
            {'date':'bad','item_count':99},None]}
        self.path.write_text(json.dumps(self.original),'utf8');self.calls=[]
        self.old={n:getattr(g,n) for n in ['_prefer_export_derived_manifest_counts','load_archive_public_items','_planned_incomplete_count_for_date']}
        g._prefer_export_derived_manifest_counts=lambda:True
        def load(root,day):
            self.calls.append(day)
            statuses={'261029':['completed'],'261105':['incomplete'],'261110':['completed','completed','incomplete']}[day]
            return [types.SimpleNamespace(completion_status=x) for x in statuses],''
        g.load_archive_public_items=load;g._planned_incomplete_count_for_date=lambda root,day:1 if day=='261110' else 0
    def tearDown(self):
        for n,v in self.old.items():setattr(g,n,v)
        self.temp.cleanup()
    def read(self):return json.loads(self.path.read_text('utf8'))
    def test_target_counts_and_other_entries_fully_preserved(self):
        self.assertEqual(g.sync_archive_manifest_counts_from_completion_export(self.root,only_date='261110'),['261110'])
        actual=self.read();self.assertEqual(self.calls,['261110']);self.assertEqual(actual['entries'][:2],self.original['entries'][:2]);self.assertEqual(actual['entries'][3:],self.original['entries'][3:]);self.assertEqual(actual['metadata'],self.original['metadata'])
        target=actual['entries'][2];self.assertEqual((target['item_count'],target['completed_count'],target['incomplete_count'],target['planned_incomplete_count']),(3,2,1,1));self.assertEqual(target['extra'],'retain');self.assertEqual(target['title'],'Target 3件')
    def test_repeat_is_byte_identical(self):
        g.sync_archive_manifest_counts_from_completion_export(self.root,only_date='261110');before=self.path.read_bytes();self.assertEqual(g.sync_archive_manifest_counts_from_completion_export(self.root,only_date='261110'),[]);self.assertEqual(self.path.read_bytes(),before)
    def test_unscoped_legacy_sync_still_updates_all_dates(self):
        self.assertEqual(g.sync_archive_manifest_counts_from_completion_export(self.root),['261029','261105','261110']);self.assertEqual(self.calls,['261029','261105','261110']);self.assertNotIn('planned_incomplete_count',self.read()['entries'][0]);self.assertEqual(self.read()['entries'][1]['incomplete_count'],1)
    def test_unknown_date_does_not_read_or_write_other_dates(self):
        before=self.path.read_bytes();self.assertEqual(g.sync_archive_manifest_counts_from_completion_export(self.root,only_date='261231'),[]);self.assertEqual(self.calls,[]);self.assertEqual(self.path.read_bytes(),before)
    def test_missing_or_broken_target_export_does_not_write(self):
        g.load_archive_public_items=lambda root,day:(None,'invalid input');before=self.path.read_bytes();self.assertEqual(g.sync_archive_manifest_counts_from_completion_export(self.root,only_date='261110'),[]);self.assertEqual(self.path.read_bytes(),before)
    def test_broken_manifest_does_not_write(self):
        self.path.write_bytes(b'{broken');self.assertEqual(g.sync_archive_manifest_counts_from_completion_export(self.root,only_date='261110'),[]);self.assertEqual(self.path.read_bytes(),b'{broken');self.assertEqual(self.calls,[])
    def test_no_explicit_export_keeps_legacy_noop(self):
        g._prefer_export_derived_manifest_counts=lambda:False;before=self.path.read_bytes();self.assertEqual(g.sync_archive_manifest_counts_from_completion_export(self.root,only_date='261110'),[]);self.assertEqual(self.path.read_bytes(),before);self.assertEqual(self.calls,[])
    def test_actual_main_routes_full_share_and_completion_scopes(self):
        # Stop immediately after count-sync dispatch, before rendering or external reads.
        from unittest.mock import patch
        (self.root/'scripts').mkdir();(self.root/'share').mkdir();fake=self.root/'scripts/generate_portal.py';fake.write_text('# synthetic marker','utf8')
        company='--company-repo-root' in args.generator.read_text('utf8')
        class Synced(Exception):pass
        for mode,expected in [('full',None),('share-update',None),('completion-archive','261110')]:
            observed=[]
            def stop(root,**kwargs):
                observed.append((root,kwargs));raise Synced()
            argv=['generate_portal.py','--mode',mode,'--date','261110']
            if company:argv+=['--company-repo-root',str(self.root)]
            with patch.object(g,'__file__',str(fake)),patch.object(sys,'argv',argv),patch.object(g,'_configure_stdio_encoding',lambda:None),patch.object(g,'load_portal_dotenv',lambda root:None),patch.object(g,'_print_completion_reports_root_info',lambda *a,**kw:0),patch.object(g,'inject_share_detail_edit_into_share_pages',lambda root:None),patch.object(g,'load_archive_manifest_entries',lambda root:[]),patch.object(g,'prepare_archive_maps',return_value={}),patch.object(g,'sync_archive_manifest_counts_from_completion_export',stop):
                with self.assertRaises(Synced):g.main()
            self.assertEqual(observed,[(self.root,{'only_date':expected})])
    def test_main_passes_completion_only_date(self):
        tree=ast.parse(args.generator.read_text('utf8'));main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        calls=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='sync_archive_manifest_counts_from_completion_export']
        self.assertEqual(len(calls),1);self.assertEqual([(k.arg,ast.dump(k.value)) for k in calls[0].keywords],[('only_date',"Name(id='completion_date', ctx=Load())")])
        assignment=next(n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='completion_date' for t in n.targets))
        self.assertIsInstance(assignment.value,ast.IfExp);self.assertEqual(ast.unparse(assignment.value),'target_date if mode == PORTAL_MODE_COMPLETION_ARCHIVE else None')

if __name__=='__main__':unittest.main(argv=[sys.argv[0],*remaining])
