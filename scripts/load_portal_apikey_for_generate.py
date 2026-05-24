"""Load publishable apikey for generate_portal (never prints the key)."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _jwt_role(key: str) -> str | None:
    parts = key.split(".")
    if len(parts) != 3:
        return None
    try:
        import base64

        pad = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(pad))
        return str(payload.get("role") or "")
    except (ValueError, json.JSONDecodeError, OSError):
        return None


def resolve_portal_apikey(repo_root: Path) -> str:
    for name in ("PORTAL_SURVEY_REQUEST_API_KEY", "SUPABASE_ANON_KEY"):
        raw = (os.environ.get(name) or "").strip()
        if not raw:
            continue
        role = _jwt_role(raw)
        if role == "service_role":
            continue
        if role == "anon" or len(raw) > 40:
            return raw
    survey_html = repo_root / "portal" / "survey" / "index.html"
    if survey_html.is_file():
        text = survey_html.read_text(encoding="utf-8", errors="replace")
        m = re.search(
            r'var\s+SURVEY_STATUS_REQUEST_API_KEY\s*=\s*"([^"]+)"',
            text,
        )
        if not m:
            m = re.search(r'var\s+PORTAL_STATUS_API_KEY\s*=\s*"([^"]+)"', text)
        if m:
            key = m.group(1).strip()
            if key and _jwt_role(key) != "service_role":
                return key
    return ""


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    key = resolve_portal_apikey(root)
    if not key:
        print("PORTAL_APIKEY_MISSING", file=sys.stderr)
        return 1
    # stdout for parent shell: set env without echoing in logs if redirected carefully
    print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
