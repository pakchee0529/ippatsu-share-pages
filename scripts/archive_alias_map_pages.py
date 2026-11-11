"""Bounded, map-only navigation for the three immutable November ledger aliases.

The reviewed input contains public map evidence only. Never use it to recreate
quantities, completion status, receipts, ledger revisions or saved forms.
"""
from pathlib import Path
from html import escape
from urllib.parse import urlsplit
import json
import re
import hashlib
import stat

from archive_map_contract import MapView, norm, point, same, verify_rendered, CARD, Tags, text_class

APPROVED = {
    '261104': '4b5adf9025c31c556195a892352ce5b8573086c1',
    '261105': 'b1d4056a2fb0475d83bfa761b238423483daa739',
    '261106': 'ab214479711a491e733a39df0e130eff9a1f21b8',
}
# Canonical public map-only projections independently matched to APPROVED blobs.
PROJECTION_SHA256 = {'261104': 'a8f84e74d06827ac908cb047efa910ab72049da86e57cac41278412bba373a71', '261105': '614121df3f1af471fb64ae941b4e30b2a377d7d2d13e4c1a28b85a9bea6996dd', '261106': '4c57af8e91c6ff0403fa4a8643f993f4b9a14d4fbbc4e9297e7d4d17a598e92d'}
MAP_PAGE_SHA256 = {'261104': 'c655061a75107f913a344c3a716fd47b81a2602819f4a2e069bccee37692286f', '261105': '6d3e12c19177e4b6352fb5a11bd22bcface7b2ee3ede539c53491843fef9ea8a', '261106': 'bfaff69107d0ca5cb20507328d24d841fb7176b2f9a812eff1b49e62e7650377'}
BASE = '/ippatsu-share-pages/portal/archive/'


def reference_href(day):
    if day not in APPROVED:
        raise ValueError('Unapproved independent-map date')
    return BASE + day + '/map.html'


def _label(value):
    if not isinstance(value, str) or not value.strip() or any(c in value for c in '<>\x00'):
        raise ValueError('Invalid public map label')
    return value


def _point(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError('Missing or invalid map point')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in value[1:]):
        raise ValueError('Non-numeric map point')
    result = point(_label(value[0]), *value[1:])
    if result is None:
        raise ValueError('Map coordinate out of bounds')
    return result


def load_maps(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name('archive_alias_maps.json')
    document = json.loads(path.read_text('utf-8'))
    if set(document) != {'schema', 'days'} or document['schema'] != 'archive-alias-maps/v1':
        raise ValueError('Invalid alias map schema')
    result = {}
    for day in document['days']:
        if set(day) != {'date', 'source_blob', 'cases'}:
            raise ValueError('Unexpected alias map day fields')
        date = day['date']
        if date not in APPROVED or date in result or day['source_blob'] != APPROVED[date]:
            raise ValueError('Unapproved/duplicate alias map source')
        projection = json.dumps(day['cases'], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        if hashlib.sha256(projection).hexdigest() != PROJECTION_SHA256[date]:
            raise ValueError('Reviewed map-only projection changed: ' + date)
        views = {}
        for row in day['cases']:
            if set(row) != {'management_no', 'label', 'start', 'end', 'single_url', 'representative'}:
                raise ValueError('Unexpected alias map fields')
            number = row['management_no']
            if not isinstance(number, str) or not re.fullmatch(r'[0-9]{8}', number) or number in views:
                raise ValueError('Invalid/duplicate alias map identity')
            url = row['single_url']
            if not isinstance(url, str):
                raise ValueError('Invalid map URL')
            u = urlsplit(url)
            if u.scheme != 'https' or u.netloc != 'www.google.com' or u.path != '/maps' or u.fragment or any(ord(c) < 32 for c in url):
                raise ValueError('Unapproved map URL')
            view = MapView(_label(row['label']), _point(row['start']), _point(row['end']), url, _point(row['representative']))
            if same(view.start, view.end):
                raise ValueError('Non-distinct map endpoints')
            views[number] = view
        if not views:
            raise ValueError('Empty alias map day')
        result[date] = views
    if set(result) != set(APPROVED):
        raise ValueError('Incomplete alias map date set')
    return result


def bind_maps(maps, cases):
    """Bind against freshly rebuilt immutable identities, not editable prior hrefs."""
    for day, views in maps.items():
        rows = [row for row in cases if row['date'] == day]
        by_number = {row['management_no']: row for row in rows}
        if len(rows) != len(by_number) or set(by_number) != set(views):
            raise ValueError('Alias map/catalog identity mismatch: ' + day)
        for number, view in views.items():
            if norm(view.label) != norm(by_number[number]['label']):
                raise ValueError('Alias map/catalog full-span mismatch: ' + number)
    return maps


def validate_repo_maps(repo_root, maps):
    """Read-only verification of preinstalled, reviewed sidecars. Never generate."""
    for day, views in maps.items():
        path = Path(repo_root).absolute() / 'portal/archive' / day / 'map.html'
        _reject_reparse(path)
        if not path.is_file():
            raise ValueError('Reviewed map page missing: ' + day)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != MAP_PAGE_SHA256[day]:
            raise ValueError('Reviewed map page changed: ' + day)
        body = raw.decode('utf-8')
        if f'<title>{day} · アーカイブ詳細</title>' not in body:
            raise ValueError('Map page date mismatch')
        found = {}
        for match in CARD.finditer(body):
            attrs = Tags(match[0]).tags[0][1]
            number = attrs.get('data-management-no', '')
            if not re.fullmatch(r'[0-9]{8}', number) or number in found or attrs.get('data-date') != day:
                raise ValueError('Map page identity/date mismatch')
            found[number] = text_class(match[0], 'card-title')
        if set(found) != set(views) or any(norm(found[key]) != norm(view.label) for key, view in views.items()):
            raise ValueError('Map page full-span identity mismatch')
    return {day: reference_href(day) for day in maps}


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


def render_map_page(day, views):
    import generate_portal as portal
    if day not in APPROVED:
        raise ValueError('Unapproved map output date')
    cards, points = [], []
    for idx, (number, view) in enumerate(views.items()):
        geo = {role: {'name': p[0], 'lat': p[1], 'lng': p[2]} for role, p in [('a', view.start), ('b', view.end)]}
        geo_id = f'alias-two-geo-{idx}'
        cards.append(f'<article class="card" id="map-{number}" data-date="{day}" data-management-no="{number}">'
            f'<h2 class="card-title">{escape(view.label)}</h2><p class="item-mgmt">{number}</p>'
            '<div class="card-actions">' + portal._archive_single_map_button(view)
            + portal._share_two_map_button(geo_id, idx) + '</div>'
            + portal._share_two_map_panel(idx)
            + f'<script type="application/json" id="{geo_id}">{_json(geo)}</script></article>')
        p = view.representative
        points.append({'management_no': number, 'name': view.label, 'lat': p[1], 'lng': p[2]})
    css = '''body{font-family:system-ui,sans-serif;margin:auto;padding:16px;max-width:960px;background:#f8fafc;color:#172033}h1{font-size:1.5rem}.card{background:white;border:1px solid #cbd5e1;border-radius:12px;padding:16px;margin:16px 0}.card-title{font-size:1.1rem}.card-actions{display:flex;gap:10px;flex-wrap:wrap}.btn{display:inline-flex;align-items:center;min-height:44px;padding:0 14px;border:0;border-radius:8px;background:#1d4ed8;color:white;text-decoration:none;font-size:1rem;cursor:pointer}.share-two-map-canvas,#share-map{height:380px;width:100%}.two-map-wrap{margin-top:12px}[hidden]{display:none!important}a{color:#1d4ed8}.notice{padding:12px;background:#eff6ff;border-radius:8px}'''
    js = '''function gmaps(lat,lng){return "https://www.google.com/maps?q="+encodeURIComponent(lat+","+lng);}
var POINTS = ''' + _json(points) + ''';
var map=L.map('share-map',{scrollWheelZoom:false});
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
var bounds=[];POINTS.forEach(function(p){var content=document.createElement('div');var a=document.createElement('a');a.href='#map-'+p.management_no;a.textContent=p.name+' / '+p.management_no;content.appendChild(a);L.marker([p.lat,p.lng]).addTo(map).bindPopup(content);bounds.push([p.lat,p.lng]);});
if(bounds.length)map.fitBounds(bounds,{padding:[30,30],maxZoom:17});
''' + portal.two_map_click_handler_js()
    body = f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{day} · アーカイブ詳細</title><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"><style>' + css + portal.two_map_tooltip_css() + '</style></head><body>'
    body += f'<nav><a href="{BASE}{day}/view.html">保存済み離隔表・指示書へ戻る</a> · <a href="{BASE}">アーカイブ一覧</a></nav><h1>20{day[:2]}年{int(day[2:4])}月{int(day[4:])}日 地図</h1>'
    body += '<p class="notice">当時の公開共有ページから確認できた地図だけを表示しています。数量・実績・現場条件は復元していません。保存済み離隔表・指示書は上のリンクからご確認ください。</p><h2>全体地図</h2><div id="share-map" role="application" aria-label="全体地図"></div>'
    body += ''.join(cards) + '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>' + js + '</script></body></html>'
    verify_rendered(body, day, views)
    return body


def _reject_reparse(path):
    # A staging path must not follow an existing symlink/junction outside its root.
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError('Symlink in map output path')
        if component.exists():
            flags = getattr(component.lstat(), 'st_file_attributes', 0)
            if flags & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
                raise ValueError('Reparse point in map output path')


def preflight_map_pages(output_root, maps, date=None):
    root = Path(output_root).absolute()
    _reject_reparse(root)
    approved = load_maps()
    pending = []
    for day, views in maps.items():
        if day not in approved or views != approved[day]:
            raise ValueError('Unreviewed map output projection')
        if date and date != day:
            continue
        target = root / 'portal/archive' / day / 'map.html'
        _reject_reparse(target)
        body = render_map_page(day, views).encode('utf-8')
        if hashlib.sha256(body).hexdigest() != MAP_PAGE_SHA256[day]:
            raise ValueError('Map renderer differs from reviewed page bytes')
        if target.exists() and (not target.is_file() or target.read_bytes() != body):
            raise ValueError('Refusing to overwrite a different existing map page')
        pending.append((target, body))
    return pending


def write_map_pages(output_root, maps, date=None):
    root = Path(output_root).absolute()
    pending = preflight_map_pages(root, maps, date)
    # Validate and render every selected day before creating any output.
    for target, body in pending:
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            _reject_reparse(target)
            with target.open('xb') as stream:
                stream.write(body)
    return [target.relative_to(root).as_posix() for target, _ in pending]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--date', choices=sorted(APPROVED))
    args = parser.parse_args()
    if args.output_root.resolve() == args.repo_root.resolve() or args.output_root.resolve().is_relative_to(args.repo_root.resolve()):
        raise ValueError('Generate into a separate staging root')
    catalog = json.loads((args.repo_root / 'portal/archive/archive-v2-r1/catalog.json').read_text('utf-8'))
    maps = bind_maps(load_maps(), catalog['cases'])
    print(json.dumps(write_map_pages(args.output_root, maps, args.date)))
