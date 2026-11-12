"""Synthetic offline regression suite. Never uses production exports or DBs."""
import copy
from dataclasses import fields, MISSING, replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
import generate_portal as g
import archive_map_contract as c

DAY='261111'


def item(key='51403131', label='試験1～2', **kwargs):
    values={f.name:'—' for f in fields(g.ArchivePublicItem) if f.default is MISSING}
    values.update(management_no=key,label=label,completion_status='completed',map_url='',
                  start_lat='',start_lng='',end_lat='',end_lng='',branch_cut_total=0,root_cut_total=0)
    values.update(kwargs)
    return g.ArchivePublicItem(**values)


def planned(key='51403130',label='試験2～3',**kwargs):
    return g.PlannedIncompleteItem(key,key,label,'時間切れ','未施工','true','なし','fixture','',**kwargs)


def render(items, pending=(), views=None, gps=None):
    return g.build_archive_detail_html(g.ManifestEntry(DAY),items,'',list(pending),map_views=views,gps=gps)


def sample():
    a=item(start_lat='34.1',start_lng='135.1',end_lat='34.2',end_lng='135.2')
    b=planned(start_lat='34.2',start_lng='135.2',end_lat='34.3',end_lng='135.3')
    return [a],[b]


class Maps(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.old=(g._ARCHIVE_GPS_JSON,g._ARCHIVE_MAP_BASELINE_ROOT,g._COMPLETION_REPORTS_ROOT_OVERRIDE,g._DATA_ROOT_OVERRIDE)
        g._ARCHIVE_GPS_JSON=None;g._ARCHIVE_MAP_BASELINE_ROOT=None;g._DATA_ROOT_OVERRIDE=None
    def tearDown(self):
        g._ARCHIVE_GPS_JSON,g._ARCHIVE_MAP_BASELINE_ROOT,g._COMPLETION_REPORTS_ROOT_OVERRIDE,g._DATA_ROOT_OVERRIDE=self.old
        self.tmp.cleanup()
    def baseline(self,html,base='share'):
        path=self.root/base/DAY/'index.html';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(html);return path
    def test_mixed_baseline_missing_gps_and_zero_export(self):
        a,b=sample();before=render(a,b);self.baseline(before)
        a=[replace(a[0],start_lat='0',start_lng='0',end_lat='0',end_lng='0')]
        b=[replace(b[0],start_lat='0',start_lng='0',end_lat='0',end_lng='0')]
        original=copy.deepcopy((a,b))
        views=g.prepare_archive_maps(self.root,DAY,a,b)
        after=render(a,b,views);c.verify_rendered(after,DAY,views)
        c.verify_preserved(after,DAY,[c.parse_page(before,DAY)])
        self.assertEqual((a,b),original);self.assertEqual(after,before)
    def test_repeat_retired_archive_preserves_maps(self):
        a,b=sample();before=render(a,b);self.baseline(before,'portal/archive')
        blank=[item()];pending=[planned()]
        views=g.prepare_archive_maps(self.root,DAY,blank,pending)
        self.assertEqual(render(blank,pending,views),before)
    def test_source_without_baseline_and_no_maps(self):
        for a,b in [sample(),([item()],[]),([],[planned()]),([],[])]:
            views=g.prepare_archive_maps(self.root,DAY,a,b)
            c.verify_rendered(render(a,b,views),DAY,views)
        parsed=c.parse_page(render([item()]),DAY)['51403131']
        self.assertFalse(parsed.single_url);self.assertIsNone(parsed.representative)
    def test_start_and_end_only_roles(self):
        for gps,role in [({'試験1':(34.1,135.1)},'start'),({'試験2':(34.2,135.2)},'end')]:
            views=c.resolve([item()],gps,[],g);v=views['51403131']
            self.assertIsNotNone(getattr(v,role));self.assertIsNone(getattr(v,'end' if role=='start' else 'start'))
            c.verify_rendered(render([item()],views=views),DAY,views)
            self.assertNotIn('data-two-open ',render([item()],views=views))
            old=g._archive_resolved_item_points(item(),gps)
            self.assertIsNotNone(old[0 if role=='start' else 1]);self.assertIsNone(old[1 if role=='start' else 0])
    def test_plain_coordinates_completed_and_planned(self):
        for a,b in [([item(lat='34.1',lng='135.1')],[]),([],[planned(lat='34.1',lng='135.1')])]:
            views=c.resolve(a+b,{},[],g);v=next(iter(views.values()))
            self.assertIsNone(v.start);self.assertIsNone(v.end);self.assertIsNotNone(v.representative)
            c.verify_rendered(render(a,b,views),DAY,views)
    def test_plain_conflict(self):
        with self.assertRaises(ValueError):c.resolve([item(lat='34',lng='135',end_lat='35',end_lng='136')],{},[],g)
    def test_rounded_single_independent_precise_endpoints(self):
        a,b=sample();views=c.resolve(a+b,{},[],g);key=a[0].management_no
        views[key]=replace(views[key],single_url='https://www.google.com/maps?q=34.20,135.20')
        html=render(a,b,views);baseline=c.parse_page(html,DAY)
        recovered=c.resolve([item(),planned()],{},[baseline],g)
        self.assertEqual(recovered[key].single_url,views[key].single_url)
        c.verify_rendered(render([item()],[planned()],recovered),DAY,recovered)
    def test_wrong_date_and_metadata(self):
        a,b=sample();html=render(a,b)
        for bad in [html.replace('261111 ·','261112 ·'),html.replace('<article class="card"','<article data-date="261112" class="card"',1),html.replace('<article class="card"','<article data-management-no="99999999" class="card"',1)]:
            with self.assertRaises(ValueError):c.parse_page(bad,DAY)
    def test_duplicate_and_mismatched_identity(self):
        a,b=sample();baseline=c.parse_page(render(a,b),DAY)
        for inputs in [[item(),item()], [item(key='99999999'),planned()], [item(label='別名1～2'),planned()], [item()]]:
            with self.assertRaises(ValueError):c.resolve(inputs,{},[baseline],g)
        html=render(a,b);card=c.CARD.search(html)[0]
        with self.assertRaises(ValueError):c.parse_page(html.replace(card,card+card),DAY)
    def test_source_gps_and_prior_conflicts(self):
        a,b=sample();baseline=c.parse_page(render(a,b),DAY)
        with self.assertRaises(ValueError):c.resolve([replace(a[0],start_lat='35'),b[0]],{},[baseline],g)
        with self.assertRaises(ValueError):c.resolve([item(),planned()],{'試験1':(35,135)},[baseline],g)
        with self.assertRaises(ValueError):c.resolve(a+b,{'試験1':(35,135)},[],g)
    def test_tampered_controls_and_every_point(self):
        a,b=sample();views=c.resolve(a+b,{},[],g);html=render(a,b,views)
        tampered=[html.replace('?q=34.2,135.2','?q=35.2,135.2',1),
            html.replace('"lat": 34.1','"lat": 35.1',1),
            html.replace('"lat": 34.2','"lat": 35.2',1),
            html.replace('"lat": 34.3','"lat": 35.3'),
            html.replace('id="share-map"','id="not-map"'),
            html.replace('data-two-json="two-geo-0"','data-two-json="missing"'),
            html.replace('data-two-open ','disabled data-two-open ',1),
            html.replace('"management_no": "51403131"','"management_no": "51403130"')]
        for bad in tampered:
            with self.subTest(bad=bad[-100:]):
                with self.assertRaises(ValueError):c.verify_rendered(bad,DAY,views)
        # Same aggregate point count cannot hide a swap of endpoint payloads.
        bad=html.replace('"lat": 34.1','"lat": 34.9').replace('"lat": 34.3','"lat": 34.1').replace('"lat": 34.9','"lat": 34.3')
        with self.assertRaises(ValueError):c.verify_rendered(bad,DAY,views)
    def test_guard_rejects_missing_all_maps_with_zero_export(self):
        a,b=sample();prior=c.parse_page(render(a,b),DAY)
        with self.assertRaises(ValueError):c.verify_preserved(render([item()],[planned()]),DAY,[prior])
    def test_explicit_missing_or_broken_baseline(self):
        g._ARCHIVE_MAP_BASELINE_ROOT=self.root/'external'
        with self.assertRaises(ValueError):g.prepare_archive_maps(self.root,DAY,[item()],[])
        path=self.baseline('{broken','external')
        with self.assertRaises(ValueError):g.prepare_archive_maps(self.root,DAY,[item()],[])
    def test_explicit_gps_paths_and_replaced_content(self):
        p=self.root/'a.json';q=self.root/'b.json'
        p.write_text('{"試験1":"34.1,135.1"}');q.write_text('{"試験1":"35.1,136.1"}')
        self.assertNotEqual(g.load_gps_poles(self.root,gps_path=p),g.load_gps_poles(self.root,gps_path=q))
        p.write_text(q.read_text());self.assertEqual(g.load_gps_poles(self.root,gps_path=p),g.load_gps_poles(self.root,gps_path=q))
        g._ARCHIVE_GPS_JSON=p
        with patch.object(g,'__file__','/unrelated/isolated/scripts/generate_portal.py'):
            views=g.prepare_archive_maps(self.root,DAY,[item()],[])
        self.assertEqual(views['51403131'].start[1:],(35.1,136.1))
        p.write_text('{bad')
        with self.assertRaises(ValueError):g.prepare_archive_maps(self.root,DAY,[item()],[])
        g._ARCHIVE_GPS_JSON=self.root/'missing.json'
        with self.assertRaises(FileNotFoundError):g.prepare_archive_maps(self.root,DAY,[item()],[])
    def test_loader_projects_plain_without_mutating_export(self):
        g._COMPLETION_REPORTS_ROOT_OVERRIDE=self.root
        doc={'date':DAY,'items':[{'completion_status':'completed','source_item':{'management_no':'51403131','label':'試験1','lat':34.1,'lng':135.1}}],
             'planned_but_incomplete':[{'management_no':'51403130','label':'試験2','source_item':{'lat':34.2,'lng':135.2}}]}
        p=self.root/(DAY+'.json');p.write_text(json.dumps(doc));before=p.read_bytes()
        a,_=g.load_archive_public_items(self.root,DAY);b=g.load_archive_planned_incomplete(self.root,DAY)
        self.assertEqual(a[0].lat,'34.1');self.assertEqual(b[0].lat,'34.2');self.assertEqual(p.read_bytes(),before)
    def test_default_writer_uses_prior_share_and_keeps_other_files(self):
        a,b=sample();before=render(a,b);self.baseline(before)
        sentinel=self.root/'portal/archive/261110/saved-forms/keep.html';sentinel.parent.mkdir(parents=True);sentinel.write_text('keep')
        with patch.object(g,'load_archive_public_items',return_value=([item()],'')),patch.object(g,'load_archive_planned_incomplete',return_value=[planned()]),patch.object(g,'_check_archive_items_vs_export_summary'):
            g.write_archive_detail_pages(self.root,[g.ManifestEntry(DAY)])
            out=self.root/'portal/archive'/DAY/'index.html';first=out.read_bytes()
            g.write_archive_detail_pages(self.root,[g.ManifestEntry(DAY)])
            self.assertEqual(out.read_bytes(),first)
        c.verify_preserved(out.read_text(),DAY,[c.parse_page(before,DAY)])
        self.assertEqual(sentinel.read_text(),'keep')
    def test_projection_failure_has_no_partial_detail_writes(self):
        self.baseline(render([item(key='99999999')]))
        with patch.object(g,'load_archive_public_items',return_value=([item()],'')),patch.object(g,'load_archive_planned_incomplete',return_value=[]),patch.object(g,'_check_archive_items_vs_export_summary'):
            with self.assertRaises(ValueError):g.write_archive_detail_pages(self.root,[g.ManifestEntry(DAY)])
        self.assertFalse((self.root/'portal/archive').exists())
    def test_main_default_completion_preflight_before_count_sync(self):
        self.baseline(render([item(key='99999999')]))
        fake=self.root/'scripts/generate_portal.py';fake.parent.mkdir()
        argv=['generate_portal.py','--mode','completion-archive','--date',DAY]
        with patch.object(g,'__file__',str(fake)),patch.object(sys,'argv',argv),patch.object(g,'load_portal_dotenv'),patch.object(g,'_print_completion_reports_root_info',return_value=0),patch.object(g,'load_archive_manifest_entries',return_value=[g.ManifestEntry(DAY)]),patch.object(g,'load_archive_public_items',return_value=([item()],'')),patch.object(g,'load_archive_planned_incomplete',return_value=[]),patch.object(g,'sync_archive_manifest_counts_from_completion_export') as sync:
            with self.assertRaises(ValueError):g.main()
            sync.assert_not_called()

    def test_existing_data_root_gps_without_new_flags(self):
        company=self.root/'company'; data=company/'data'; data.mkdir(parents=True)
        path=company/'app/resources/data/GPS.json';path.parent.mkdir(parents=True)
        path.write_text('{"試験1":"34.1,135.1", "試験2":"34.2,135.2"}')
        staged=self.root/'unrelated/public-candidate';staged.mkdir(parents=True)
        g._DATA_ROOT_OVERRIDE=data
        views=g.prepare_archive_maps(staged,DAY,[item()],[])
        self.assertEqual(views['51403131'].end[1:],(34.2,135.2))
        c.verify_rendered(render([item()],views=views),DAY,views)
        # Missing company GPS must not fall back to a different sibling tree.
        path.unlink()
        with patch.object(g,'_share_gps_pole_map',side_effect=AssertionError('wrong tree')):
            self.assertIsNone(g.prepare_archive_maps(staged,DAY,[item()],[])['51403131'].representative)
    def test_public_legacy_spaced_ids_and_fixed_aliases(self):
        repo=Path(__file__).resolve().parents[1]
        page=(repo/'portal/archive/261102/index.html').read_text()
        parsed=c.parse_page(page,'261102');self.assertIn('51400869',parsed)
        for day in ('261104','261105','261106'):
            text=(repo/'portal/archive'/day/'index.html').read_text()
            self.assertTrue(c.is_fixed_form_alias(text))
            self.assertEqual(len(c.baseline_pages(repo,day)),int((repo/'share'/day/'index.html').is_file()))
            with self.assertRaises(ValueError):c.baseline_pages(repo,day,repo/'portal/archive')
        spaced=item(key='514 03131');v=c.resolve([spaced],{},[],g)
        c.verify_rendered(render([spaced],views=v),DAY,v)
        with self.assertRaises(ValueError):c.resolve([spaced,item()],{},[],g)
    def test_url_equivalence_preserves_original(self):
        original='https://www.google.com/maps?q=34.20%2C135.20&foo=bar'
        other='https://www.google.com/maps?foo=bar&q=34.2,135.2'
        self.assertTrue(c.same_url(original,other))
        a=item(map_url=other);prior={'51403131':c.MapView(a.label,single_url=original,representative=(a.label,34.2,135.2))}
        v=c.resolve([a],{},[prior],g);self.assertEqual(v['51403131'].single_url,original)
        with self.assertRaises(ValueError):c.resolve([replace(a,map_url=other.replace('34.2','35.2'))],{},[prior],g)
        self.assertFalse(c.same_url('https://maps.app.goo.gl/a','https://maps.app.goo.gl/b'))
    def test_first_completion_not_in_manifest_is_preflighted(self):
        self.baseline(render([item(key='99999999')]))
        fake=self.root/'scripts/generate_portal.py';fake.parent.mkdir()
        with patch.object(g,'__file__',str(fake)),patch.object(sys,'argv',['generate_portal.py','--mode','completion-archive','--date',DAY]),patch.object(g,'load_portal_dotenv'),patch.object(g,'_print_completion_reports_root_info',return_value=0),patch.object(g,'load_archive_manifest_entries',return_value=[]),patch.object(g,'load_archive_public_items',return_value=([item()],'')),patch.object(g,'load_archive_planned_incomplete',return_value=[]),patch.object(g,'sync_archive_manifest_counts_from_completion_export') as sync:
            with self.assertRaises(ValueError):g.main()
            sync.assert_not_called()

    def test_independent_verifier_rejects_identity_bound_source_drift(self):
        import verify_archive_pages as verifier
        (self.root/'portal/archive').mkdir(parents=True)
        (self.root/'portal/archive/index.html').write_text('fixture')
        (self.root/'portal/archive_manifest.json').write_text(json.dumps({'entries':[{'date':DAY,'href':'./'+DAY+'/'}]}))
        a=item(start_lat='34.1',start_lng='135.1',end_lat='34.2',end_lng='135.2')
        self.baseline(render([a]),'portal/archive')
        exports=self.root/'exports';exports.mkdir()
        src={'management_no':a.management_no,'label':a.label,'start_lat':34.1,'start_lng':135.1,'end_lat':34.2,'end_lng':135.2}
        doc={'date':DAY,'items':[{'completion_status':'completed','source_item':src}],'planned_but_incomplete':[]}
        path=exports/(DAY+'.json');path.write_text(json.dumps(doc))
        row=verifier.ArchiveTopRow(date_key=DAY,main=a.label,href='./'+DAY+'/',search=a.label)
        with patch.object(verifier,'parse_archive_top',return_value=[row]):
            self.assertEqual(verifier.verify(self.root,exports,{DAY}),[])
            src['end_lat']=35.2;path.write_text(json.dumps(doc))
            self.assertTrue(any('source map contract' in e for e in verifier.verify(self.root,exports,{DAY})))
    def test_independent_verifier_detects_lost_prior_maps_without_export(self):
        import verify_archive_pages as verifier
        a,b=sample();self.baseline(render(a,b));self.baseline(render([item()],[planned()]),'portal/archive')
        (self.root/'portal/archive/index.html').write_text('fixture')
        (self.root/'portal/archive_manifest.json').write_text(json.dumps({'entries':[{'date':DAY,'href':'./'+DAY+'/'}]}))
        row=verifier.ArchiveTopRow(date_key=DAY,main='fixture',href='./'+DAY+'/')
        with patch.object(verifier,'parse_archive_top',return_value=[row]):
            errors=verifier.verify(self.root,None,{DAY})
        self.assertTrue(any('map preservation' in e for e in errors))
    def test_export_date_and_row_source_identity_mismatch(self):
        source={'management_no':'51403131','label':'試験1'}
        for doc in [{'date':'261112','items':[{'source_item':source}]},
                    {'date':DAY,'items':[{'management_no':'51403130','source_item':source}]}]:
            with self.assertRaises(ValueError):c.export_map_items(doc,DAY)

    def test_pinned_public_261111_map_only_evidence(self):
        import hashlib, subprocess
        from types import SimpleNamespace
        repo=Path(__file__).resolve().parents[1]
        try:
            old=subprocess.check_output(['git','show','5d77ca1521f190d1d364cd4d0db1edba41fe09ce:share/261111/index.html'],cwd=repo,stderr=subprocess.DEVNULL)
            broken=subprocess.check_output(['git','show','1ed1df2b43cdd122a4dfd4bbe36cef6c13891bec:portal/archive/261111/index.html'],cwd=repo,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            self.skipTest('Pinned public history unavailable in this checkout; no network fallback')
        self.assertEqual(hashlib.sha256(old).hexdigest(),'4686b95b8c550abb8709b533353d1100972cfbef21062a1fd9a5897c507d1591')
        baseline=c.parse_page(old.decode(),'261111')
        # Only public identity/map objects. No status, quantity, revision or export fabrication.
        objects=[SimpleNamespace(management_no=k,label=v.label,map_url='',start_lat='',start_lng='',end_lat='',end_lng='',lat='',lng='') for k,v in baseline.items()]
        self.assertEqual(c.resolve(objects,{},[baseline],g),baseline)
        with self.assertRaises(ValueError):c.verify_preserved(broken.decode(),'261111',[baseline])

    def test_disabled_single_and_duplicate_dom_ids_are_rejected(self):
        a,b=sample();views=c.resolve(a+b,{},[],g);html=render(a,b,views)
        mutants=[html.replace('<a class="btn btn-map btn-map-single"','<a disabled class="btn btn-map btn-map-single"',1),
                 html.replace('<a class="btn btn-map btn-map-single"','<a aria-disabled="true" class="btn btn-map btn-map-single"',1),
                 html.replace('<a class="btn btn-map btn-map-single"','<a class="btn btn-map btn-map-single btn-map-disabled"',1),
                 html.replace('id="share-map"','id="share-map"',1).replace('</body>','<div id="share-map"></div></body>'),
                 html.replace('</body>','<div id="two-geo-0"></div></body>'),
                 html.replace('data-two-open ','aria-disabled="true" data-two-open ',1)]
        for html in mutants:
            with self.assertRaises(ValueError):c.verify_rendered(html,DAY,views)


    def test_existing_midpoint_representative_is_not_an_endpoint(self):
        a,b=sample();prior=c.resolve(a+b,{},[],g)
        prior[a[0].management_no]=replace(prior[a[0].management_no],representative=(a[0].label,34.15,135.15))
        recovered=c.resolve(a+b,{},[prior],g)
        self.assertEqual(recovered,prior)
        c.verify_rendered(render(a,b,recovered),DAY,recovered)
        c.verify_preserved(render(a,b,recovered),DAY,[prior])
    def test_existing_midpoint_and_matching_plain_preserve_endpoint(self):
        a=item(start_lat='34.1',start_lng='135.1',end_lat='34.2',end_lng='135.2',lat='34.15',lng='135.15')
        old=c.MapView(a.label,(a.label,34.1,135.1),(a.label,34.2,135.2),'https://www.google.com/maps?q=34.2,135.2',(a.label,34.15,135.15))
        self.assertEqual(c.resolve([a],{},[{a.management_no:old}],g)[a.management_no],old)
    def test_existing_midpoint_still_rejects_plain_and_endpoint_conflicts(self):
        a=item(start_lat='34.1',start_lng='135.1',end_lat='34.2',end_lng='135.2')
        old=c.MapView(a.label,(a.label,34.1,135.1),(a.label,34.2,135.2),'https://www.google.com/maps?q=34.2,135.2',(a.label,34.15,135.15))
        for bad,gps in [(replace(a,lat='34.17',lng='135.17'),{}),(replace(a,end_lat='34.3'),{}),(a,{'試験2':(34.3,135.3)})]:
            with self.subTest(bad=bad,gps=gps),self.assertRaises(ValueError):c.resolve([bad],gps,[{a.management_no:old}],g)
    def test_conflicting_prior_midpoint_is_still_rejected(self):
        a=item();old=c.MapView(a.label,single_url='https://www.google.com/maps?q=34.15,135.15',representative=(a.label,34.15,135.15))
        changed=replace(old,representative=(a.label,34.16,135.16))
        with self.assertRaises(ValueError):c.resolve([a],{},[{a.management_no:old},{a.management_no:changed}],g)
    def test_midpoint_prepare_and_repeat_writer_preserve_prior_maps(self):
        a,b=sample();prior=c.resolve(a+b,{},[],g)
        prior[a[0].management_no]=replace(prior[a[0].management_no],representative=(a[0].label,34.15,135.15))
        before=render(a,b,prior);self.baseline(before)
        blank=[item()];pending=[planned()]
        with patch.object(g,'load_archive_public_items',return_value=(blank,'')),patch.object(g,'load_archive_planned_incomplete',return_value=pending),patch.object(g,'_check_archive_items_vs_export_summary'):
            g.write_archive_detail_pages(self.root,[g.ManifestEntry(DAY)])
            out=self.root/'portal/archive'/DAY/'index.html';first=out.read_bytes()
            g.write_archive_detail_pages(self.root,[g.ManifestEntry(DAY)])
            self.assertEqual(first,out.read_bytes())
        c.verify_preserved(out.read_text(),DAY,[c.parse_page(before,DAY)])


    def test_prior_single_only_cannot_invent_overall_point(self):
        a=item(map_url='https://www.google.com/maps?q=34.2,135.2')
        prior={a.management_no:c.MapView(a.label,single_url=a.map_url)}
        with self.assertRaisesRegex(ValueError,'Unverified archive map role addition.*representative'):
            c.resolve([a],{},[prior],g)
    def test_prior_overall_only_cannot_invent_single_link(self):
        a=item();prior={a.management_no:c.MapView(a.label,representative=(a.label,34.2,135.2))}
        with self.assertRaisesRegex(ValueError,'Unverified archive map role addition.*single_url'):
            c.resolve([a],{},[prior],g)
    def test_unknown_prior_blocks_gps_source_plain_and_url_additions(self):
        a=item();prior={a.management_no:c.MapView(a.label)}
        examples=[(a,{'試験1':(34.1,135.1),'試験2':(34.2,135.2)}),
                  (replace(a,start_lat='34.1',start_lng='135.1',end_lat='34.2',end_lng='135.2'),{}),
                  (replace(a,lat='34.15',lng='135.15'),{}),
                  (replace(a,map_url='https://www.google.com/maps?q=34.2,135.2'),{})]
        for inputs,gps in examples:
            saved=copy.deepcopy((inputs,gps,prior))
            with self.subTest(inputs=inputs,gps=gps),self.assertRaisesRegex(ValueError,'Unverified archive map role addition'):
                c.resolve([inputs],gps,[prior],g)
            self.assertEqual((inputs,gps,prior),saved)
    def test_initial_gps_projection_without_baseline_is_unchanged(self):
        a=item();gps={'試験1':(34.1,135.1),'試験2':(34.2,135.2)}
        got=c.resolve([a],gps,[],g)[a.management_no]
        self.assertTrue(all(c._published_map_roles(got).values()))
    def test_one_endpoint_repeat_matches_exact_html_and_keeps_two_disabled(self):
        a=item()
        for gps in ({'試験1':(34.1,135.1)},{'試験2':(34.2,135.2)}):
            first=c.resolve([a],gps,[],g);html=render([a],views=first)
            prior=c.parse_page(html,DAY);again=c.resolve([a],gps,[prior],g)
            self.assertEqual(render([a],views=again),html)
            self.assertNotIn('data-two-open ',html)
            self.assertEqual(c._published_map_roles(again[a.management_no]),c._published_map_roles(prior[a.management_no]))
            with self.assertRaisesRegex(ValueError,'Unverified archive map role addition.*start,end'):
                c.resolve([a],{'試験1':(34.1,135.1),'試験2':(34.2,135.2)},[prior],g)
    def test_existing_baselines_can_supply_complementary_verified_roles(self):
        a=item();url='https://www.google.com/maps?q=34.2,135.2';rep=(a.label,34.2,135.2)
        first={a.management_no:c.MapView(a.label,single_url=url)}
        second={a.management_no:c.MapView(a.label,representative=rep)}
        got=c.resolve([a],{},[first,second],g)[a.management_no]
        self.assertEqual(got.single_url,url);self.assertEqual(got.representative,rep)
    def test_unknown_prior_stops_writer_before_any_archive_output(self):
        a=item();self.baseline(render([a]));gps=self.root/'gps.json'
        gps.write_text(json.dumps({'試験1':'34.1,135.1','試験2':'34.2,135.2'}),encoding='utf8');g._ARCHIVE_GPS_JSON=gps
        with patch.object(g,'load_archive_public_items',return_value=([a],'')),patch.object(g,'load_archive_planned_incomplete',return_value=[]),patch.object(g,'_check_archive_items_vs_export_summary'):
            with self.assertRaisesRegex(ValueError,'Unverified archive map role addition'):
                g.write_archive_detail_pages(self.root,[g.ManifestEntry(DAY)])
        self.assertFalse((self.root/'portal/archive').exists())
    def test_unknown_prior_stops_main_before_count_sync(self):
        a=item();self.baseline(render([a]));gps=self.root/'gps.json'
        gps.write_text(json.dumps({'試験1':'34.1,135.1','試験2':'34.2,135.2'}),encoding='utf8');g._ARCHIVE_GPS_JSON=gps
        fake=self.root/'scripts/generate_portal.py';fake.parent.mkdir()
        with patch.object(g,'__file__',str(fake)),patch.object(sys,'argv',['generate_portal.py','--mode','completion-archive','--date',DAY,'--archive-gps-json',str(gps)]),patch.object(g,'load_portal_dotenv'),patch.object(g,'_print_completion_reports_root_info',return_value=0),patch.object(g,'load_archive_manifest_entries',return_value=[g.ManifestEntry(DAY)]),patch.object(g,'load_archive_public_items',return_value=([a],'')),patch.object(g,'load_archive_planned_incomplete',return_value=[]),patch.object(g,'sync_archive_manifest_counts_from_completion_export') as sync:
            with self.assertRaisesRegex(ValueError,'Unverified archive map role addition'):g.main()
            sync.assert_not_called()


if __name__=='__main__':unittest.main()
