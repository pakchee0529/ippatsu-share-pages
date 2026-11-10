"""Reproducibly repair four retired share-page return links, without business writes.

This is a bounded historical-navigation adapter, not a normal-day generator.
It protects input hashes, missing retired parent indexes, same-day saved archive
membership and referenced immutable files. All inputs are checked before writing.
Run with --repo-root INPUT --output-root EMPTY_STAGE --evidence-root EVIDENCE.
"""
from pathlib import Path
from urllib.parse import urlsplit
import argparse, hashlib, json, re

PLAN = {
    "share/261028/daily/index.html": "a822e3211e3021017ba2ebcff7dbaa1a3e33e7f5d31a465af50e0d52708145b6",
    "share/261028/instructions/index.html": "cd4fad887d34c1386e2fe0f87ab62b13afc80acfd99d86de009cf59eb49ebc24",
    "share/261029/daily/index.html": "eb33aa7623b9ff8ac71da405b57f2536f62dde64817aa6628c8483e93a9cf51e",
    "share/261029/instructions/index.html": "12dc61ea83341e5a1a75c152ef7777dc7c85c88306fa936f65cf5b3a791c3eaa",
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def config(text):
    matches = re.findall(r'<script id="shared-ledger-config" type="application/json">(.*?)</script>', text, re.S)
    if len(matches) != 1:
        raise ValueError("Expected one unchanged public ledger config")
    return json.loads(matches[0])

def repair_bytes(source, date, mode, expected_sha):
    rel = f"share/{date}/{mode}/index.html"
    if rel not in PLAN:
        raise ValueError("Date or mode is outside the four-path repair scope")
    text = source.decode("utf-8")
    cfg = config(text)
    if cfg.get("date") != date:
        raise ValueError("Public config date mismatch")
    ids = [x["cs"] for x in cfg["cases"]]
    if not ids or len(set(ids)) != len(ids) or any(not re.fullmatch(r"\d{8}", x) for x in ids):
        raise ValueError("Invalid or duplicate public case identities")
    old_label = "当日の共有ページへ戻る" if mode == "daily" else "共有ページに戻る"
    label = "当日の完了アーカイブへ" if mode == "daily" else "当日の保存指示書へ"
    href = f"../../../portal/archive/{date}/view.html" + ("?document=instructions" if mode == "instructions" else "")
    old = f'<a href="../">{old_label}</a>'
    new = f'<a href="{href}">{label}</a>'
    if sha(source.replace(b"\r\n", b"\n")) != expected_sha:
        if text.count(new) == 1 and text.count(old) == 0:
            before = text.replace(new, old, 1).encode("utf-8")
            if sha(before.replace(b"\r\n", b"\n")) == expected_sha:
                return source, {"path": rel, "date": date, "mode": mode, "href": href, "cases": ids,
                                "status": "already_aligned", "old_sha256": sha(source), "new_sha256": sha(source),
                                "only_return_href_and_label_changed": True, "config_unchanged": True}
        raise ValueError("Input hash changed; review the new input before repairing")
    if text.count(old) != 1:
        raise ValueError("Expected exactly one original return link")
    result = text.replace(old, new, 1).encode("utf-8")
    if result.replace(new.encode(), old.encode(), 1) != source:
        raise ValueError("Unexpected non-navigation change")
    if config(result.decode()) != cfg:
        raise ValueError("Public config changed")
    return result, {"path": rel, "date": date, "mode": mode, "href": href, "cases": ids,
                    "old_sha256": sha(source), "new_sha256": sha(result),
                    "only_return_href_and_label_changed": True, "config_unchanged": True}

def verify_archive(repo, date, ids):
    if (repo / "share" / date / "index.html").exists():
        raise ValueError("Parent share index exists; this is not a retired return link")
    view = repo / "portal/archive" / date / "view.html"
    if not view.is_file():
        raise ValueError("Same-day archive viewer is missing")
    text = view.read_text(encoding="utf-8")
    matches = re.findall(r'<script type="application/json" id="archive-snapshot-data">(.*?)</script>', text, re.S)
    if len(matches) != 1:
        raise ValueError("Expected one frozen archive dataset")
    data = json.loads(matches[0])
    days = data.get("days", [])
    if data.get("scope") != "saved-day" or len(days) != 1 or days[0].get("date") != date or not days[0].get("available"):
        raise ValueError("Archive does not identify the same saved day")
    cases = data.get("cases", [])
    if len(cases) != len(ids) or {x.get("management_no") for x in cases} != set(ids):
        raise ValueError("Archive membership differs from the old public page")
    if any(x.get("date") != date or not x.get("clearance_html") or not x.get("instructions_html") for x in cases):
        raise ValueError("Archive is missing a same-day saved document")
    proofs = {}
    for item in cases:
        for key in ("daily_source_href", "instructions_href"):
            href = item.get(key, "")
            prefix = f"/ippatsu-share-pages/portal/archive/{date}/saved-forms/"
            u = urlsplit(href)
            if u.scheme or u.netloc or not u.path.startswith(prefix):
                raise ValueError("Archive source is not an approved same-day immutable path")
            path = (repo / u.path.removeprefix("/ippatsu-share-pages/")).resolve()
            if not path.is_relative_to(repo) or not path.is_file():
                raise ValueError("Referenced immutable document is missing")
            proofs[path.relative_to(repo).as_posix()] = sha(path.read_bytes())
    return {"view_sha256": sha(view.read_bytes()), "immutable_sources": proofs}

def generate(repo, output, evidence):
    repo, output, evidence = (Path(p).resolve() for p in (repo, output, evidence))
    if output == repo or output.is_relative_to(repo) or evidence == repo or evidence.is_relative_to(repo):
        raise ValueError("Output and evidence must be outside the input repository")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be empty")
    prepared = []
    proofs = {}
    for rel, expected in PLAN.items():
        source_path = (repo / rel).resolve()
        if not source_path.is_relative_to(repo) or not source_path.is_file():
            raise ValueError("Expected input path missing or outside input repository")
        _, date, mode, _ = rel.split("/")
        source = source_path.read_bytes()
        result, row = repair_bytes(source, date, mode, expected)
        proofs[date] = verify_archive(repo, date, row["cases"])
        prepared.append((rel, source, result, row))
    # Nothing above mutates an input or a target; all guards must pass first.
    output.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    for rel, source, result, row in prepared:
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result)
    for rel, source, result, row in prepared:
        if (repo / rel).read_bytes() != source:
            raise ValueError("Input changed during staging")
    for proof in proofs.values():
        for rel, expected in proof["immutable_sources"].items():
            if sha((repo / rel).read_bytes()) != expected:
                raise ValueError("Immutable source changed during staging")
    report = {"schema": "retired-page-navigation-repair/v1", "public_or_db_write": False,
              "source_inputs_unchanged": True, "immutable_unchanged": True,
              "files": [x[3] for x in prepared], "archive_proofs": proofs}
    (evidence / "repair-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--evidence-root", type=Path, required=True)
    a = p.parse_args()
    result = generate(a.repo_root, a.output_root, a.evidence_root)
    print(json.dumps({"staged_files": len(result["files"]), "immutable_unchanged": True,
                      "public_or_db_write": False}, ensure_ascii=False))
