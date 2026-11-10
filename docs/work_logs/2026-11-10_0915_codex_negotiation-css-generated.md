# Apply the adopted disabled-map style to four negotiation pages

Using scripts/align_published_negotiation_css.py, align portal/negotiation/index.html and gojo, totsukawa, yoshino/index.html. Only the existing formal generator's .btn-map-disabled / .btn-map:disabled declaration is added. It gives unavailable map buttons their already-adopted gray, non-interactive appearance.

All four style blocks now exactly match the current formal negotiation template after whitespace normalization. The entire body, every script, configuration and business value are byte-identical. No map locations, statuses, action handlers, permissions or source template are changed. Current static affected-button count is zero; dynamic content was not exercised.

49 guard checks, deterministic output and exact-result idempotence passed. No actual browser or production action was run. The coordinating writer performs publication and post-publication HTTP checks separately.
