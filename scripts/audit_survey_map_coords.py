#!/usr/bin/env python3
"""Audit portal/survey/index.html for map marker coordinates."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LAT_MIN, LAT_MAX = 33.0, 36.0
LNG_MIN, LNG_MAX = 134.0, 137.0


def in_range(lat: float, lng: float) -> bool:
    if lat == 0.0 or lng == 0.0:
        return False
    return LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX


def audit_html(html: str, *, html_path: str = "") -> dict:

    markers: list[dict] = []
    for m in re.finditer(
        r'<article[^>]*data-management-no-key="([^"]+)"[^>]*'
        r'data-multipin-lat="([^"]+)"[^>]*data-multipin-lng="([^"]+)"',
        html,
    ):
        key, lat_s, lng_s = m.group(1), m.group(2), m.group(3)
        lat, lng = float(lat_s), float(lng_s)
        chunk = html[max(0, m.start() - 500) : m.end() + 100]
        label_m = re.search(r'data-label="([^"]*)"', chunk)
        mgmt_m = re.search(r'data-management-no="([^"]*)"', chunk)
        markers.append(
            {
                "source": "data-multipin-attr (Leaflet #share-map via collectVisibleSurveyMultipinPoints)",
                "management_no_key": key,
                "management_no": mgmt_m.group(1) if mgmt_m else "",
                "label": label_m.group(1) if label_m else "",
                "lat": lat,
                "lng": lng,
                "in_range": in_range(lat, lng),
                "html_line": html[: m.start()].count("\n") + 1,
            }
        )

    two_geo_out: list[dict] = []
    for m in re.finditer(
        r'id="two-geo-(\d+)"[^>]*>(\{.*?\})</script>',
        html,
        re.DOTALL,
    ):
        idx = m.group(1)
        try:
            data = json.loads(m.group(2))
        except json.JSONDecodeError:
            continue
        for role in ("a", "b"):
            pt = data.get(role) or {}
            if "lat" not in pt or "lng" not in pt:
                continue
            lat, lng = float(pt["lat"]), float(pt["lng"])
            row = {
                "source": f"two-geo-{idx}.{role} (per-card map only)",
                "name": pt.get("name", ""),
                "lat": lat,
                "lng": lng,
                "in_range": in_range(lat, lng),
            }
            if not row["in_range"]:
                two_geo_out.append(row)
        for i, pt in enumerate(data.get("nearby") or []):
            if not isinstance(pt, dict) or "lat" not in pt or "lng" not in pt:
                continue
            lat, lng = float(pt["lat"]), float(pt["lng"])
            if not in_range(lat, lng):
                two_geo_out.append(
                    {
                        "source": f"two-geo-{idx}.nearby[{i}]",
                        "name": pt.get("name", ""),
                        "lat": lat,
                        "lng": lng,
                        "in_range": False,
                    }
                )

    out_of = [m for m in markers if not m["in_range"]]
    return {
        "html_path": html_path,
        "survey_cards": len(re.findall(r"survey-update-card", html)),
        "multipin_marker_count": len(markers),
        "multipin_markers": markers,
        "out_of_range_multipin_count": len(out_of),
        "out_of_range_multipin": out_of,
        "out_of_range_two_geo_count": len(two_geo_out),
        "out_of_range_two_geo": two_geo_out,
        "key_51410418_multipin": [
            m for m in markers if m["management_no_key"] == "51410418"
        ],
        "has_static_var_points": bool(re.search(r"var points\s*=", html)),
        "has_L_marker_literal": bool(re.search(r"L\.marker\s*\(\s*\[", html)),
    }


def main() -> int:
    html_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent / "portal" / "survey" / "index.html"
    )
    html = Path(html_path).read_text(encoding="utf-8", errors="replace")
    report = audit_html(html, html_path=str(html_path))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
