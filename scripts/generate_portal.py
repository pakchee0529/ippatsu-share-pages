#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan share/<date>/index.html and regenerate portal/index.html and portal/archive/index.html (stdlib only)."""

from __future__ import annotations

import html as html_lib
import json
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

# Leading Japanese run (kanji / hiragana / katakana) before span codes (digits etc.).
_CROWN_HEAD = re.compile(
    r"^([\u3040-\u309F\u30A0-\u30FF\u4e00-\u9fff]+)(?=[0-9０-９]|$)"
)
_ARTICLE_CARD = re.compile(
    r'<article\s+[^>]*\bclass\s*=\s*["\']card["\'][^>]*>', re.I
)
_H2_CARD_TITLE = re.compile(
    r'<h2\s+[^>]*\bclass\s*=\s*["\']card-title["\'][^>]*>([^<]*)</h2>', re.I
)


class TitleExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._buf: list[str] = []
        self.title: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "title":
            self._in_title = True
            self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
            raw = "".join(self._buf).strip()
            self.title = html_lib.unescape(raw) if raw else None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._buf.append(data)


class _ShareDisplaySuffixExtractor(HTMLParser):
    """``<meta name="share-display-suffix" content="...">`` の content のみ取得（先頭1件）。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.suffix: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if self.suffix is not None:
            return
        if tag.lower() != "meta":
            return
        ad = {k.lower(): (v or "") for k, v in attrs}
        if (ad.get("name") or "").strip().lower() != "share-display-suffix":
            return
        content = ad.get("content")
        if content is None:
            return
        raw = html_lib.unescape(str(content)).strip()
        if raw:
            self.suffix = raw


def extract_share_display_suffix(html: str) -> str:
    """共有HTMLのメタから表示補足のみ取得（本文は見ない）。"""
    parser = _ShareDisplaySuffixExtractor()
    try:
        parser.feed(html)
    except Exception:
        return ""
    s = parser.suffix
    return s.strip() if s else ""


def extract_title(index_path: Path) -> str | None:
    try:
        text = index_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    parser = TitleExtractor()
    try:
        parser.feed(text)
    except Exception:
        return None
    t = parser.title
    if not t:
        return None
    return t.strip() or None


def fallback_heading(date_folder: str) -> str:
    """YYMMDD -> 20YY年MM月DD日; sample -> fixed label; else folder name."""
    if date_folder.lower() == "sample":
        return "サンプル（参考表示）"
    if re.fullmatch(r"\d{6}", date_folder):
        yy, mm, dd = int(date_folder[0:2]), int(date_folder[2:4]), int(date_folder[4:6])
        year = 2000 + yy
        return f"{year}年{mm:02d}月{dd:02d}日"
    return date_folder


def sort_key(date_folder: str) -> tuple:
    """Six-digit dates first (numeric), then others, then sample last."""
    if date_folder.isdigit() and len(date_folder) == 6:
        return (0, int(date_folder))
    if date_folder.lower() == "sample":
        return (2, date_folder)
    return (1, date_folder)


def card_heading(date_folder: str, index_path: Path) -> str:
    if date_folder.lower() == "sample":
        return "サンプル（参考表示）"
    # 6桁日付キー: <title>/h1 に display_suffix が含まれることがあるため、
    # ポータル先頭の日付はフォルダ名からのみ生成する（補足は meta のみで後段に付与）。
    if re.fullmatch(r"\d{6}", date_folder):
        return fallback_heading(date_folder)
    t = extract_title(index_path)
    if t:
        return t
    return fallback_heading(date_folder)


def count_article_cards(html: str) -> int:
    return len(_ARTICLE_CARD.findall(html))


def extract_points_array(html: str) -> list[dict] | None:
    marker = "var POINTS = "
    i = html.find(marker)
    if i < 0:
        return None
    i += len(marker)
    while i < len(html) and html[i] in " \t\r\n":
        i += 1
    if i >= len(html) or html[i] != "[":
        return None
    depth = 0
    start = i
    for j in range(i, len(html)):
        c = html[j]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                blob = html[start : j + 1]
                try:
                    data = json.loads(blob)
                except json.JSONDecodeError:
                    return None
                if isinstance(data, list):
                    return data
                return None
    return None


def extract_card_title_labels(html: str) -> list[str]:
    raw = _H2_CARD_TITLE.findall(html)
    return [html_lib.unescape(m).strip() for m in raw if m.strip()]


def extract_crown_name(label: str) -> str | None:
    """Area-style prefix before span codes; no digits/lat-lng/person fields."""
    if not label:
        return None
    s = html_lib.unescape(label).strip()
    m = _CROWN_HEAD.match(s)
    if not m:
        return None
    base = m.group(1).strip()
    if not base:
        return None
    return base


@dataclass(frozen=True)
class ShareSummary:
    item_count: int
    crown_names: tuple[str, ...]
    is_sample: bool
    display_suffix: str = ""


def summarize_share_html(html: str, date_folder: str) -> ShareSummary:
    if date_folder.lower() == "sample":
        n = count_article_cards(html)
        return ShareSummary(item_count=n, crown_names=(), is_sample=True)

    suffix_meta = extract_share_display_suffix(html)

    n_cards = count_article_cards(html)
    points = extract_points_array(html)
    labels: list[str] = []

    if points and all(isinstance(p, dict) for p in points):
        if len(points) == n_cards:
            for p in points:
                name = p.get("name")
                labels.append(str(name).strip() if name is not None else "")
        else:
            labels = extract_card_title_labels(html)
    else:
        labels = extract_card_title_labels(html)

    crowns_ordered: list[str] = []
    seen: set[str] = set()
    for lb in labels:
        c = extract_crown_name(lb)
        if c and c not in seen:
            seen.add(c)
            crowns_ordered.append(c)

    item_count = n_cards
    if item_count == 0 and labels:
        item_count = len(labels)

    return ShareSummary(
        item_count=item_count,
        crown_names=tuple(crowns_ordered),
        is_sample=False,
        display_suffix=suffix_meta,
    )


def format_crown_summary(crowns: tuple[str, ...], max_show: int = 4) -> str:
    if not crowns:
        return ""
    if len(crowns) <= max_show:
        return "・".join(crowns)
    shown = crowns[:max_show]
    rest = len(crowns) - max_show
    return "・".join(shown) + f"　ほか{rest}件"


def build_portal_heading(
    date_heading: str, summary: ShareSummary, max_show: int = 4
) -> str:
    if summary.is_sample:
        return date_heading
    parts: list[str] = [date_heading]
    if summary.crown_names:
        sm = format_crown_summary(summary.crown_names, max_show=max_show)
        if sm:
            parts.append(sm)
    parts.append(f"{summary.item_count}件")
    sfx = (summary.display_suffix or "").strip()
    if sfx:
        parts.append(sfx)
    return "　".join(parts)


def escape_html(s: str) -> str:
    return html_lib.escape(s, quote=True)


def month_heading_key(folder: str) -> tuple[int, int] | None:
    """6桁 YYMMDD から (西暦年, 月)。"""
    if not re.fullmatch(r"\d{6}", folder):
        return None
    yy, mm = int(folder[0:2]), int(folder[2:4])
    return (2000 + yy, mm)


def month_label_from_key(year: int, month: int) -> str:
    return f"{year}年{month:02d}月"


def group_archive_sections(
    parts: list[tuple[str, ShareSummary]],
) -> list[tuple[tuple[int, int], str, list[tuple[str, ShareSummary]]]]:
    """月新しい順。各月内は日付キー新しい順。"""
    from collections import defaultdict

    buckets: dict[tuple[int, int], list[tuple[str, ShareSummary]]] = defaultdict(list)
    for folder, summary in parts:
        mk = month_heading_key(folder)
        if mk is None:
            continue
        buckets[mk].append((folder, summary))
    keys = sorted(buckets.keys(), reverse=True)
    out: list[tuple[tuple[int, int], str, list[tuple[str, ShareSummary]]]] = []
    for y, m in keys:
        label = month_label_from_key(y, m)
        items = sorted(buckets[(y, m)], key=lambda t: sort_key(t[0]), reverse=True)
        out.append(((y, m), label, items))
    return out


def archive_row_search_blob(
    folder: str, date_jp: str, crown_sm: str, item_n: int, suffix: str
) -> str:
    """検索用のプレーンテキスト（小文字化前提で連結）。"""
    bits = [
        folder,
        date_jp,
        crown_sm or "",
        f"{item_n}件",
        suffix or "",
    ]
    return " ".join(b for b in bits if str(b).strip())


def build_archive_html(
    sections: list[tuple[tuple[int, int], str, list[tuple[str, ShareSummary]]]],
) -> str:
    """月ごとのアーカイブ一覧（検索付き）。"""
    month_blocks: list[str] = []
    for (y, m), month_label, items in sections:
        mid = f"m-{y:04d}-{m:02d}"
        rows_html: list[str] = []
        for folder, summary in items:
            date_jp = fallback_heading(folder)
            crown_sm = format_crown_summary(summary.crown_names)
            if not crown_sm.strip():
                crown_sm = "—"
            sfx = (summary.display_suffix or "").strip()
            sfx_html = ""
            if sfx:
                sfx_html = (
                    f'    <div class="archive-suffix">{escape_html(sfx)}</div>\n'
                )
            blob = archive_row_search_blob(
                folder, date_jp, crown_sm, summary.item_count, sfx
            )
            search_attr = escape_html(blob)
            href = f"../share/{folder}/"
            rows_html.append(
                f"""    <article class="archive-row" data-search="{search_attr}">
      <div class="archive-row-top">
        <div class="archive-date">{escape_html(date_jp)} <span class="archive-dkey">({escape_html(folder)})</span></div>
        <div class="archive-count">{summary.item_count}件</div>
      </div>
      <div class="archive-crown">{escape_html(crown_sm)}</div>
{sfx_html}      <a class="btn btn-archive" href="{escape_html(href)}">共有ページを開く</a>
    </article>"""
            )
        rows_str = "\n".join(rows_html)
        month_blocks.append(
            f"""  <section class="month-block" aria-labelledby="{mid}">
    <h2 class="month-title" id="{mid}">{escape_html(month_label)}</h2>
    <div class="archive-list" role="list">
{rows_str}
    </div>
  </section>"""
        )
    months_str = "\n".join(month_blocks) if month_blocks else ""
    empty_note = (
        '  <p class="empty-note">該当する公開ページ（6桁日付の share/&lt;date&gt;/）がありません。</p>\n'
        if not months_str
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>現場共有アーカイブ</title>
<style>
:root {{
  --bg-b: #eef2f7;
  --card-b: #fff;
  --text-b: #142033;
  --muted-b: #5a6578;
  --border-b: #cfd8e3;
  --accent-b: #1565c0;
  --accent-b-hover: #0d47a1;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Hiragino Sans",
    "Noto Sans JP", sans-serif;
  background: var(--bg-b);
  color: var(--text-b);
  line-height: 1.5;
  padding: 0.85rem 0.85rem 1.5rem;
  max-width: 40rem;
  margin-left: auto;
  margin-right: auto;
}}
.top-bar {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
  margin-bottom: 0.75rem;
}}
.top-bar a {{
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--accent-b);
  text-decoration: none;
  padding: 0.35rem 0.5rem;
  border-radius: 6px;
}}
.top-bar a:hover, .top-bar a:focus-visible {{
  text-decoration: underline;
  outline: none;
}}
h1 {{
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
}}
.lead {{
  font-size: 0.92rem;
  color: var(--muted-b);
  margin: 0 0 0.75rem;
}}
.search-wrap {{
  margin-bottom: 1rem;
}}
#archive-search {{
  width: 100%;
  min-height: 48px;
  font-size: 1rem;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--border-b);
  border-radius: 10px;
  font-family: inherit;
}}
.month-block {{
  margin-bottom: 1.25rem;
}}
.month-title {{
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
  padding-bottom: 0.35rem;
  border-bottom: 2px solid var(--border-b);
  color: var(--text-b);
}}
.archive-list {{
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}}
.archive-row {{
  background: var(--card-b);
  border: 1px solid var(--border-b);
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  box-shadow: 0 1px 2px rgba(20, 32, 51, 0.05);
}}
.archive-row-top {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}}
.archive-date {{
  font-weight: 700;
  font-size: 0.95rem;
}}
.archive-dkey {{
  font-weight: 600;
  color: var(--muted-b);
  font-size: 0.82rem;
}}
.archive-count {{
  font-size: 0.88rem;
  color: var(--muted-b);
  font-weight: 600;
  white-space: nowrap;
}}
.archive-crown {{
  font-size: 0.88rem;
  color: var(--text-b);
  margin-bottom: 0.35rem;
  word-break: break-word;
}}
.archive-suffix {{
  font-size: 0.82rem;
  color: var(--muted-b);
  margin-bottom: 0.45rem;
}}
a.btn-archive {{
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.95rem;
  color: #fff;
  background: var(--accent-b);
  border-radius: 9px;
  padding: 0.55rem 0.75rem;
  min-height: 44px;
}}
a.btn-archive:hover, a.btn-archive:active {{
  background: var(--accent-b-hover);
}}
.empty-note {{
  color: var(--muted-b);
  font-size: 0.95rem;
}}
.footer-note {{
  margin-top: 1.25rem;
  font-size: 0.8rem;
  color: var(--muted-b);
  text-align: center;
}}
.visually-hidden {{
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}}
</style>
</head>
<body>
  <nav class="top-bar" aria-label="サイト内リンク">
    <a href="../">ポータルTOP</a>
    <a href="../ui_samples/">UIサンプル</a>
  </nav>
  <h1>現場共有アーカイブ</h1>
  <p class="lead">公開中の過去現場（share/&lt;日付&gt;/）を月ごとに並べています。検索で日付・径間名・件数・補足から絞り込めます。</p>
  <div class="search-wrap">
    <label for="archive-search" class="visually-hidden">検索</label>
    <input type="search" id="archive-search" placeholder="日付・冠称名・件数・補足で検索" autocomplete="off">
  </div>
  <div id="archive-months">
{months_str}
{empty_note}  </div>
  <p class="footer-note">このページは <code>scripts/generate_portal.py</code> で再生成できます。</p>
  <script>
(function () {{
  var input = document.getElementById("archive-search");
  if (!input) return;
  function norm(s) {{
    return (s || "").toLowerCase();
  }}
  function apply() {{
    var q = norm(input.value).trim();
    var rows = document.querySelectorAll(".archive-row");
    var months = document.querySelectorAll(".month-block");
    rows.forEach(function (row) {{
      var hay = norm(row.getAttribute("data-search") || "");
      var show = !q || hay.indexOf(q) >= 0;
      row.style.display = show ? "" : "none";
    }});
    months.forEach(function (sec) {{
      var vis = false;
      sec.querySelectorAll(".archive-row").forEach(function (r) {{
        if (r.style.display !== "none") vis = true;
      }});
      sec.style.display = vis ? "" : "none";
    }});
  }}
  input.addEventListener("input", apply);
  input.addEventListener("search", apply);
}})();
  </script>
</body>
</html>
"""


def build_html(
    entries: list[tuple[str, str]],
) -> str:
    """entries: list of (date_folder, portal_card_heading)."""
    cards = []
    for folder, heading in entries:
        href = f"../share/{folder}/"
        cards.append(
            f"""    <article class="card" role="listitem">
      <h2 class="card-title">{escape_html(heading)}</h2>
      <a class="btn" href="{escape_html(href)}">共有ページを開く</a>
    </article>"""
        )
    cards_str = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>現場共有ポータル</title>
<style>
:root {{
  --bg-b: #f0f4f8;
  --card-b: #fff;
  --text-b: #142033;
  --muted-b: #5a6578;
  --border-b: #cfd8e3;
  --accent-b: #1565c0;
  --accent-b-hover: #0d47a1;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Hiragino Sans",
    "Noto Sans JP", sans-serif;
  background: var(--bg-b);
  color: var(--text-b);
  line-height: 1.55;
  padding: 1rem 1rem 2rem;
  max-width: 40rem;
  margin-left: auto;
  margin-right: auto;
}}
h1, .portal-title {{
  font-size: 1.35rem;
  font-weight: 700;
  margin: 0;
  line-height: 1.3;
}}
.portal-header {{
  margin-bottom: 0.75rem;
}}
.portal-header-row {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}}
.portal-title {{
  flex: 1;
  min-width: 0;
  word-break: break-word;
}}
.portal-menu-wrap {{
  position: relative;
  flex-shrink: 0;
}}
.portal-menu-btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  min-height: 48px;
  min-width: 48px;
  padding: 0.45rem 0.65rem;
  font-size: 0.95rem;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-b);
  background: var(--card-b);
  border: 1px solid var(--border-b);
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(20, 32, 51, 0.06);
}}
.portal-menu-btn:hover,
.portal-menu-btn:focus-visible {{
  border-color: var(--accent-b);
  outline: none;
}}
.portal-menu-icon {{
  font-size: 1.15rem;
  line-height: 1;
}}
.portal-menu-label {{
  white-space: nowrap;
}}
.portal-menu-panel {{
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 20;
  min-width: 12.5rem;
  padding: 0.35rem 0;
  background: var(--card-b);
  border: 1px solid var(--border-b);
  border-radius: 10px;
  box-shadow: 0 4px 14px rgba(20, 32, 51, 0.12);
}}
.portal-menu-panel[hidden] {{
  display: none !important;
}}
.portal-menu-item {{
  display: block;
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  color: var(--text-b);
  text-decoration: none;
  border: 0;
  background: transparent;
  width: 100%;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
}}
a.portal-menu-item:hover,
a.portal-menu-item:focus-visible {{
  background: var(--bg-b);
  outline: none;
}}
.portal-menu-soon {{
  color: var(--muted-b);
  cursor: default;
}}
.intro {{
  font-size: 0.95rem;
  color: var(--muted-b);
  margin: 0 0 1.25rem;
  padding: 0.85rem 1rem;
  background: var(--card-b);
  border-radius: 10px;
  border: 1px solid var(--border-b);
}}
.lead {{
  font-weight: 600;
  color: var(--text-b);
  margin-bottom: 0.35rem;
}}
.card-list {{
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}}
.card {{
  background: var(--card-b);
  border: 1px solid var(--border-b);
  border-radius: 12px;
  padding: 1rem 1rem 1rem;
  box-shadow: 0 1px 3px rgba(20, 32, 51, 0.06);
}}
.card-title {{
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0 0 0.85rem;
  line-height: 1.35;
  word-break: break-word;
}}
.card a.btn {{
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  text-decoration: none;
  font-weight: 600;
  font-size: 1rem;
  color: #fff;
  background: var(--accent-b);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  min-height: 48px;
  line-height: 1.2;
}}
.card a.btn:active,
.card a.btn:hover {{
  background: var(--accent-b-hover);
}}
.footer-note {{
  margin-top: 1.5rem;
  font-size: 0.82rem;
  color: var(--muted-b);
  text-align: center;
}}
</style>
</head>
<body>
  <header class="portal-header">
    <div class="portal-header-row">
      <h1 class="portal-title">現場共有ポータル</h1>
      <div class="portal-menu-wrap">
        <button type="button" class="portal-menu-btn" id="portal-menu-btn" aria-expanded="false" aria-haspopup="true" aria-controls="portal-menu-panel">
          <span class="portal-menu-icon" aria-hidden="true">☰</span>
          <span class="portal-menu-label">メニュー</span>
        </button>
        <nav id="portal-menu-panel" class="portal-menu-panel" role="menu" hidden>
          <a class="portal-menu-item" role="menuitem" href="./">ポータルTOP</a>
          <a class="portal-menu-item" role="menuitem" href="./ui_samples/">UIサンプル</a>
          <a class="portal-menu-item" role="menuitem" href="./archive/">アーカイブ</a>
        </nav>
      </div>
    </div>
  </header>

  <div class="intro">
    <p class="lead">このページは現場共有ページへの入口です。</p>
    <p style="margin:0">今日・今週の作業内容は、次のリンクから日付ごとの共有ページを開いて確認してください。スマホのブックマークに登録して使えます。</p>
  </div>

  <div class="card-list" role="list">
{cards_str}
  </div>

  <p class="footer-note">このページは <code>scripts/generate_portal.py</code> で再生成できます。</p>
  <script>
(function () {{
  var btn = document.getElementById("portal-menu-btn");
  var panel = document.getElementById("portal-menu-panel");
  if (!btn || !panel) return;
  function setOpen(open) {{
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  }}
  btn.addEventListener("click", function (ev) {{
    ev.stopPropagation();
    setOpen(panel.hidden);
  }});
  document.addEventListener("click", function () {{
    setOpen(false);
  }});
  panel.addEventListener("click", function (ev) {{
    ev.stopPropagation();
  }});
  document.addEventListener("keydown", function (ev) {{
    if (ev.key === "Escape") setOpen(false);
  }});
}})();
  </script>
</body>
</html>
"""


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    share_dir = repo_root / "share"
    if not share_dir.is_dir():
        print(f"Missing directory: {share_dir}", file=sys.stderr)
        return 1

    rows: list[tuple[str, Path]] = []
    for sub in sorted(share_dir.iterdir(), key=lambda p: p.name):
        if not sub.is_dir():
            continue
        if sub.name.lower() == "sample":
            continue
        idx = sub / "index.html"
        if not idx.is_file():
            continue
        rows.append((sub.name, idx))

    rows.sort(key=lambda x: sort_key(x[0]))

    entries: list[tuple[str, str]] = []
    archive_parts: list[tuple[str, ShareSummary]] = []
    for folder, path in rows:
        html_text = path.read_text(encoding="utf-8", errors="replace")
        date_line = card_heading(folder, path)
        summary = summarize_share_html(html_text, folder)
        heading = build_portal_heading(date_line, summary)
        entries.append((folder, heading))
        if re.fullmatch(r"\d{6}", folder):
            archive_parts.append((folder, summary))

    out = build_html(entries)
    out_path = repo_root / "portal" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8", newline="\n")
    print(f"Wrote {out_path} ({len(entries)} cards)")

    sections = group_archive_sections(archive_parts)
    arch_html = build_archive_html(sections)
    arch_path = repo_root / "portal" / "archive" / "index.html"
    arch_path.parent.mkdir(parents=True, exist_ok=True)
    arch_path.write_text(arch_html, encoding="utf-8", newline="\n")
    print(
        f"Wrote {arch_path} ({len(archive_parts)} dates, {len(sections)} months)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
