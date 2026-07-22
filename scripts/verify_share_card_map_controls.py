#!/usr/bin/env python3
"""Verify share-card map target, disabled states, and button ordering."""

from __future__ import annotations

import re

import generate_portal as portal


def _card() -> str:
    return """
<article class="card">
  <div class="card-head">
    <h2 class="card-title">二津野4～5</h2>
    <p class="item-mgmt">51400000</p>
    <div class="card-actions">
      <button type="button" class="btn btn-note" data-note-toggle>現場指示</button>
    </div>
  </div>
  <div class="note-panel"></div>
</article>
""".strip()


def _single_target(html: str) -> tuple[float, float] | None:
    match = re.search(
        r'class="[^"]*btn-map-single[^"]*" '
        r'href="https://www\.google\.com/maps\?q=([^,]+),([^\"]+)"',
        html,
    )
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def _assert_order(html: str) -> None:
    single = html.find("btn-map-single")
    two = html.find("btn-map-two")
    note = html.find("btn-note")
    assert 0 <= single < two < note, (single, two, note)


def main() -> int:
    card = _card()
    both, _point = portal._share_card_with_recovered_map(
        card,
        0,
        {"二津野4": (34.0, 135.0), "二津野5": (34.1, 135.1)},
        [],
    )
    assert _single_target(both) == (34.1, 135.1)
    assert "data-two-open" in both
    assert "btn-map-two btn-map-disabled" not in both
    _assert_order(both)

    partial, _point = portal._share_card_with_recovered_map(
        card,
        0,
        {"二津野4": (34.0, 135.0)},
        [],
    )
    assert _single_target(partial) == (34.0, 135.0)
    assert "btn-map-two btn-map-disabled" in partial
    _assert_order(partial)

    missing, _point = portal._share_card_with_recovered_map(card, 0, {}, [])
    assert "btn-map-single btn-map-disabled" in missing
    assert "btn-map-two btn-map-disabled" in missing
    assert "現場地図を開く" not in missing
    _assert_order(missing)

    invalid_embedded = card.replace(
        '<div class="note-panel"></div>',
        '<script type="application/json" id="two-geo-0">'
        '{"a":{"name":"(unknown)","lat":0,"lng":0},'
        '"b":{"name":"(unknown)","lat":0,"lng":0}}'
        '</script><div class="note-panel"></div>',
    )
    invalid, point = portal._share_card_with_recovered_map(
        invalid_embedded, 0, {}, []
    )
    assert point is None
    assert "btn-map-single btn-map-disabled" in invalid
    assert "btn-map-two btn-map-disabled" in invalid
    assert 'type="application/json"' not in invalid
    _assert_order(invalid)

    print("OK: share card map controls use old/young/disabled rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
