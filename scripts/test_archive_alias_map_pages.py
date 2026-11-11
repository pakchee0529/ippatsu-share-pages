"""Public/synthetic contract tests for the independent immutable-alias map route."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import archive_alias_map_pages as route
from archive_map_contract import parse_page, verify_rendered


class AliasMapTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(Path(route.__file__).with_name('archive_alias_maps.json').read_text('utf-8'))
        self.maps = route.load_maps()
        self.cases = [{'date':day,'management_no':key,'label':view.label} for day,views in self.maps.items() for key,view in views.items()]

    def rejects(self, mutate):
        document = copy.deepcopy(self.document)
        mutate(document)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'input.json'; p.write_text(json.dumps(document),'utf-8')
            with self.assertRaises((ValueError, TypeError)):
                route.load_maps(p)

    def test_exact_roundtrip(self):
        for day, views in self.maps.items():
            body = route.render_map_page(day, views)
            verify_rendered(body, day, views)
            self.assertEqual(parse_page(body, day), views)
            self.assertNotIn('data-final-ledger-identity', body)
            self.assertNotIn('clearance_html', body)
            self.assertNotIn('<table', body)
            self.assertIn('数量・実績・現場条件は復元していません', body)

    def test_reject_wrong_source(self):
        self.rejects(lambda d:d['days'][0].update(source_blob='0'*40))

    def test_reject_wrong_date(self):
        self.rejects(lambda d:d['days'][0].update(date='261107'))

    def test_reject_missing_day(self):
        self.rejects(lambda d:d['days'].pop())

    def test_reject_duplicate_day(self):
        self.rejects(lambda d:d['days'].append(d['days'][0]))

    def test_reject_duplicate_case(self):
        self.rejects(lambda d:d['days'][0]['cases'].append(d['days'][0]['cases'][0]))

    def test_reject_unapproved_fields(self):
        for field in ['reference_href','receipt','quantity','case_uuid','internal_note']:
            with self.subTest(field=field):
                self.rejects(lambda d:d['days'][0]['cases'][0].update({field:'unexpected'}))

    def test_reject_url_injection(self):
        for value in ['javascript:alert(1)','https://evil.example/maps?q=1,2','//www.google.com/maps','https://www.google.com@evil.example/maps','https://www.google.com:443/maps','https://www.google.com/maps#bad','https://www.google.com/maps\n?q=1,2']:
            with self.subTest(value=value):
                self.rejects(lambda d:d['days'][0]['cases'][0].update(single_url=value))

    def test_reject_bad_coordinates(self):
        for value in [None,['pole',True,135],['pole',float('nan'),135],['pole',0,0],['pole','34',135]]:
            with self.subTest(value=value):
                self.rejects(lambda d:d['days'][0]['cases'][0].update(start=value))

    def test_reject_html_in_names(self):
        self.rejects(lambda d:d['days'][0]['cases'][0].update(label='<img src=x>'))
        self.rejects(lambda d:d['days'][0]['cases'][0].update(start=['<img src=x>',34,135]))

    def test_bind_exact_catalog(self):
        self.assertEqual(route.bind_maps(self.maps,self.cases),self.maps)
        for mutate in [lambda c:c.pop(),lambda c:c.append(c[0]),lambda c:c[0].update(label='wrong full span'),lambda c:c[0].update(date='261107'),lambda c:c[0].update(management_no='99999999')]:
            cases=copy.deepcopy(self.cases);mutate(cases)
            with self.assertRaises(ValueError):route.bind_maps(self.maps,cases)

    def test_fixed_route_only(self):
        self.assertEqual(route.reference_href('261104'),'/ippatsu-share-pages/portal/archive/261104/map.html')
        for day in ['../261104','https://evil.example','261107']:
            with self.assertRaises(ValueError):route.reference_href(day)

    def test_writes_only_selected_new_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            alias=root/'portal/archive/261104/index.html';alias.parent.mkdir(parents=True);alias.write_bytes(b'immutable alias')
            result=route.write_map_pages(root,self.maps,'261104')
            self.assertEqual(result,['portal/archive/261104/map.html'])
            self.assertEqual(alias.read_bytes(),b'immutable alias')
            first=(root/result[0]).read_bytes();route.write_map_pages(root,self.maps,'261104')
            self.assertEqual(first,(root/result[0]).read_bytes())
            self.assertEqual(len(list(root.rglob('map.html'))),1)

    def test_reject_projection_tampering(self):
        for field,value in [('single_url','https://www.google.com/maps?q=34,135&tracking=1'),('representative',['changed',34,135]),('start',['changed',34,135]),('label','changed full span')]:
            with self.subTest(field=field):
                self.rejects(lambda d:d['days'][0]['cases'][0].update({field:value}))

    def test_preflight_conflict_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bad=root/'portal/archive/261105/map.html'
            bad.parent.mkdir(parents=True);bad.write_bytes(b'previous independent file')
            with self.assertRaises(ValueError):route.write_map_pages(root,self.maps)
            self.assertFalse((root/'portal/archive/261104/map.html').exists())
            self.assertEqual(bad.read_bytes(),b'previous independent file')

    def test_programmatic_unreviewed_projection(self):
        from dataclasses import replace
        maps=copy.deepcopy(self.maps);key=next(iter(maps['261105']))
        maps['261105'][key]=replace(maps['261105'][key],single_url='https://www.google.com/maps?q=34,135')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):route.write_map_pages(Path(tmp),maps)
            self.assertEqual(list(Path(tmp).rglob('map.html')),[])

    def test_reparse_detection(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(Path,'is_symlink',return_value=True):
                with self.assertRaises(ValueError):route.write_map_pages(Path(tmp),self.maps)
            self.assertEqual(list(Path(tmp).rglob('map.html')),[])

    def test_verify_preinstalled_map_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);route.write_map_pages(root,self.maps)
            before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
            refs=route.validate_repo_maps(root,self.maps)
            self.assertEqual(refs,{day:route.reference_href(day) for day in self.maps})
            self.assertEqual(before,{p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_missing_preinstalled_map_rejected_without_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(ValueError,'missing'):route.validate_repo_maps(root,self.maps)
            self.assertEqual(list(root.rglob('*')),[])

    def test_conflicting_preinstalled_map_rejected_readonly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);route.write_map_pages(root,self.maps)
            p=root/'portal/archive/261105/map.html';p.write_bytes(p.read_bytes()+b' ')
            before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with self.assertRaisesRegex(ValueError,'changed'):route.validate_repo_maps(root,self.maps)
            self.assertEqual(before,{p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
