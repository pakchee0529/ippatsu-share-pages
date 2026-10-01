"""Regenerate only the existing ledger footer, leaving published case data intact."""
from pathlib import Path
import html
import re
from generate_portal import _photo_ledger_input_footer_html

PATTERN=re.compile(r'<div class="photo-ledger-input-footer"[^>]*>[\s\S]*?</div>')
def refresh(content):
    def replace(match):
        link=re.search(r'href="([^"]*/ledger-input/[^\"]*)"',match[0])
        return _photo_ledger_input_footer_html(html.unescape(link[1])) if link else match[0]
    return PATTERN.sub(replace,content)

def main():
    root=Path(__file__).resolve().parents[1]
    for file in sorted((root/'share').glob('*/index.html')):
        old=file.read_text(encoding='utf-8');new=refresh(old)
        if old!=new:
            file.write_text(new,encoding='utf-8',newline='\n');print(file.relative_to(root))
if __name__=='__main__':main()
