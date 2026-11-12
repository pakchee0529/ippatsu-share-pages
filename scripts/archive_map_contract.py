"""Identity-bound, map-only archive projection and independent rendered-map guard.

No writes, database access, or business-field reconstruction. Public baselines
are explicit <root>/<YYMMDD>/index.html files; current share/archive pages are
also checked before retirement/replacement. Callers own private event binding.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import json
import math
import re
import unicodedata

Point = tuple[str, float, float]
CARD = re.compile(r'<article\b[^>]*class="[^"]*\bcard\b[^"]*"[^>]*>.*?</article>', re.S)


@dataclass(frozen=True)
class MapView:
    label: str
    start: Point | None = None
    end: Point | None = None
    single_url: str = ''
    representative: Point | None = None


def norm(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).upper()


def identity(raw):
    # Reuse the established company/share-pages management-number contract.
    from generate_portal import management_no_key
    key = management_no_key(raw)
    if not key:
        raise ValueError('Invalid archive map identity')
    return key


def same_url(a, b):
    if a == b:
        return True
    ua, ub = urlsplit(a), urlsplit(b)
    if (ua.scheme, ua.netloc, ua.path, ua.fragment) != (ub.scheme, ub.netloc, ub.path, ub.fragment):
        return False
    qa, qb = parse_qs(ua.query, keep_blank_values=True), parse_qs(ub.query, keep_blank_values=True)
    pa, pb = url_point(a, ''), url_point(b, '')
    qa.pop('q', None); qb.pop('q', None)
    return same(pa, pb) and qa == qb


def is_fixed_form_alias(text):
    return (bool(re.search(r'<title>離隔表</title>', text))
            and not CARD.search(text)
            and bool(re.search(r'<article\b[^>]*class="ledger-view"[^>]*data-management-no=', text))
            and 'data-final-ledger-identity=' in text)


def coord(lat, lng):
    try:
        a, b = float(lat), float(lng)
    except (ValueError, TypeError):
        return None
    return (a, b) if math.isfinite(a) and math.isfinite(b) and 20 <= a <= 46.5 and 122 <= b <= 154.5 else None


def point(name, lat, lng):
    pair = coord(lat, lng)
    return (name, *pair) if pair else None


def same(a, b):
    return a is not None and b is not None and all(abs(x-y) <= 1e-9 for x,y in zip(a[1:], b[1:]))


def safe_url(value):
    u = urlsplit(value)
    if u.scheme not in ('https', 'http') or not u.hostname or u.username or u.password:
        raise ValueError('Invalid archive map URL')
    return value


def url_point(value, label):
    if not value:
        return None
    safe_url(value)
    q = parse_qs(urlsplit(value).query).get('q', [])
    if len(q) != 1 or ',' not in q[0]:
        return None
    return point(label, *q[0].split(',', 1))


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.tags=[]; self.feed(text)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def text_class(block, cls):
    m = re.search(r'<(?P<tag>\w+)\b[^>]*class="(?:[^"]*\s)?'+re.escape(cls)+r'(?:\s[^"]*)?"[^>]*>(.*?)</(?P=tag)>', block, re.S)
    if not m:
        raise ValueError('Archive map card missing '+cls)
    s = re.sub(r'<span\b[^>]*class="[^"]*\bstatus-pill\b[^"]*"[^>]*>.*?</span>', '', m[2], flags=re.S)
    return unescape(re.sub('<[^>]*>', '', s)).strip()


def parse_page(text, date):
    """Parse actual controls and points, rejecting malformed/ambiguous identity."""
    if not re.fullmatch(r'\d{6}', date):
        raise ValueError('Invalid archive map date')
    title = re.search(r'<title>(.*?)</title>', text, re.S)
    expected_titles = {f'{date} · アーカイブ詳細', f'20{date[:2]}年{int(date[2:4])}月{int(date[4:])}日'}
    title_text = unescape(title[1]).strip() if title else ''
    jp = re.fullmatch(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title_text)
    jp_matches = jp and tuple(map(int, jp.groups())) == (2000+int(date[:2]),int(date[2:4]),int(date[4:]))
    if title_text not in expected_titles and not jp_matches:
        raise ValueError('Archive map baseline date/title mismatch: '+date)
    result = {}
    page_ids = [a.get("id") for _, a in Tags(text).tags if a.get("id")]
    for m in CARD.finditer(text):
        block=m[0]; tags=Tags(block).tags; article=tags[0][1]
        key=identity(text_class(block, 'item-mgmt')); label=text_class(block, 'card-title')
        if key in result:
            raise ValueError('Duplicate/invalid archive map identity: '+key)
        if article.get('data-date', date) != date or identity(article.get('data-management-no', key)) != key or identity(article.get('data-management-no-key', key)) != key:
            raise ValueError('Archive map card identity mismatch: '+key)
        singles=[(t,a) for t,a in tags if 'btn-map-single' in a.get('class','').split()]
        twos=[(t,a) for t,a in tags if 'btn-map-two' in a.get('class','').split()]
        if len(singles)!=1 or len(twos)!=1:
            raise ValueError('Archive map controls missing/duplicated: '+key)
        st,sa=singles[0]; tt,ta=twos[0]
        single=safe_url(sa.get('href','')) if st=='a' else ''
        if single and ('disabled' in sa or sa.get('aria-disabled', '').lower() == 'true' or 'btn-map-disabled' in sa.get('class','').split()):
            raise ValueError('Disabled single-map link: '+key)
        if not single and ('disabled' not in sa or 'btn-map-disabled' not in sa.get('class','').split()):
            raise ValueError('Invalid disabled single map: '+key)
        start=end=None
        if 'data-two-open' in ta:
            if tt!='button' or 'disabled' in ta or ta.get('aria-disabled', '').lower() == 'true' or 'btn-map-disabled' in ta.get('class','').split():
                raise ValueError('Invalid enabled two map: '+key)
            ident=ta.get('data-two-json','')
            payloads=re.findall(r'<script\b[^>]*id="'+re.escape(ident)+r'"[^>]*>(.*?)</script>',block,re.S) if ident else []
            ids=[a.get('id') for _,a in tags]
            if len(payloads)!=1 or any(page_ids.count(value)!=1 for value in (ident, ta.get('data-two-wrap'), ta.get('data-two-map'))):
                raise ValueError('Broken two-map references: '+key)
            raw=json.loads(payloads[0]); endpoints=[]
            if not isinstance(raw,dict):raise ValueError('Invalid two-map payload: '+key)
            for role in ('a','b'):
                p=raw.get(role,{})
                if not isinstance(p,dict):raise ValueError('Invalid two-map endpoint: '+key)
                endpoint=point(str(p.get('name','')),p.get('lat'),p.get('lng'))
                if endpoint is None: raise ValueError('Invalid two-map coordinate: '+key)
                endpoints.append(endpoint)
            start,end=endpoints
            if same(start,end):raise ValueError('Non-distinct two-map endpoints: '+key)
        elif 'disabled' not in ta or 'btn-map-disabled' not in ta.get('class','').split():
            raise ValueError('Invalid disabled two map: '+key)
        result[key]=MapView(label,start,end,single)
    matches=list(re.finditer(r'\bvar\s+(?:POINTS|points)\s*=\s*', text))
    if len(matches)>1:raise ValueError('Multiple archive map point arrays')
    points=[]
    if matches:
        points,_=json.JSONDecoder().raw_decode(text[matches[0].end():].lstrip())
        if not isinstance(points,list):raise ValueError('Archive points must be array')
    seen=set()
    for p in points:
        if not isinstance(p,dict):raise ValueError('Invalid overall-map point')
        key=identity(p.get('management_no','')); label=str(p.get('name',''))
        if key not in result or key in seen or norm(label)!=norm(result[key].label):
            raise ValueError('Archive overall-map identity mismatch: '+key)
        rep=point(label,p.get('lat'),p.get('lng'))
        if rep is None:raise ValueError('Invalid overall-map coordinate: '+key)
        result[key]=replace(result[key],representative=rep);seen.add(key)
    if points and page_ids.count('share-map')!=1:
        raise ValueError('Archive overall-map container missing')
    return result


def merge_point(a,b,key,role):
    if a and b and not same(a,b):
        raise ValueError(f'Conflicting archive map {role}: {key}')
    return a or b


def merge_baselines(baselines, identities):
    result={}
    for baseline in baselines:
        if set(baseline)!=set(identities):raise ValueError('Archive map baseline target identity set mismatch')
        for key, view in baseline.items():
            if norm(view.label)!=norm(identities[key]):raise ValueError('Archive map baseline span mismatch: '+key)
            old=result.get(key, MapView(view.label))
            if old.single_url and view.single_url and not same_url(old.single_url,view.single_url):
                raise ValueError('Conflicting archive single map URL: '+key)
            result[key]=MapView(view.label,
                merge_point(old.start,view.start,key,'start'),merge_point(old.end,view.end,key,'end'),
                old.single_url or view.single_url,merge_point(old.representative,view.representative,key,'overall'))
    return result


def baseline_pages(repo_root, date, explicit_root=None):
    paths=[]
    if explicit_root is not None:
        p=Path(explicit_root)/date/'index.html'
        if not p.is_file():raise ValueError('Explicit archive map baseline missing: '+str(p))
        paths.append(p)
    for p in (Path(repo_root)/'share'/date/'index.html', Path(repo_root)/'portal/archive'/date/'index.html'):
        if p.is_file() and p not in paths:paths.append(p)
    result=[]
    for p in paths:
        text=p.read_text(encoding='utf-8')
        explicit = explicit_root is not None and p == Path(explicit_root)/date/'index.html'
        if not explicit and is_fixed_form_alias(text):
            continue  # Known immutable ledger alias, not a legacy map page.
        result.append(parse_page(text,date))
    return result


def _published_map_roles(view):
    """Match the existing renderer: a single internal endpoint is not published."""
    two = bool(view.start and view.end and not same(view.start, view.end))
    return {'single_url': view.single_url,
            'start': view.start if two else None,
            'end': view.end if two else None,
            'representative': view.representative}


_AVAILABILITY_SHA256_LF = '18165217a47a8c70599a7c56505fc0d0e2b9a7a02def32d6e94efa7ba4381096'
_MAP_ROLES = ('single_url', 'start', 'end', 'representative')


@dataclass(frozen=True)
class MapAvailability:
    date: str
    data: bytes


def map_projection_sha256(date, key, view):
    import hashlib
    value = {'date': date, 'management_no': key, 'label': view.label, 'roles': _published_map_roles(view)}
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _availability_entries(data):
    import hashlib
    if not isinstance(data, bytes) or hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest() != _AVAILABILITY_SHA256_LF:
        raise ValueError('Archive map availability contract hash changed')
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result: raise ValueError('Duplicate archive map availability key')
            result[key] = value
        return result
    document = json.loads(data.decode('utf-8'), object_pairs_hook=pairs)
    if not isinstance(document, dict) or set(document) != {'schema', 'entries'} or document['schema'] != 'archive-map-availability/v1':
        raise ValueError('Invalid archive map availability schema')
    entries = document['entries']
    if not isinstance(entries, list) or not entries: raise ValueError('Invalid archive map availability entries')
    seen = set()
    for row in entries:
        if not isinstance(row, dict) or set(row) != {'date', 'management_no', 'label', 'unavailable_roles', 'evidence'}:
            raise ValueError('Invalid archive map availability row')
        day, key, label = row['date'], row['management_no'], row['label']
        if not isinstance(day, str) or not re.fullmatch(r'[0-9]{6}', day): raise ValueError('Invalid archive map availability date')
        from datetime import date as calendar_date
        calendar_date(2000 + int(day[:2]), int(day[2:4]), int(day[4:]))
        if not isinstance(key, str) or identity(key) != key or (day, key) in seen:
            raise ValueError('Duplicate or invalid archive map availability identity')
        seen.add((day, key))
        if not isinstance(label, str) or not label or any(ord(ch) < 32 for ch in label): raise ValueError('Invalid archive map availability label')
        roles = row['unavailable_roles']
        if not isinstance(roles, list) or not roles or any(not isinstance(role, str) or role not in _MAP_ROLES for role in roles) or roles != [role for role in _MAP_ROLES if role in roles]:
            raise ValueError('Invalid archive map availability roles')
        proof = row['evidence']
        if not isinstance(proof, dict) or set(proof) != {'commit', 'path', 'blob_sha1', 'html_sha256', 'map_projection_sha256'}:
            raise ValueError('Invalid archive map availability evidence')
        if proof['path'] != f'portal/archive/{day}/index.html': raise ValueError('Archive map availability evidence path mismatch')
        for name, size in (('commit', 40), ('blob_sha1', 40), ('html_sha256', 64), ('map_projection_sha256', 64)):
            if not isinstance(proof[name], str) or not re.fullmatch('[0-9a-f]{'+str(size)+'}', proof[name]):
                raise ValueError('Invalid archive map availability evidence hash')
    return entries


def _verified_unavailable(availability, date, prior, identities):
    if type(availability) is not MapAvailability or date != availability.date: raise ValueError('Archive map availability date binding mismatch')
    if not isinstance(date, str) or not re.fullmatch(r'[0-9]{6}', date): raise ValueError('Invalid archive map availability target date')
    result = {}
    for row in _availability_entries(availability.data):
        if row['date'] != date: continue
        key, label = row['management_no'], row['label']; view = prior.get(key)
        if view is None or view.label != label or identities.get(key) != label: raise ValueError('Archive map availability baseline identity/label mismatch: '+key)
        if map_projection_sha256(date, key, view) != row['evidence']['map_projection_sha256']: raise ValueError('Archive map availability baseline projection changed: '+key)
        roles = frozenset(row['unavailable_roles'])
        if any(_published_map_roles(view)[role] for role in roles): raise ValueError('Archive map availability contradicts a known baseline role: '+key)
        result[key] = roles
    return result


def load_map_availability(date, baselines):
    # Resolve beside the verified helper, never via another checkout or fallback.
    path = Path(__file__).with_name('archive_map_availability.json')
    if not path.is_file() or path.is_symlink() or getattr(path.lstat(), 'st_file_attributes', 0) & 0x400: raise ValueError('Archive map availability contract missing or unsafe')
    data = globals().get('__verified_availability_bytes__')
    if data is None: data = path.read_bytes()
    value = MapAvailability(date, data)
    identities = {key: view.label for baseline in baselines for key, view in baseline.items()}
    prior = merge_baselines(baselines, identities)
    _verified_unavailable(value, date, prior, identities)
    return value


def verify_map_availability(text, date, availability):
    """Check rendered unknown roles without using resolver or GPS output."""
    actual = parse_page(text, date)
    retained = _verified_unavailable(availability, date, actual, {key: view.label for key, view in actual.items()})
    for key, roles in retained.items():
        if any(_published_map_roles(actual[key])[role] for role in roles): raise ValueError('Rendered unavailable archive map role became enabled: '+key)


def resolve(items, gps, baselines, portal, *, availability=None, date=None):
    identities={}
    for it in items:
        key=identity(it.management_no)
        if key in identities:raise ValueError('Duplicate/invalid archive source identity: '+key)
        identities[key]=it.label
    prior=merge_baselines(baselines,identities)
    unavailable=_verified_unavailable(availability,date,prior,identities) if availability is not None else {}
    result={}
    for it in items:
        key=identity(it.management_no); label=it.label; old=prior.get(key,MapView(label))
        retained=unavailable.get(key,frozenset())
        source_start=point(label,it.start_lat,it.start_lng);source_end=point(label,it.end_lat,it.end_lng)
        # Resolve endpoint roles separately; compact available-points lists lose end-only identity.
        gs=ge=None; parts=portal._share_split_span_label(label)
        if parts:
            names=(parts[0],portal._share_complete_span_end_label(parts[0],parts[1],gps))
            resolved=[]
            for name in names:
                pole=portal._share_resolve_gps_pole_label(name,gps)
                resolved.append(point(pole,*gps[pole]) if pole else None)
            gs,ge=resolved
        else:
            pole=portal._share_resolve_gps_pole_label(label,gps)
            if pole:gs=point(pole,*gps[pole])
        start=merge_point(old.start,merge_point(source_start,gs,key,'source/GPS start'),key,'start')
        end=merge_point(old.end,merge_point(source_end,ge,key,'source/GPS end'),key,'end')
        for role, explicit in (('start',source_start),('end',source_end)):
            if role in retained and explicit is not None:
                raise ValueError('Explicit source contradicts unavailable map role: '+key+': '+role)
        if 'start' in retained:start=None
        if 'end' in retained:end=None
        plain=point(label,getattr(it,'lat',''),getattr(it,'lng',''))
        if 'representative' in retained and plain is not None:
            raise ValueError('Explicit source contradicts unavailable map role: '+key+': representative')
        # A verified overall-map point may be a midpoint, not a span endpoint.
        # Keep same-role plain/baseline conflicts; do not compare unlike roles.
        rep=old.representative if old.representative is not None else end or start
        if 'representative' in retained:rep=None
        rep=merge_point(rep,plain,key,'plain lat/lng')
        source_url=it.map_url.strip()
        if source_url:safe_url(source_url)
        if 'single_url' in retained and source_url:
            raise ValueError('Explicit source contradicts unavailable map role: '+key+': single_url')
        if old.single_url and source_url and not same_url(old.single_url,source_url):
            raise ValueError('Conflicting source/prior single map URL: '+key)
        single=old.single_url or source_url
        # A q= URL can be rounded independently; do not use it to replace known endpoints.
        if 'representative' not in retained:rep=rep or url_point(single,label)
        if 'single_url' not in retained and not single and rep:single=f'https://www.google.com/maps?q={rep[1]},{rep[2]}'
        view=MapView(label,start,end,single,rep)
        if key in prior:
            # An existing page cannot distinguish lost evidence from deliberately
            # unverified coordinates. Do not silently enable an absent map role.
            # Verified restoration uses the separate evidence-bound repair route.
            before=_published_map_roles(old); after=_published_map_roles(view)
            added=[role for role in before if after[role] and not before[role]]
            if added:
                raise ValueError('Unverified archive map role addition: '+key+': '+','.join(added))
        result[key]=view
    return result


def verify_rendered(text,date,expected):
    actual=parse_page(text,date)
    if set(actual)!=set(expected):raise ValueError('Rendered archive map identity set changed')
    for key,want in expected.items():
        got=actual[key]
        if norm(got.label)!=norm(want.label) or got.single_url!=want.single_url:
            raise ValueError('Rendered archive single-map/label changed: '+key)
        two=want.start and want.end and not same(want.start,want.end)
        for role in ('start','end'):
            a=getattr(got,role);b=getattr(want,role) if two else None
            if bool(a)!=bool(b) or a and (not same(a,b) or a[0]!=b[0]):
                raise ValueError('Rendered archive two-map changed: '+key+' '+role)
        if bool(got.representative)!=bool(want.representative) or got.representative and not same(got.representative,want.representative):
            raise ValueError('Rendered archive overall map changed: '+key)


def verify_preserved(text,date,baselines):
    """Independent lower-bound guard: previously available values must survive."""
    actual=parse_page(text,date)
    expected=merge_baselines(baselines,{k:v.label for k,v in actual.items()})
    for key,want in expected.items():
        got=actual[key]
        if want.single_url and got.single_url!=want.single_url:raise ValueError('Lost/changed prior single map: '+key)
        for role in ('start','end','representative'):
            before=getattr(want,role);after=getattr(got,role)
            if before and (not same(before,after) or role!='representative' and before[0]!=after[0]):
                raise ValueError('Lost/changed prior map '+role+': '+key)


def export_map_items(document, date):
    """Read only public identity/map fields; never reconstruct business facts."""
    from types import SimpleNamespace
    if str(document.get('date', '')) != date:
        raise ValueError('Archive map export date mismatch')
    result = []
    for group in ('items', 'planned_but_incomplete'):
        rows = document.get(group, [])
        if not isinstance(rows, list):
            raise ValueError('Archive map export group is not an array')
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Invalid archive map export row')
            source = row.get('source_item', {})
            if not isinstance(source, dict):
                raise ValueError('Invalid archive map source_item')
            number = str(source.get('management_no') or row.get('management_no') or '')
            if source.get('management_no') and row.get('management_no') and identity(source['management_no']) != identity(row['management_no']):
                raise ValueError('Archive export/source identity mismatch')
            values = {name: str(source.get(name) or '') for name in
                      ('map_url', 'start_lat', 'start_lng', 'end_lat', 'end_lng', 'lat', 'lng')}
            result.append(SimpleNamespace(management_no=number,
                          label=str(source.get('label') or row.get('label') or ''), **values))
    return result
