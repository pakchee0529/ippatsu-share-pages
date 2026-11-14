"""Retain adopted blank-to-zero projections without publishing private originals.

Private inspected-cell observations are consumed only on an explicit correction.
The sanitized projection is retained as generation input so regeneration cannot
silently revert a reviewed correction to the original unknown/candidate labels.
"""
from decimal import Decimal
import json
import re
from app.share.source_quantity_evidence import project_observation, validate_blank_projection

SCHEMA = 'ippatsu-source-blank-projections/v1'
OBSERVATIONS = 'ippatsu-source-quantity-observations/v1'
FILE = 'scripts/source_quantity_projections.json'


def retained_projections(root, source_ref, dates, evidence_path=None):
    data = json.loads((root / FILE).read_text('utf8'))
    if not isinstance(data, dict) or set(data) != {'schema', 'source_ref', 'projections'} or data['schema'] != SCHEMA or data['source_ref'] != source_ref or not isinstance(data['projections'], list):
        raise ValueError('Retained source-quantity revision differs')
    rows = {}
    for row in data['projections']:
        _validate_row(row, dates)
        p = row['projection']; key = (row['date'], p['case_key'], p['field'])
        if key in rows:
            raise ValueError('Duplicate retained source quantity')
        rows[key] = row
    if evidence_path is not None:
        private = json.loads(evidence_path.read_text('utf8'))
        if not isinstance(private, dict) or set(private) != {'schema', 'source_ref', 'observations'} or private['schema'] != OBSERVATIONS or private['source_ref'] != source_ref or not isinstance(private['observations'], list):
            raise ValueError('Private observation revision differs')
        seen = set()
        for row in private['observations']:
            if not isinstance(row, dict) or set(row) != {'date', 'case_key', 'field', 'observation'} or row['date'] not in dates:
                raise ValueError('Private observation outside requested scope')
            key = (row['date'], row['case_key'], row['field'])
            if key in seen:
                raise ValueError('Duplicate private source quantity')
            seen.add(key)
            p = project_observation(row['case_key'], row['field'], row['observation'])
            if p['state'] == 'unknown':
                if key in rows:
                    raise ValueError('Unresolved new observation conflicts with retained zero')
                continue
            if p['state'] != 'source_blank_zero':
                raise ValueError('This correction path accepts inspected blanks only; numeric source values remain unchanged')
            public = {'date': row['date'], 'projection': p}
            _validate_row(public, dates)
            rows[key] = public
    return {'schema': SCHEMA, 'source_ref': source_ref,
            'projections': [rows[key] for key in sorted(rows)]}


def _validate_row(row, dates):
    if not isinstance(row, dict) or set(row) != {'date', 'projection'} or row['date'] not in dates:
        raise ValueError('Retained projection outside requested dates')
    validate_blank_projection(row['projection'])


def apply_blank_projections(entries, date, retained):
    cases = {entry['cs']: entry for entry in entries}
    for row in retained['projections']:
        if row['date'] != date:
            continue
        p = row['projection']; validate_blank_projection(p)
        if p['case_key'] not in cases:
            raise ValueError('Source projection case outside the public day')
        if cases[p['case_key']]['label'] != p['span_label']:
            raise ValueError('Source projection span differs from the public case')
        quantity = next((q for q in cases[p['case_key']]['quantities'] if q['field'] == p['field']), None)
        if quantity is None:
            raise ValueError('Source projection quantity field missing')
        if quantity['state'] in {'source_positive', 'source_zero', 'formal_confirmed'}:
            match = re.match(r'[0-9]+(?:\.[0-9]+)?', quantity['text'])
            if match is None or Decimal(match[0]) != 0:
                raise ValueError('Inspected blank conflicts with an existing published numeric quantity')
            continue  # Preserve existing zero and its prior public confirmation category.
        if quantity['state'] not in {'unknown', 'source_blank', 'nonapplicable_candidate', 'source_blank_zero'}:
            raise ValueError('Unsupported public quantity state')
        quantity.update(state=p['state'], text=p['text'])
