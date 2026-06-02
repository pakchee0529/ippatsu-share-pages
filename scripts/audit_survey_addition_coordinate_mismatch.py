#!/usr/bin/env python3
"""Read-only audit: survey addition scripts vs queue / Supabase / portal HTML / GPS."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

# share-pages repo root
SHARE_ROOT = Path(__file__).resolve().parent.parent
PC_ROOT = SHARE_ROOT.parent / "ippatsu-pc"
PC_PROD_DATA = Path(r"C:\Users\kotan\Projects\ippatsu-pc-prod\data")
QUEUE_DEV = PC_ROOT / "data" / "survey" / "queue.json"
QUEUE_PROD = PC_PROD_DATA / "survey" / "queue.json"
GPS_PATH = PC_ROOT / "app" / "resources" / "data" / "GPS.json"
SURVEY_HTML = SHARE_ROOT / "portal" / "survey" / "index.html"
NEG_HTML = SHARE_ROOT / "portal" / "negotiation" / "index.html"
PREVIEW_KEYS = (
    "51404162",
    "51402038",
    "51410139",
    "51410418",
    "51410417",
    "51400394",
    "51403794",
)
LAT_MIN, LAT_MAX, LNG_MIN, LNG_MAX = 33.0, 36.0, 134.0, 137.0


def norm_key(mno: str) -> str:
    return re.sub(r"\D", "", mno or "")


def norm_label(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", (s or "").strip()))


def in_jp_bounds(lat: float | None, lng: float | None) -> bool:
    if lat is None or lng is None or lat == 0 or lng == 0:
        return False
    return LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX


def load_queue(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for it in raw.get("items") or []:
        if not isinstance(it, dict):
            continue
        k = norm_key(str(it.get("management_no") or ""))
        if k:
            out[k] = it
    return out


def parse_survey_cards(html: str) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    for m in re.finditer(
        r'<article[^>]*data-management-no-key="([^"]+)"[^>]*>',
        html,
    ):
        key = m.group(1)
        start = m.start()
        end = html.find("</article>", start)
        block = html[start : end if end > 0 else start + 8000]
        cards[key] = {
            "has_map_btn": 'class="btn btn-map"' in block and "地図を表示" in block,
            "has_two_btn": "data-two-open" in block,
            "has_multipin": "data-multipin-lat" in block,
            "label": _attr(block, "data-label"),
            "management_no": _attr(block, "data-management-no"),
        }
    return cards


def parse_negotiation_cards(html: str) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    for m in re.finditer(
        r'<article[^>]*data-management-no-key="([^"]+)"[^>]*>',
        html,
    ):
        key = m.group(1)
        start = m.start()
        end = html.find("</article>", start)
        block = html[start : end if end > 0 else start + 5000]
        cards[key] = {
            "has_map_btn": "btn-map" in block and ("地図を表示" in block or "maps?q=" in block),
            "has_two_btn": "data-two-open" in block,
            "label": _attr(block, "data-label"),
        }
    return cards


def _attr(block: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', block)
    return m.group(1) if m else ""


def gps_can_resolve(label: str, pole_coords: dict[str, str]) -> dict[str, Any]:
    """Lightweight: reuse ippatsu-pc search if importable."""
    try:
        if str(PC_ROOT) not in sys.path:
            sys.path.insert(0, str(PC_ROOT))
        from tools.preview_survey_wait_additions_20260529 import (  # type: ignore
            share_gps_autofill,
        )

        gps = share_gps_autofill(label, pole_coords)
        ok = bool(gps.get("map_url")) and gps.get("lat") is not None
        two = (
            gps.get("start_lat") is not None
            and gps.get("end_lat") is not None
            and in_jp_bounds(
                float(gps["start_lat"]),
                float(gps["start_lng"]),
            )
            and in_jp_bounds(float(gps["end_lat"]), float(gps["end_lng"]))
        )
        return {
            "gps_ok": ok,
            "gps_two_ok": two,
            "warning": gps.get("warning"),
            "method": gps.get("resolution_method"),
        }
    except Exception as e:
        return {"gps_ok": None, "gps_two_ok": None, "warning": str(e)}


def fetch_supabase_status() -> dict[str, dict[str, Any]]:
    try:
        if str(SHARE_ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(SHARE_ROOT / "scripts"))
        import generate_portal as gp  # type: ignore

        gp.load_portal_dotenv(SHARE_ROOT)
        out: dict[str, dict[str, Any]] = {}
        for status in ("survey_wait", "negotiation_wait"):
            items, _, _, _smoke = gp._load_status_public_items(
                status=status,
                legacy_count=0,
                empty_msg="",
            )
            for it in items:
                k = (it.management_no_key or "").strip()
                if k:
                    out[k] = {
                        "status": status,
                        "label": it.label,
                        "management_no": it.management_no,
                        "start_lat": it.start_lat,
                        "start_lng": it.start_lng,
                        "end_lat": it.end_lat,
                        "end_lng": it.end_lng,
                    }
        return out
    except Exception as e:
        return {"__error__": {"status": str(e)}}


def classify_row(row: dict[str, Any]) -> str:
    if row.get("preview_target"):
        if not row.get("in_queue_dev") and not row.get("in_queue_prod"):
            if row.get("gps_ok"):
                return "C"  # GPS ok but queue missing -> map UI gap
            return "B" if row.get("supabase_status") == "survey_wait" else "E"
    if row.get("supabase_status") == "survey_wait":
        if row.get("portal_multipin") or (row.get("portal_map_btn") and row.get("portal_two_btn")):
            return "A"
        if row.get("gps_ok") and not row.get("in_queue_dev"):
            return "C"
        if not row.get("gps_ok") and not row.get("queue_has_coords"):
            return "B"
        if row.get("queue_has_coords") and not row.get("portal_map_btn"):
            return "C"
    if row.get("supabase_status") == "negotiation_wait" and row.get("portal_neg_map"):
        return "D"
    return "?"


def main() -> int:
    queue_dev = load_queue(QUEUE_DEV)
    queue_prod = load_queue(QUEUE_PROD)
    survey_cards = parse_survey_cards(SURVEY_HTML.read_text(encoding="utf-8"))
    neg_cards = parse_negotiation_cards(NEG_HTML.read_text(encoding="utf-8"))
    sb = fetch_supabase_status()
    sb_err = sb.get("__error__")

    pole_coords: dict[str, str] = {}
    if GPS_PATH.is_file():
        try:
            if str(PC_ROOT) not in sys.path:
                sys.path.insert(0, str(PC_ROOT))
            from app.core.loader import load_pole_coords  # type: ignore

            pole_coords, _ = load_pole_coords(GPS_PATH)
        except Exception:
            pass

    survey_keys = sorted(
        k for k, v in sb.items() if k != "__error__" and v.get("status") == "survey_wait"
    )
    neg_keys = sorted(
        k for k, v in sb.items() if k != "__error__" and v.get("status") == "negotiation_wait"
    )
    all_keys = sorted(set(survey_keys) | set(neg_keys) | set(PREVIEW_KEYS))

    rows: list[dict[str, Any]] = []
    for key in all_keys:
        sb_row = sb.get(key) or {}
        qd = queue_dev.get(key)
        qp = queue_prod.get(key)
        sc = survey_cards.get(key, {})
        nc = neg_cards.get(key, {})
        label = sb_row.get("label") or (qd or {}).get("label") or sc.get("label") or ""
        gps = gps_can_resolve(label, pole_coords) if label and pole_coords else {}
        q_has = bool(
            qd
            and (
                (qd.get("start_lat") and qd.get("start_lng"))
                or (qd.get("lat") and qd.get("lng"))
            )
        )
        row = {
            "management_no_key": key,
            "label": label,
            "preview_target": key in PREVIEW_KEYS,
            "supabase_status": sb_row.get("status"),
            "in_queue_dev": key in queue_dev,
            "in_queue_prod": key in queue_prod,
            "queue_label_dev": (qd or {}).get("label"),
            "queue_status_dev": (qd or {}).get("status"),
            "queue_survey_status": (qd or {}).get("survey_status"),
            "queue_has_coords": q_has,
            "gps_ok": gps.get("gps_ok"),
            "gps_two_ok": gps.get("gps_two_ok"),
            "gps_warning": gps.get("warning"),
            "portal_survey": key in survey_cards,
            "portal_map_btn": sc.get("has_map_btn"),
            "portal_two_btn": sc.get("has_two_btn"),
            "portal_multipin": sc.get("has_multipin"),
            "portal_negotiation": key in neg_cards,
            "portal_neg_map": nc.get("has_map_btn"),
            "portal_neg_two": nc.get("has_two_btn"),
            "class": "",
        }
        row["class"] = classify_row(row)
        rows.append(row)

    summary = {
        "survey_wait_count": len(survey_keys),
        "negotiation_wait_count": len(neg_keys),
        "survey_portal_cards": len(survey_cards),
        "survey_multipin_html": sum(1 for c in survey_cards.values() if c.get("has_multipin")),
        "survey_map_btn": sum(1 for c in survey_cards.values() if c.get("has_map_btn")),
        "survey_two_btn": sum(1 for c in survey_cards.values() if c.get("has_two_btn")),
        "neg_map_btn": sum(1 for c in neg_cards.values() if c.get("has_map_btn")),
        "preview_keys_in_queue_dev": [k for k in PREVIEW_KEYS if k in queue_dev],
        "preview_keys_in_queue_prod": [k for k in PREVIEW_KEYS if k in queue_prod],
        "preview_keys_missing_queue_dev": [k for k in PREVIEW_KEYS if k not in queue_dev],
        "supabase_fetch_error": sb_err,
    }
    report = {"summary": summary, "rows": rows, "preview_keys": list(PREVIEW_KEYS)}
    out_path = SHARE_ROOT / "output" / "survey_addition_coordinate_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
