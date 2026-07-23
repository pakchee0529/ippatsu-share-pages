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
    assert '<div class="two-map-wrap" id="two-wrap-0" hidden>' in both
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

    g9_gps = {
        "二津野96G9": (33.9138, 135.78144),
        "二津野97G9": (33.91354, 135.78177),
    }
    g9_card = card.replace("二津野4～5", "二津野96～97")
    g9, _point = portal._share_card_with_recovered_map(g9_card, 0, g9_gps, [])
    assert _single_target(g9) == (33.91354, 135.78177)
    assert "btn-map-two btn-map-disabled" not in g9
    assert '"name": "二津野96G9"' in g9
    assert '"name": "二津野97G9"' in g9
    assert '<div class="two-map-wrap" id="two-wrap-0" hidden>' in g9
    _assert_order(g9)

    prefixed_gps = {
        "S今西68": (34.0, 135.0),
        "S今西69": (34.1, 135.1),
        "P百谷38S10": (34.2, 135.2),
        "P百谷38S11": (34.3, 135.3),
        "白銀63N5E9G2": (34.4, 135.4),
        "白銀63N5E9G3": (34.5, 135.5),
        "入谷1": (34.6, 135.6),
        "上湯川167G9": (34.7, 135.7),
    }
    for label, expected in (
        ("S今西68～69", (34.1, 135.1)),
        ("P百谷38S10～38S11", (34.3, 135.3)),
        ("白銀63N5E9G2～E9G3", (34.5, 135.5)),
        ("入谷1～上湯川167", (34.7, 135.7)),
    ):
        recovered_card = card.replace("二津野4～5", label)
        recovered, _point = portal._share_card_with_recovered_map(
            recovered_card, 0, prefixed_gps, []
        )
        assert _single_target(recovered) == expected
        assert "btn-map-two btn-map-disabled" not in recovered
        _assert_order(recovered)

    single_card = card.replace("二津野4～5", "二津野96")
    single, _point = portal._share_card_with_recovered_map(
        single_card, 0, g9_gps, []
    )
    assert _single_target(single) == (33.9138, 135.78144)
    assert "btn-map-two btn-map-disabled" in single
    _assert_order(single)

    virtual_start_card = card.replace("二津野4～5", "沼田原85K～86N1")
    virtual_start, _point = portal._share_card_with_recovered_map(
        virtual_start_card,
        0,
        {"沼田原86N1": (34.8, 135.8)},
        [],
    )
    assert _single_target(virtual_start) == (34.8, 135.8)
    assert "btn-map-two btn-map-disabled" in virtual_start
    _assert_order(virtual_start)

    print("OK: share card map controls use old/young/disabled rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
