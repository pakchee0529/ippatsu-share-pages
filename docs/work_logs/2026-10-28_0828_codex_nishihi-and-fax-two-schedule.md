# 2026-10-28 scheduled spans and CS conditions

Reflect user-confirmed 261028 schedule additions 西日裏99～100 (51406421) and 西日裏90G1～90G2 (51406563), preserving the existing six. Exact eight-card order follows the user's instruction. 西日裏96～97 now shows confirmed 持出 / B車可 / road 4m / slope 傾; its warning remains.

DB changes used existing Whole Save/CAS and ordinary lifecycle/schedule/order functions with version guards. Quantities, notes, completion dates, reception episodes and saved ledger documents were retained. No new case intake or duplicate registration.

Newly scheduled two cases have no case_details rows or saved ledger documents. An isolated export-boundary adapter represents those absent quantity values as None, feeding the existing unknown display contract and null shared-ledger baseline. No numeric data was fabricated and no generator checks were disabled. Existing six quantity displays remain unchanged. Production source and shared-ledger modules are unchanged.

Generated only the current shared page, daily clearance view, instruction view and portal top from the pinned normal generator. Local mobile/desktop DOM tests passed (13 checks, no non-GET request); new cases remain null/unknown. Other public assets are byte-identical. DB receipts and private source evidence stay outside this repository. HTTP/live display verification follows publication.
