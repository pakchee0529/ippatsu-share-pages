"""Read-only regression: source assets -> builder -> exact published views.
Run: python scripts/test_archive_layout_generation.py [repo_root]
No DB/network; temporary outputs only. This is not a visual-browser test.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
saved = {p: digest(p) for p in (root / "portal/archive").glob("*/saved-forms/**/*.html")}
with tempfile.TemporaryDirectory(prefix="archive-layout-test-") as td:
    out, evidence = Path(td) / "output", Path(td) / "evidence"
    subprocess.run([sys.executable, str(root / "scripts/archive_snapshot_builder.py"),
                    "--repo-root", str(root), "--output-root", str(out),
                    "--evidence-root", str(evidence),
                    "--assets-root", str(root / "scripts/archive_snapshot_assets")], check=True)
    generated = [out / "portal/archive/index.html",
                 out / "portal/archive/archive-v2-r1/app.js",
                 out / "portal/archive/archive-v2-r1/style.css",
                 *sorted((out / "portal/archive").glob("*/view.html"))]
    for p in generated:
        rel = p.relative_to(out)
        assert p.read_bytes() == (root / rel).read_bytes(), f"Stale generated view: {rel}"
    rel = Path("portal/archive/archive-v2-r1/catalog.json")
    assert json.loads((out / rel).read_text()) == json.loads((root / rel).read_text()), "Catalog drift"
    index = (out / "portal/archive/index.html").read_text()
    for name in ("app.js", "style.css"):
        value = digest(out / "portal/archive/archive-v2-r1" / name)[:16]
        assert name + "?v=" + value in index, f"Stale cache key: {name}"
    count = 0
    for p in sorted((out / "portal/archive").glob("*/view.html")):
        src = p.read_text()
        assert "alignBranchPhotoCount(fragment.content)" in src
        assert ".quantity-heading{display:flex;flex-wrap:wrap;" in src
        data = re.search(r'id="archive-snapshot-data">(.*?)</script>', src, re.S)
        assert data, f"Missing frozen snapshots: {p}"
        count += len(json.loads(data[1])["cases"])
    assert {p: digest(p) for p in saved} == saved, "Saved originals modified"
    print(f"PASS: {len(generated)} exact generated files; {count} cases; cache keys; saved originals unchanged.")
