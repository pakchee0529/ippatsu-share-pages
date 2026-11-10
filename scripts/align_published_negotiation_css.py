"""Align existing public negotiation CSS with its already-adopted generator.

A bounded published-asset alignment adapter, not a new business generation route.
It inserts only the exact disabled-map CSS already in generate_portal.py since
commit aef1a87. No public data, scripts, settings, inputs or API calls are changed.
"""
from pathlib import Path
import argparse, ast, hashlib, json, re
PLAN = {
    "portal/negotiation/index.html": "2f8fa07bd2b9f8c6cbfb759159028d4b84805a5b645cf28d0bdc64b579caeddc",
    "portal/negotiation/gojo/index.html": "836aee048aea54c07c5e885a65816e6b6b2939286c223480750b9b323ce195fb",
    "portal/negotiation/totsukawa/index.html": "4d407d40b01cc5bed16554cc550120c54844ac6308a62b87b4bc4db9c572d2d7",
    "portal/negotiation/yoshino/index.html": "0fb674a08b99a339cfc5814d01025ded90eb935a9aa0e3c7af738c55454a482e",
}
SOURCE_SHA256_LF = "9e2ec2d826764c249dadfc98a0a68f5903994fb7d963b1ff4a53fbe11e78a3b3"
ANCHOR = ".btn-map:hover, .btn-map:focus { filter: brightness(1.05); }\n"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def source_block(source):
    normalized = source.replace(b"\r\n", b"\n")
    if sha(normalized) != SOURCE_SHA256_LF:
        raise ValueError("Adopted generator hash changed; review before alignment")
    text = normalized.decode("utf-8")
    functions = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "build_negotiation_html"]
    if len(functions) != 1:
        raise ValueError("Expected the adopted negotiation template")
    region = ast.get_source_segment(text, functions[0])
    blocks = re.findall(r'\.btn-map-disabled,\s*\.btn-map:disabled \{\{.*?\}\}', region, re.S)
    if len(blocks) != 1:
        raise ValueError("Expected one disabled-map CSS definition")
    return blocks[0].replace("{{", "{").replace("}}", "}") + "\n"

def repair_bytes(source, rel, block):
    if rel not in PLAN:
        raise ValueError("Path is outside the four-page alignment scope")
    text = source.decode("utf-8")
    normalized = text.replace("\r\n", "\n")
    styles = list(re.finditer(r'<style[^>]*>(.*?)</style>', normalized, re.S))
    if len(styles) != 1:
        raise ValueError("Expected one existing style block")
    style = styles[0].group(1)
    count = style.count(".btn-map-disabled")
    if count:
        if count != 1 or style.count(block) != 1:
            raise ValueError("Conflicting or duplicated disabled-map CSS")
        before = normalized.replace(block, "", 1)
        if sha(before.encode()) != PLAN[rel]:
            raise ValueError("Existing CSS is not the exact bounded repair; input changed")
        return source, {"path": rel, "status": "already_aligned", "sha256": sha(source)}
    if sha(normalized.encode()) != PLAN[rel]:
        raise ValueError("Input hash changed; review before alignment")
    if style.count(ANCHOR) != 1:
        raise ValueError("Expected exactly one existing map-hover insertion anchor")
    newline = "\r\n" if "\r\n" in text else "\n"
    old = ANCHOR.replace("\n", newline)
    inserted = block.replace("\n", newline)
    if text.count(old) != 1:
        raise ValueError("Insertion anchor is ambiguous outside the style block")
    result = text.replace(old, old + inserted, 1).encode("utf-8")
    if result.replace(inserted.encode(), b"", 1) != source:
        raise ValueError("Unexpected non-CSS change")
    new_text = result.decode()
    strip_style = lambda t: re.sub(r'<style[^>]*>.*?</style>', '<style/>', t, flags=re.S)
    if strip_style(new_text) != strip_style(text):
        raise ValueError("Body, script or configuration changed")
    return result, {"path": rel, "status": "aligned", "old_sha256": sha(source),
                    "new_sha256": sha(result), "only_adopted_css_inserted": True,
                    "body_scripts_config_unchanged": True, "css_source_sha256": sha(block.encode())}

def generate(repo, output, evidence):
    repo, output, evidence = (Path(p).resolve() for p in (repo, output, evidence))
    if output == repo or output.is_relative_to(repo) or evidence == repo or evidence.is_relative_to(repo):
        raise ValueError("Output and evidence must be outside the input repository")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be empty")
    block = source_block((repo / "scripts/generate_portal.py").read_bytes())
    prepared = []
    for rel in PLAN:
        path = (repo / rel).resolve()
        if not path.is_relative_to(repo) or not path.is_file():
            raise ValueError("Expected input missing or outside input repository")
        source = path.read_bytes()
        value, record = repair_bytes(source, rel, block)
        prepared.append((rel, source, value, record))
    output.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    for rel, source, value, record in prepared:
        p = output / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value)
    if any((repo / rel).read_bytes() != source for rel, source, value, record in prepared):
        raise ValueError("Input changed during staging")
    report = {"schema": "adopted-negotiation-css-alignment/v1", "public_or_db_write": False,
              "business_generator_changed": False, "source_sha256_lf": SOURCE_SHA256_LF,
              "source_inputs_unchanged": True, "files": [x[3] for x in prepared]}
    (evidence / "repair-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--evidence-root", type=Path, required=True)
    a = p.parse_args()
    result = generate(a.repo_root, a.output_root, a.evidence_root)
    print(json.dumps({"staged_files": len(result["files"]), "public_or_db_write": False}, ensure_ascii=False))
