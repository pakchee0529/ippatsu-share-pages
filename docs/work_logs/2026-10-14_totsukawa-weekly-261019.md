# Totsukawa weekly schedule publication

User approved importing the scanned October 19-23 weekly schedule and publishing
daily field pages. The source JPEG is 26101408100.jpg, reviewed as 22 cases in
daily order 4/5/5/5/3. No GM or span-total fields were imported.

All 22 cases matched existing Totsukawa cases uniquely. The established weekly
import path restored 21 legacy completed cases and advanced one negotiation-wait
case to construction_wait. No cases were created or removed. DB read-back passed.
All 22 instruction quantity patches matched after import; unrelated cases and
non-quantity detail fields were verified unchanged.

Generated five daily pages and added their links to portal/index.html. Every card
has a map link, two-endpoint map, overall marker, and ledger-input link. Final
HTML order matches the JPEG. No HTML map warnings were reported.

Publication uses a detached worktree based on origin/main to avoid publishing
unrelated local commits. Application source and original workbooks are unchanged.
Operational evidence is under ippatsu-pc-prod/output/weekly_261019.
