# Repair four historical return links

Using scripts/repair_retired_share_navigation.py, regenerate only share/261028/{daily,instructions}/index.html and share/261029/{daily,instructions}/index.html. Their parent share indexes no longer exist. The daily link now opens the same-day completed archive viewer, and the instruction link opens that viewer in instruction mode. Labels identify those destinations accurately.

The 10/28 eight-case and 10/29 three-case sets exactly match the explicit saved archives. Apart from the single return href and label on each page, every source byte is preserved, including public config, case order, quantities, conditions, photos and old asset references. No old page or TOP entry is restored or deleted. All immutable documents remain unchanged.

62 guard checks and deterministic generation passed. This repairs navigation only; retained historical live pages are not re-certified as current business data. Browser/print/server-save validation is not claimed. Publication and HTTP verification are separate coordinating-writer steps.
