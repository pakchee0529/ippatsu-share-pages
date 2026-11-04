"""Regression: removed temporary TOP entries must not return on regeneration."""
from generate_portal import build_html

page = build_html([('261104', '2026年11月04日　奥吉野　4件')], calendar_api_key='')
for removed in ('weekly-plan', 'print-test-entry', 'print-260721', './weekly/2026-11-02.pdf'):
    assert removed not in page, removed
for retained in ('today-schedule-root', '../share/261104/', './calendar/', 'OJTアンケート', '意見・改善案'):
    assert retained in page, retained
print('PASS: removed PDF and print-test entries stay absent; operational entries retained')
