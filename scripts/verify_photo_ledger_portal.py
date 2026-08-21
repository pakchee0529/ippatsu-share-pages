"""Verify that QR divider assets are retained but no longer exposed by the portal."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE_DIR = ROOT / "portal" / "photo-ledger"
GENERIC_PAGE = ROOT / "portal" / "photo-ledger-generic" / "index.html"


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
    require(required_files <= actual_files, "retained QR assets are incomplete")

    portal_top = (ROOT / "portal" / "index.html").read_text(encoding="utf-8")
    require(
        'href="./photo-ledger/"' not in portal_top,
        "retired QR divider link is still exposed",
    )
    require(
        'href="./photo-ledger-generic/"' not in portal_top,
        "retired generic QR divider link is still exposed",
    )
    require(GENERIC_PAGE.is_file(), "generic QR divider page is missing")
    require(
        "QR仕切り札" not in portal_top,
        "retired QR divider label is still exposed",
    )

    print("photo ledger portal retirement verifier: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
