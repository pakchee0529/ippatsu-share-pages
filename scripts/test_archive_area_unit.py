"""Regression for archive area expressions. No database writes or network calls."""
from generate_portal import _archive_m2_expr, _archive_number_expr
key = "bush_cut_area_m2"
for before, added, final in [(50, 64, 114), (15, 30, 45)]:
    source = {key: final, "_completion_felling_formula": {key: {"before": before, "added": added}}}
    assert _archive_m2_expr(source, key) == f"{before} + {added}㎡"
    assert _archive_number_expr(source, key, suffix="本") == f"{before} + {added}本"
assert _archive_m2_expr({key: 0}, key) == "0㎡"
assert _archive_m2_expr({key: 45}, key) == "45㎡"
assert _archive_m2_expr({key: 45, "_completion_felling_formula": {key: {"before": 45, "added": 0}}}, key) == "45㎡"
print("PASS: 7 archive area/number expression checks")
