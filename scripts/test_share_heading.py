"""Numeric headings must not combine with regex group references into octal escapes."""
import generate_portal as g
for date, expected in [("261013", "2026年10月13日"), ("260101", "2026年01月01日")]:
    source = '<title>old</title><header><h1 class="page-title">old</h1></header>'
    result = g._normalize_share_page_heading(source, date)
    assert '<h1 class="page-title">' + expected + '</h1>' in result, result
    assert '<title>' + expected + '</title>' in result
    assert g._normalize_share_page_heading(result, date) == result
print("PASS: numeric date heading, retained h1, idempotent normalization")
