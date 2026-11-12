"""Public map-only provenance and synthetic negative tests. No business exports or DB."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import archive_map_contract as c
import generate_portal as g

REPO=Path(__file__).resolve().parents[1]
DATA=Path(c.__file__).with_name('archive_map_availability.json').read_bytes().replace(b'\r\n',b'\n')
DOCUMENT=json.loads(DATA)


def source(key,view,**fields):
    values=dict(management_no=key,label=view.label,map_url='',start_lat='',start_lng='',end_lat='',end_lng='',lat='',lng='')
    values.update(fields)
    return SimpleNamespace(**values)


def map_fixture(day, views):
    # Synthetic map-only DOM, not the business renderer or the date-bound alias route.
    from html import escape
    cards=[];points=[]
    for key,view in views.items():
        assert view.start is None and view.end is None
        cards.append('<article class="card"><h2 class="card-title">'+escape(view.label)+'</h2><p class="item-mgmt">'+escape(key)+'</p>'+g._archive_single_map_button(view)+g._share_disabled_two_map_button()+'</article>')
        if view.representative:
            points.append({'management_no':key,'name':view.label,'lat':view.representative[1],'lng':view.representative[2]})
    return '<!doctype html><title>'+day+' · アーカイブ詳細</title>'+''.join(cards)+'<div id="share-map"></div><script>var POINTS = '+json.dumps(points,ensure_ascii=False)+';</script>'


class AvailabilityTests(unittest.TestCase):
    def fixture(self,index=0):
        row=DOCUMENT['entries'][index];day=row['date'];key=row['management_no']
        text=(REPO/row['evidence']['path']).read_text('utf8');view=c.parse_page(text,day)[key]
        return row,day,key,text,view,{key:view}
    def contract(self,day,prior):return c.load_map_availability(day,[prior])
    def resolve(self,day,prior,items,gps=None,availability=True):
        proof=self.contract(day,prior) if availability else None
        return c.resolve(items,gps or {},[prior],g,availability=proof,date=day)
    def assert_rejected_document(self,mutate):
        doc=copy.deepcopy(DOCUMENT);mutate(doc);raw=json.dumps(doc,ensure_ascii=False).encode()
        with patch.object(c,'_AVAILABILITY_SHA256_LF',hashlib.sha256(raw).hexdigest()):
            with self.assertRaises((ValueError,TypeError,KeyError)):c._availability_entries(raw)
    def test_pinned_contract_and_public_provenance(self):
        self.assertEqual(hashlib.sha256(DATA).hexdigest(),c._AVAILABILITY_SHA256_LF)
        self.assertEqual(len(c._availability_entries(DATA)),3)
        for row in DOCUMENT['entries']:
            proof=row['evidence']
            try:raw=subprocess.check_output(['git','show',proof['commit']+':'+proof['path']],cwd=REPO,stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:self.skipTest('Pinned public history not available; no network fallback')
            self.assertEqual(hashlib.sha256(raw).hexdigest(),proof['html_sha256'])
            self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),proof['blob_sha1'])
            view=c.parse_page(raw.decode('utf8'),row['date'])[row['management_no']]
            self.assertEqual(c.map_projection_sha256(row['date'],row['management_no'],view),proof['map_projection_sha256'])
            self.assertEqual([r for r in c._MAP_ROLES if not c._published_map_roles(view)[r]],row['unavailable_roles'])
    def test_all_three_keep_unknown_roles_and_repeat_with_gps_candidates(self):
        for i in range(3):
            row,day,key,text,view,prior=self.fixture(i);items=[source(key,view)]
            with patch.object(g,'_share_split_span_label',return_value=('TEST1','TEST2')),patch.object(g,'_share_complete_span_end_label',return_value='TEST2'),patch.object(g,'_share_resolve_gps_pole_label',side_effect=lambda name,gps:name if name in gps else None):
                gps={'TEST1':(34.1,135.1),'TEST2':(34.2,135.2)}
                after=self.resolve(day,prior,items,gps);again=self.resolve(day,after,items,gps)
                self.assertEqual(c._published_map_roles(after[key]),c._published_map_roles(view))
                self.assertEqual(after,again)
                with self.assertRaisesRegex(ValueError,'Unverified archive map role addition'):self.resolve(day,prior,items,gps,False)
            rendered=map_fixture(day,after)
            c.verify_rendered(rendered,day,after)
            c.verify_map_availability(rendered,day,self.contract(day,prior))
            self.assertEqual(c.parse_page(rendered,day),after)
    def test_known_single_url_literal_is_preserved(self):
        row,day,key,text,view,prior=self.fixture(0)
        got=self.resolve(day,prior,[source(key,view)])[key]
        self.assertEqual(got.single_url,view.single_url);self.assertTrue(got.single_url)
        self.assertIsNone(got.representative)
    def test_explicit_source_cannot_silently_end_unknown_contract(self):
        values={'start':{'start_lat':'34.1','start_lng':'135.1'},'end':{'end_lat':'34.2','end_lng':'135.2'},'representative':{'lat':'34.15','lng':'135.15'},'single_url':{'map_url':'https://www.google.com/maps?q=34.1,135.1'}}
        for i in range(3):
            row,day,key,text,view,prior=self.fixture(i)
            for role in row['unavailable_roles']:
                with self.subTest(day=day,role=role),self.assertRaisesRegex(ValueError,'Explicit source contradicts unavailable map role'):
                    self.resolve(day,prior,[source(key,view,**values[role])])
    def test_baseline_and_input_identity_label_must_match(self):
        row,day,key,text,view,prior=self.fixture()
        for changed in [{}, {'99999999':view},{key:replace(view,label=view.label+' ')}, {key:replace(view,single_url=view.single_url+'&changed=1')}]:
            with self.subTest(changed=changed),self.assertRaises(ValueError):self.contract(day,changed)
        with self.assertRaises(ValueError):self.resolve(day,prior,[source(key,view,label=view.label+' ')])
    def test_known_baseline_role_cannot_be_hidden(self):
        for i in range(3):
            row,day,key,text,view,prior=self.fixture(i)
            for role in row['unavailable_roles']:
                value='https://www.google.com/maps?q=34.1,135.1' if role=='single_url' else (view.label,34.1,135.1)
                changed=replace(view,**{role:value})
                # A single internal endpoint is not published. Supply a pair to test a newly enabled map.
                if role in ('start','end'):changed=replace(changed,start=(view.label,34.1,135.1),end=(view.label,34.2,135.2))
                with self.subTest(day=day,role=role),self.assertRaises(ValueError):self.contract(day,{key:changed})
    def test_date_binding_and_baseline_required(self):
        row,day,key,text,view,prior=self.fixture();proof=self.contract(day,prior)
        with self.assertRaises(ValueError):c.resolve([source(key,view)],{},[prior],g,availability=proof,date='261111')
        with self.assertRaises(ValueError):c.load_map_availability(day,[])
        with self.assertRaises(ValueError):c.resolve([source(key,view)],{},[],g,availability=proof,date=day)
    def test_contract_bytes_tampered_or_cached_bytes_are_rejected(self):
        row,day,key,text,view,prior=self.fixture()
        with self.assertRaises(ValueError):c._availability_entries(DATA+b' ')
        with patch.object(c,'__verified_availability_bytes__',DATA+b' ',create=True):
            with self.assertRaises(ValueError):self.contract(day,prior)
    def test_missing_same_directory_contract_has_no_fallback(self):
        row,day,key,text,view,prior=self.fixture()
        with tempfile.TemporaryDirectory() as tmp,patch.object(c,'__file__',str(Path(tmp)/'archive_map_contract.py')):
            with self.assertRaisesRegex(ValueError,'missing or unsafe'):self.contract(day,prior)
    def test_captured_verified_bytes_do_not_reread_changed_disk_json(self):
        row,day,key,text,view,prior=self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            local=Path(tmp)/'archive_map_availability.json'
            local.write_bytes(DATA+b' changed after capture')
            with patch.object(c,'__file__',str(Path(tmp)/'archive_map_contract.py')),patch.object(c,'__verified_availability_bytes__',DATA,create=True):
                proof=self.contract(day,prior)
                self.assertEqual(proof.data,DATA)
                c.verify_map_availability(text,day,proof)
            with patch.object(c,'__file__',str(Path(tmp)/'archive_map_contract.py')):
                with self.assertRaises(ValueError):self.contract(day,prior)
    def test_missing_contract_stops_unaffected_date_without_fallback(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(c,'__file__',str(Path(tmp)/'archive_map_contract.py')):
            with self.assertRaisesRegex(ValueError,'missing or unsafe'):c.load_map_availability('261111',[])
    def test_contract_structure_is_strict_even_for_new_pinned_bytes(self):
        mutations=[lambda d:d.update(schema='wrong'),lambda d:d.update(extra='unexpected'),lambda d:d.update(entries=[]),lambda d:d['entries'].append(copy.deepcopy(d['entries'][0])),lambda d:d['entries'][0].update(date='260631'),lambda d:d['entries'][0].update(management_no='bad'),lambda d:d['entries'][0].update(label='bad\nlabel'),lambda d:d['entries'][0].update(unavailable_roles=['unknown']),lambda d:d['entries'][0].update(unavailable_roles=['start','start']),lambda d:d['entries'][0].update(extra=True),lambda d:d['entries'][0]['evidence'].update(path='other/index.html'),lambda d:d['entries'][0]['evidence'].update(html_sha256='bad')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):self.assert_rejected_document(mutate)
    def test_duplicate_json_keys_rejected(self):
        raw=DATA.replace(b'"schema":',b'"schema":"archive-map-availability/v1","schema":',1)
        with patch.object(c,'_AVAILABILITY_SHA256_LF',hashlib.sha256(raw).hexdigest()):
            with self.assertRaisesRegex(ValueError,'Duplicate'):c._availability_entries(raw)
    def test_map_projection_hash_mismatch_is_rejected(self):
        row,day,key,text,view,prior=self.fixture();doc=copy.deepcopy(DOCUMENT);doc['entries'][0]['evidence']['map_projection_sha256']='0'*64;raw=json.dumps(doc,ensure_ascii=False).encode()
        with patch.object(c,'_AVAILABILITY_SHA256_LF',hashlib.sha256(raw).hexdigest()):
            with self.assertRaisesRegex(ValueError,'projection changed'):c.resolve([source(key,view)],{},[prior],g,availability=c.MapAvailability(day,raw),date=day)
    def test_nonmap_changes_do_not_change_map_contract(self):
        row,day,key,text,view,prior=self.fixture();changed='<!-- non-map metadata fixture -->\n'+text
        actual=c.parse_page(changed,day);proof=c.load_map_availability(day,[actual]);c.verify_map_availability(changed,day,proof)
        self.assertEqual(c.map_projection_sha256(day,key,actual[key]),row['evidence']['map_projection_sha256'])
    def test_output_unknown_roles_are_independently_verified(self):
        row,day,key,text,view,prior=self.fixture(2);proof=self.contract(day,prior)
        bad={key:replace(view,single_url='https://www.google.com/maps?q=34.1,135.1',representative=(view.label,34.1,135.1))}
        rendered=map_fixture(day,bad)
        with self.assertRaises(ValueError):c.verify_map_availability(rendered,day,proof)
    def test_crlf_contract_is_canonically_equivalent(self):
        self.assertEqual(c._availability_entries(DATA),c._availability_entries(DATA.replace(b'\n',b'\r\n')))


if __name__=='__main__':unittest.main()
