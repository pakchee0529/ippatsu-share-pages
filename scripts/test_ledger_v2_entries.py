from pathlib import Path
import subprocess
from refresh_ledger_v2_entries import PATTERN,refresh

root=Path(__file__).resolve().parents[1]
count=0
for file in (root/'share').glob('*/index.html'):
    relative=file.relative_to(root).as_posix()
    old=subprocess.check_output(['git','show','HEAD:'+relative],cwd=root).decode('utf-8')
    new=file.read_text(encoding='utf-8')
    assert PATTERN.sub('',old)==PATTERN.sub('',new),relative
    assert refresh(new)==new,relative
    count+=new.count('台帳入力（新版）')
assert count>0
print(f'ledger entry regeneration: {count} cards; other published content unchanged')
