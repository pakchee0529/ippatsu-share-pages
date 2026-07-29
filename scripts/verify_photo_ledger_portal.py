"""Static checks for the photo-ledger QR PoC published under the portal."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PAGE_DIR = ROOT / "portal" / "photo-ledger"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    required_files = {
        "index.html",
        "app.js",
        "styles.css",
        "pack.js",
        "qrcode.js",
        "qrcode_UTF8.js",
        "service-worker.js",
        "manifest.webmanifest",
        "icon-192.png",
        "icon-512.png",
    }
    actual_files = {
        path.name for path in PAGE_DIR.iterdir() if path.is_file()
    }
    require(required_files <= actual_files, "PWA assets are incomplete")

    portal_top = (ROOT / "portal" / "index.html").read_text(encoding="utf-8")
    require(
        'href="./photo-ledger/"' in portal_top,
        "portal hamburger menu link is missing",
    )
    require(
        "QR仕切り札（PoC）" in portal_top,
        "portal hamburger menu label is missing",
    )

    index = (PAGE_DIR / "index.html").read_text(encoding="utf-8")
    app = (PAGE_DIR / "app.js").read_text(encoding="utf-8")
    pack = (PAGE_DIR / "pack.js").read_text(encoding="utf-8")
    worker = (PAGE_DIR / "service-worker.js").read_text(encoding="utf-8")
    manifest = json.loads(
        (PAGE_DIR / "manifest.webmanifest").read_text(encoding="utf-8")
    )

    require("整理用QRです。正式看板ではありません。" in index, "notice missing")
    require(
        index.index("pack.js")
        < index.index("qrcode.js")
        < index.index("qrcode_UTF8.js")
        < index.index("app.js"),
        "QR runtime load order",
    )
    pack_values = json.loads(
        pack.removeprefix("window.PHOTO_LEDGER_PACK=").rstrip(";\n")
    )
    if pack_values.get("version") == 4:
        days = pack_values.get("days") or []
        require(days, "date registry has no day packs")
        require(
            pack_values.get("workDateCount") == len(days),
            "workDateCount does not match days",
        )
        day_keys = [str(day.get("workDate") or "") for day in days]
        require(
            pack_values.get("defaultWorkDate") in day_keys,
            "defaultWorkDate is not registered",
        )
        require(
            len(day_keys) == len(set(day_keys)),
            "work dates must be unique",
        )
    cases = pack_values.get("cases") or [
        {
            "caseId": pack_values.get("caseId"),
            "managementNo": pack_values.get("managementNo"),
            "markers": pack_values.get("markers") or [],
        }
    ]
    require(cases, "photo-ledger pack has no cases")
    require(
        pack_values.get("caseCount", len(cases)) == len(cases),
        "caseCount does not match cases",
    )
    marker_ids: list[str] = []
    for case in cases:
        markers = case.get("markers") or []
        require(len(markers) == 22, "each case must have 22 QR markers")
        require(
            all(str(item.get("payload") or "").startswith("IP1:") for item in markers),
            "case contains a non-IP1 start marker",
        )
        marker_ids.extend(str(item.get("id") or "") for item in markers)
        overview_modes = {
            item["payloadValues"]["p"]: item["endMode"]
            for item in markers
            if item["payloadValues"]["k"] == "O"
        }
        require(
            overview_modes == {"B": "NONE", "A": "PAIRED_PICK"},
            "overview before/after end modes are incorrect",
        )
    require(len(marker_ids) == len(set(marker_ids)), "marker ids must be unique")
    require('"endMode":"COUNT"' in pack, "COUNT marker is missing")
    require(
        '"endMode":"PAIRED_PICK"' in pack,
        "paired overview PICK marker is missing",
    )
    require("FinePix XP140" in pack, "camera label missing")
    require('encodeValues("IP2:"' in app, "dynamic IP2 generation is missing")
    require("marker-folder" in app, "branch/root folders are missing")
    require("workDateSelect" in app, "work-date selector is missing")
    require("chooseWorkDatePack" in app, "work-date auto selection is missing")
    require("caseSelect" in app, "work-date case selector is missing")
    require("switchCase" in app, "case switching is missing")
    require("前後採用QRを表示" in app, "paired overview picker is missing")
    require("採用QRは撮りません" in app, "overview-before guidance is missing")
    require(
        app.index('item.payloadValues.k === "O"')
        < app.index("for (const folder of folders) appendFolder(folder);")
        < app.index('item.payloadValues.k !== "O"'),
        "marker display order must be overview, branch/root, then bush and others",
    )
    require("fetch(" not in app, "phone app must not call a network API")
    require("http://" not in app and "https://" not in app, "external URL in app")
    require(manifest.get("display") == "standalone", "PWA display mode")
    require(len(manifest.get("icons") or []) == 2, "PWA icons")
    for asset in required_files - {"service-worker.js"}:
        require(
            f'"./{asset}"' in worker or asset in {"icon-192.png", "icon-512.png"},
            f"service worker cache entry missing: {asset}",
        )
    require("icon-192.png" in worker, "192 icon cache entry")
    require("icon-512.png" in worker, "512 icon cache entry")
    require("qrcode.js" in worker, "QR generator cache entry")
    require("qrcode_UTF8.js" in worker, "UTF-8 QR cache entry")

    combined = "\n".join((index, app, pack, worker))
    require(not re.search(r"[A-Za-z]:\\\\", combined), "local absolute path exposed")
    require("service_role" not in combined.casefold(), "service role text exposed")

    print("photo ledger portal verifier: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
