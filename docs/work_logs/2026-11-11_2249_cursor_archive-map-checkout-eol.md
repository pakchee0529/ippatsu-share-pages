# Preserve reviewed archive map bytes on Windows checkout

- Baseline: 71234bc370b625b58655c8c5888670708784f2ef.
- The baseline has no root .gitattributes. Three reviewed map.html files had unspecified text/eol attributes and were converted to CRLF under core.autocrlf=true, causing their raw SHA-256 map guard to reject a fresh checkout.
- Add only the exact paths portal/archive/261104/map.html, portal/archive/261105/map.html and portal/archive/261106/map.html with text eol=lf. No broad wildcard, Git configuration change or guard/hash relaxation is included.
- Two new local clones were materialized with real git checkout-index and command-local core.autocrlf=true. The before index used the unchanged baseline; the after index added only the proposed .gitattributes. No source repository was modified and no commit, fetch or push was performed by this test.
- Before: all three working-tree map files became CRLF and failed their fixed raw hashes. The ordinary builder and unchanged company source wrapper both refused them before creating any staged publication files.
- After: all three raw map hashes exactly matched their existing LF Git blob bytes and fixed MAP_PAGE_SHA256 values. The other 1079 tracked working-tree files were byte-identical between the two checkouts. Every original tracked Git blob remained unchanged.
- On the after checkout, the current unchanged company source wrapper and runner installed and read back dates 261104, 261105, 261106 and 261111. Each ordinary stage had exactly the established six outputs. All four records remained verifiable after the sequence.
- Catalog content, map pages and immutable saved forms remained unchanged through the company compatibility test. Runtime source files, company EXE, shared Git settings, database, adopted repository and existing private state were not changed. The GUI EXE was not launched; browser acceptance is not claimed.
- Proposed publication scope is exactly .gitattributes and this new work log. Existing map bytes, source code, source contract and the prior reviewed publication files are not changed.
