# Retired GAS removal: seven existing share pages

User explicitly approved removing and republishing only the obsolete GAS integration on these seven pages.

Base: 13ea337a02be9254bf63eab90bf6d8b46ee1a5f5

- share/260728/index.html
- share/260827/index.html
- share/261019/index.html
- share/261020/index.html
- share/261021/index.html
- share/261022/index.html
- share/261023/index.html

Only the opaque share-live-edit-inject block was removed (16747 bytes per file). Every byte outside that block, all cards and instruction tables, ordering, plans, and archive/manifest files were verified unchanged. The current generator removes the retired block and does not reintroduce it. Existing EXE and secret-environment stripping retained; no source/EXE/DB/permissions changes. Isolated recipe, before/after SHA and restoration backup are retained in the Codex task workspace.
