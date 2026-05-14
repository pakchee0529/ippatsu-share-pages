#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan share/<date>/index.html and regenerate portal/index.html and portal/archive/index.html (stdlib only).

ポータルTOPのカードは share 配下の従来どおり。アーカイブは portal/archive_manifest.json の entries
に登録された6桁日付のみ。アーカイブ一覧・各日付の詳細ページは manifest を正本とし、share が無い日付も
一覧・詳細に出せる（共有ページ削除後もアーカイブ詳細でサマリを残すため）。

portal/archive/<YYMMDD>/ は generate 時に manifest 済み分へ上書き生成する。manifest から date が消えた
古い YYMMDD ディレクトリは自動では削除しない（孤立が残る）。必要なら生成前に 6 桁名フォルダだけ手で整理する。
"""

from __future__ import annotations

import html as html_lib
import json
import re
import sys
from urllib.parse import parse_qs, quote, urlencode, urlparse
from dataclasses import dataclass
from datetime import date, timedelta
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

# ---------------------------------------------------------------------------
# 現調結果報告（Googleフォーム）— 正式URL・entry ID 確定後に差し替え
# プレースホルダ: viewform まで含め、クエリは仮パラメータ（management_no / label /
# report_type / report_date）。正式 prefill は entry.xxxxx= に置き換え可能。
# ---------------------------------------------------------------------------
SURVEY_REPORT_FORM_URL = (
    "https://docs.google.com/forms/d/e/FORM_ID_PLACEHOLDER/viewform"
)
# URL 上の報告種別（ボタン文言は別）。フォーム側マッピング用。
SURVEY_REPORT_TYPE_COMPLETED = "survey_completed"
SURVEY_REPORT_TYPE_RETURN_CANDIDATE = "return_candidate"


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


def build_survey_report_url(
    base_url: str,
    management_no: str,
    label: str,
    report_type: str,
    report_date_iso: str,
) -> str:
    """Googleフォームへ渡すクエリを付与（仮パラメータ。entry ID 確定後は URL 組み立てを差し替え）。"""
    b = (base_url or "").strip() or SURVEY_REPORT_FORM_URL
    params = {
        "management_no": management_no,
        "label": label,
        "report_type": report_type,
    }
    if report_date_iso:
        params["report_date"] = report_date_iso
    q = urlencode(params, quote_via=quote, safe="")
    joiner = "&" if "?" in b else "?"
    return f"{b.rstrip('?')}{joiner}{q}"


def month_heading_key(folder: str) -> tuple[int, int] | None:
    """6桁 YYMMDD から (西暦年, 月)。"""
    if not re.fullmatch(r"\d{6}", folder):
        return None
    yy, mm = int(folder[0:2]), int(folder[2:4])
    return (2000 + yy, mm)


def month_label_from_key(year: int, month: int) -> str:
    return f"{year}年{month:02d}月"


def group_archive_sections(
    parts: list[tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]],
) -> list[
    tuple[
        tuple[int, int],
        str,
        list[tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]],
    ]
]:
    """月新しい順。各月内は日付キー新しい順。"""
    from collections import defaultdict

    buckets: dict[
        tuple[int, int], list[tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]]
    ] = defaultdict(list)
    for entry, summary, public_items in parts:
        folder = entry.date
        mk = month_heading_key(folder)
        if mk is None:
            continue
        buckets[mk].append((entry, summary, public_items))
    keys = sorted(buckets.keys(), reverse=True)
    out: list[
        tuple[
            tuple[int, int],
            str,
            list[tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]],
        ]
    ] = []
    for y, m in keys:
        label = month_label_from_key(y, m)
        items = sorted(buckets[(y, m)], key=lambda t: sort_key(t[0].date), reverse=True)
        out.append(((y, m), label, items))
    return out


def _coerce_manifest_int(val: object) -> int | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float) and val == int(val):
        return int(val)
    if isinstance(val, str):
        s = val.strip()
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            try:
                return int(s)
            except ValueError:
                return None
    return None


def _strip_opt_str(val: object) -> str | None:
    if val is None:
        return None
    if not isinstance(val, str):
        return None
    s = val.strip()
    return s or None


@dataclass(frozen=True)
class ManifestEntry:
    """アーカイブ manifest の1件。

    entries に ``items`` があっても詳細ページでは列挙しない（公開サマリのみ）。
    """

    date: str
    title: str | None = None
    item_count: int | None = None
    completed_count: int | None = None
    incomplete_count: int | None = None
    reported_at: str | None = None
    href: str | None = None
    display_suffix: str | None = None


@dataclass(frozen=True)
class ArchivePublicItem:
    management_no: str
    label: str
    completion_status: str
    incomplete_reason: str
    map_url: str
    start_lat: str
    start_lng: str
    end_lat: str
    end_lng: str
    method: str
    branch_cut_total: int
    root_cut_total: int
    brush_area_m2: str
    bamboo_count: str
    vine_locations: str
    road_width_m: str
    bucket_available: str
    crane_required: str
    warning: str
    note: str


@dataclass(frozen=True)
class SurveyPublicItem:
    management_no: str
    label: str
    map_url: str
    start_label: str
    start_lat: str
    start_lng: str
    end_label: str
    end_lat: str
    end_lng: str
    note: str


@dataclass(frozen=True)
class ArchiveRowContext:
    span_summary: str
    status_summary: str
    search_blob: str
    item_count: int


def _manifest_entry_from_dict(d: dict) -> ManifestEntry | None:
    raw_date = d.get("date")
    if not isinstance(raw_date, str) or not re.fullmatch(r"\d{6}", raw_date.strip()):
        return None
    date = raw_date.strip()
    return ManifestEntry(
        date=date,
        title=_strip_opt_str(d.get("title")),
        item_count=_coerce_manifest_int(d.get("item_count")),
        completed_count=_coerce_manifest_int(d.get("completed_count")),
        incomplete_count=_coerce_manifest_int(d.get("incomplete_count")),
        reported_at=_strip_opt_str(d.get("reported_at")),
        href=_strip_opt_str(d.get("href")),
        display_suffix=_strip_opt_str(d.get("display_suffix")),
    )


def load_archive_manifest_entries(repo_root: Path) -> list[ManifestEntry]:
    """portal/archive_manifest.json の entries を ManifestEntry として返す（重複 date は先頭優先）。"""
    path = repo_root / "portal" / "archive_manifest.json"
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: could not read archive_manifest.json: {e}", file=sys.stderr)
        return []
    if not isinstance(raw, dict):
        print("Warning: archive_manifest.json root must be an object", file=sys.stderr)
        return []
    entries = raw.get("entries")
    if entries is None:
        return []
    if not isinstance(entries, list):
        print("Warning: archive_manifest.json 'entries' must be an array", file=sys.stderr)
        return []
    seen: set[str] = set()
    out: list[ManifestEntry] = []
    for ent in entries:
        me: ManifestEntry | None = None
        if isinstance(ent, str) and re.fullmatch(r"\d{6}", ent.strip()):
            me = ManifestEntry(date=ent.strip())
        elif isinstance(ent, dict):
            me = _manifest_entry_from_dict(ent)
        if me is None:
            continue
        if me.date in seen:
            continue
        seen.add(me.date)
        out.append(me)
    out.sort(key=lambda e: int(e.date), reverse=True)
    return out


def folder_to_calendar_date(folder: str) -> date | None:
    """6桁 YYMMDD を 20YY-MM-DD の暦日として解釈。無効日付は None。"""
    if not re.fullmatch(r"\d{6}", folder):
        return None
    yy, mm, dd = int(folder[0:2]), int(folder[2:4]), int(folder[4:6])
    y = 2000 + yy
    try:
        return date(y, mm, dd)
    except ValueError:
        return None


def is_in_last_seven_days(folder: str, today: date) -> bool:
    """今日を含み、今日以前7日以内（6日より前は除外）。"""
    d = folder_to_calendar_date(folder)
    if d is None:
        return False
    if d > today:
        return False
    return (today - d) <= timedelta(days=6)


def archive_row_search_blob(
    folder: str,
    date_jp: str,
    span_summary: str,
    status_summary: str,
    search_tokens: list[str],
) -> str:
    """検索用文字列。冠称名/径間名/管理番号/状態/理由を優先。"""
    bits = [folder, date_jp, span_summary, status_summary]
    bits.extend(search_tokens)
    return " ".join(b for b in bits if str(b).strip())


def _norm_for_search(s: str) -> str:
    t = (s or "").strip()
    if not t:
        return ""
    t = t.replace("～", "-").replace("〜", "-").replace("ー", "-")
    t = t.replace("　", " ").replace("\t", " ")
    return t


def build_archive_row_context(
    entry: ManifestEntry,
    share_summary: ShareSummary | None,
    public_items: list[ArchivePublicItem] | None,
) -> ArchiveRowContext:
    labels: list[str] = []
    tokens: list[str] = []
    completed = 0
    incomplete = 0
    if public_items:
        for it in public_items:
            lb = (it.label or "").strip()
            if lb:
                labels.append(lb)
                tokens.append(lb)
                n = _norm_for_search(lb)
                if n and n != lb:
                    tokens.append(n)
            mno = (it.management_no or "").strip()
            if mno:
                tokens.append(mno)
                tokens.append(mno.replace(" ", ""))
            st = (it.completion_status or "").strip()
            if st:
                if st == "completed":
                    completed += 1
                    tokens.append("完了")
                elif st == "incomplete":
                    incomplete += 1
                    tokens.append("未完了")
            rs = (it.incomplete_reason or "").strip()
            if rs and rs != "—":
                tokens.append(rs)
    uniq_labels: list[str] = []
    seen = set()
    for lb in labels:
        if lb in seen:
            continue
        seen.add(lb)
        uniq_labels.append(lb)
    span_summary = "—"
    if uniq_labels:
        show_n = 4
        head = ", ".join(uniq_labels[:show_n])
        rest = len(uniq_labels) - show_n
        span_summary = f"{head} ほか{rest}件" if rest > 0 else head
    elif share_summary and share_summary.crown_names:
        span_summary = format_crown_summary(share_summary.crown_names)
    item_n = (
        entry.item_count
        if entry.item_count is not None
        else (len(public_items) if public_items else (share_summary.item_count if share_summary else 0))
    )
    if entry.completed_count is not None:
        completed = entry.completed_count
    if entry.incomplete_count is not None:
        incomplete = entry.incomplete_count
    status_summary = f"完了{completed} / 未完了{incomplete}"
    return ArchiveRowContext(
        span_summary=span_summary,
        status_summary=status_summary,
        search_blob=archive_row_search_blob(
            entry.date,
            fallback_heading(entry.date),
            span_summary,
            status_summary,
            tokens,
        ),
        item_count=item_n,
    )


def format_archive_row_article(
    entry: ManifestEntry,
    share_summary: ShareSummary | None,
    public_items: list[ArchivePublicItem] | None,
) -> str:
    """1行分のアーカイブカード（data-search 付き）。主リンクはアーカイブ詳細 ./<date>/ 。"""
    folder = entry.date
    date_jp = fallback_heading(folder)
    ctx = build_archive_row_context(entry, share_summary, public_items)
    search_attr = escape_html(ctx.search_blob)
    href = f"./{folder}/"
    return f"""    <article class="archive-row" data-search="{search_attr}">
      <div class="archive-row-top">
        <div class="archive-main">{escape_html(ctx.span_summary)}</div>
        <div class="archive-count">{ctx.item_count}件</div>
      </div>
      <div class="archive-meta">{escape_html(date_jp)} <span class="archive-dkey">({escape_html(folder)})</span></div>
      <div class="archive-status">{escape_html(ctx.status_summary)}</div>
      <a class="btn btn-archive" href="{escape_html(href)}">アーカイブ詳細を開く</a>
    </article>"""


def build_archive_html(
    recent_parts: list[tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]],
    sections: list[
        tuple[
            tuple[int, int],
            str,
            list[tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]],
        ]
    ],
) -> str:
    """直近7日 + 月別 details（検索付き）。recent と月別で同一現場は重複しない。"""
    recent_rows_str = "\n".join(
        format_archive_row_article(e, s, p) for e, s, p in recent_parts
    )
    recent_empty_hidden = " hidden" if recent_parts else ""
    month_blocks: list[str] = []
    for (y, m), month_label, items in sections:
        mid = f"m-{y:04d}-{m:02d}"
        rows_str = "\n".join(
            format_archive_row_article(entry, summary, public_items)
            for entry, summary, public_items in items
        )
        month_blocks.append(
            f"""    <details class="month-archive" id="{escape_html(mid)}">
      <summary class="month-summary">{escape_html(month_label)}</summary>
      <div class="archive-list" role="list">
{rows_str}
      </div>
    </details>"""
        )
    months_str = "\n".join(month_blocks) if month_blocks else ""
    monthly_empty_note = ""
    if not months_str:
        monthly_empty_note = (
            '    <p class="empty-note" id="monthly-empty-build">'
            "月別アーカイブに表示する現場はありません。</p>\n"
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
.disclaimer-note {{
  font-size: 0.8rem;
  color: var(--muted-b);
  margin: 0 0 0.5rem;
  line-height: 1.45;
}}
.section-title {{
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0 0 0.45rem;
  color: var(--text-b);
}}
.recent-block {{
  margin-bottom: 1.15rem;
}}
.monthly-block {{
  margin-bottom: 0.5rem;
}}
.monthly-block > .section-title {{
  margin-bottom: 0.5rem;
}}
#archive-months {{
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}}
.month-archive {{
  background: var(--card-b);
  border: 1px solid var(--border-b);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(20, 32, 51, 0.05);
}}
.month-summary {{
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
  padding: 0.65rem 0.75rem;
  min-height: 44px;
  display: flex;
  align-items: center;
  cursor: pointer;
  list-style: none;
}}
.month-summary::-webkit-details-marker {{
  display: none;
}}
.month-archive .archive-list {{
  padding: 0 0.65rem 0.65rem;
  gap: 0.5rem;
}}
.recent-block .archive-row {{
  padding: 0.55rem 0.65rem;
}}
.recent-block a.btn-archive {{
  padding: 0.5rem 0.65rem;
  font-size: 0.92rem;
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
.archive-main {{
  font-size: 0.96rem;
  font-weight: 700;
  color: var(--text-b);
  margin: 0 0 0.2rem;
  line-height: 1.35;
  word-break: break-word;
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
.archive-meta {{
  font-size: 0.88rem;
  color: var(--muted-b);
  margin-bottom: 0.35rem;
  word-break: break-word;
}}
.archive-status {{
  font-size: 0.84rem;
  color: var(--text-b);
  margin-bottom: 0.45rem;
  font-weight: 600;
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
    <a href="../survey/">現調待ち</a>
    <a href="./">アーカイブ</a>
  </nav>
  <h1>現場共有アーカイブ</h1>
  <p class="disclaimer-note">表示対象は <code>portal/archive_manifest.json</code> の <code>entries</code> に登録した6桁日付のみです。個人情報・次回確認メモ・地主情報などはマニフェストに書き込まないでください。</p>
  <p class="lead">冠称名・径間名・管理番号で過去現場を検索できます。直近7日分は「最近1週間」、それ以前は月別に表示します。</p>
  <div class="search-wrap">
    <label for="archive-search" class="visually-hidden">検索</label>
    <input type="search" id="archive-search" placeholder="冠称名・径間名・管理番号で検索（例: 小川 / 百谷 / 51401376）" autocomplete="off">
  </div>
  <section class="recent-block" id="archive-recent" aria-labelledby="recent-h">
    <h2 class="section-title" id="recent-h">最近1週間</h2>
    <div id="recent-rows" class="archive-list" role="list">
{recent_rows_str}
    </div>
    <p id="recent-empty-build" class="empty-note"{recent_empty_hidden}>最近1週間の現場はありません。</p>
    <p id="recent-search-empty" class="empty-note" hidden>最近1週間の範囲に、検索に一致する現場はありません。</p>
  </section>
  <section class="monthly-block" id="archive-monthly-wrap" aria-labelledby="monthly-h">
    <h2 class="section-title" id="monthly-h">月別アーカイブ</h2>
    <div id="archive-months">
{months_str}
{monthly_empty_note}    <p id="monthly-search-empty" class="empty-note" hidden>月別アーカイブに、検索に一致する現場はありません。</p>
    </div>
  </section>
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
    rows.forEach(function (row) {{
      var hay = norm(row.getAttribute("data-search") || "");
      var show = !q || hay.indexOf(q) >= 0;
      row.style.display = show ? "" : "none";
    }});
    var recentBlock = document.getElementById("archive-recent");
    var recentSearchEmpty = document.getElementById("recent-search-empty");
    if (recentBlock && recentSearchEmpty) {{
      var recentRows = recentBlock.querySelectorAll(".archive-row");
      var recentVis = 0;
      recentRows.forEach(function (r) {{
        if (r.style.display !== "none") recentVis++;
      }});
      var showRecentSearchEmpty = q && recentRows.length > 0 && recentVis === 0;
      recentSearchEmpty.hidden = !showRecentSearchEmpty;
    }}
    var monthDetails = document.querySelectorAll("details.month-archive");
    monthDetails.forEach(function (det) {{
      var vis = false;
      det.querySelectorAll(".archive-row").forEach(function (r) {{
        if (r.style.display !== "none") vis = true;
      }});
      det.style.display = vis ? "" : "none";
      if (q) {{
        if (vis) det.open = true;
      }} else {{
        det.open = false;
      }}
    }});
    var mSearchEmpty = document.getElementById("monthly-search-empty");
    if (mSearchEmpty && monthDetails.length) {{
      var anyMonthOpen = false;
      monthDetails.forEach(function (d) {{
        if (d.style.display !== "none") anyMonthOpen = true;
      }});
      mSearchEmpty.hidden = !(q && !anyMonthOpen);
    }}
  }}
  input.addEventListener("input", apply);
  input.addEventListener("search", apply);
}})();
  </script>
</body>
</html>
"""


def sanitize_manifest_href(href: str | None) -> str | None:
    """詳細ページに埋め込む href の最低限の検証（スクリプト系・改行を拒否）。"""
    if href is None:
        return None
    h = href.strip()
    if not h:
        return None
    low = h.lower()
    if low.startswith(("javascript:", "data:", "vbscript:")):
        return None
    if re.search(r"[\n\r<>\x00]", h):
        return None
    return h


def _fmt_count_cell(val: int | None) -> str:
    if val is None:
        return f'<span class="missing">—</span>'
    return escape_html(str(val))


def _as_num(v: object) -> int:
    if isinstance(v, bool):
        return 0
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            try:
                return int(s)
            except ValueError:
                return 0
    return 0


def _to_str(v: object) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _yes_no_jp(v: object) -> str:
    if isinstance(v, bool):
        return "可" if v else "不可"
    s = _to_str(v).lower()
    if s in {"true", "1", "yes", "y"}:
        return "可"
    if s in {"false", "0", "no", "n"}:
        return "不可"
    return "—"


def _cut_totals(src: dict) -> tuple[int, int]:
    branch_keys = [
        "branch_cut_under_10",
        "branch_cut_10_20",
        "branch_cut_20_30",
        "branch_cut_30_40",
        "branch_cut_40_50",
        "branch_cut_over_50",
    ]
    root_keys = [
        "root_cut_under_10",
        "root_cut_10_20",
        "root_cut_20_30",
        "root_cut_30_40",
        "root_cut_40_50",
        "root_cut_over_50",
    ]
    b = sum(_as_num(src.get(k)) for k in branch_keys)
    r = sum(_as_num(src.get(k)) for k in root_keys)
    return b, r


def _method_text(src: dict) -> str:
    carry = bool(src.get("carry_out"))
    collect = bool(src.get("collect"))
    if carry and collect:
        return "持出・集積"
    if carry:
        return "持出"
    if collect:
        return "集積"
    return "—"


def _completion_reports_root(repo_root: Path) -> Path:
    return repo_root.parent / "ippatsu-pc" / "data" / "completion_reports"


def _survey_source_path(repo_root: Path) -> Path:
    return repo_root.parent / "ippatsu-pc" / "data" / "share" / "261231.json"


def _parse_latlng_from_map_url(url: str) -> tuple[str, str]:
    u = urlparse(url)
    q = parse_qs(u.query or "")
    loc = ""
    if "q" in q and q["q"]:
        loc = q["q"][0]
    if not loc:
        return "", ""
    parts = [p.strip() for p in loc.split(",", 1)]
    if len(parts) != 2:
        return "", ""
    return parts[0], parts[1]


def _pick_item_latlng(item: ArchivePublicItem) -> tuple[str, str]:
    if item.start_lat and item.start_lng:
        return item.start_lat, item.start_lng
    if item.end_lat and item.end_lng:
        return item.end_lat, item.end_lng
    if item.map_url:
        a, b = _parse_latlng_from_map_url(item.map_url)
        if a and b:
            return a, b
    return "", ""


def _pick_survey_item_latlng(item: SurveyPublicItem) -> tuple[str, str]:
    if item.start_lat and item.start_lng:
        return item.start_lat, item.start_lng
    if item.end_lat and item.end_lng:
        return item.end_lat, item.end_lng
    if item.map_url:
        a, b = _parse_latlng_from_map_url(item.map_url)
        if a and b:
            return a, b
    return "", ""


def build_multi_pin_map_url(items: list[ArchivePublicItem]) -> str:
    pts: list[tuple[str, str]] = []
    seen: set[str] = set()
    for it in items:
        a, b = _pick_item_latlng(it)
        if not a or not b:
            continue
        k = f"{a},{b}"
        if k in seen:
            continue
        seen.add(k)
        pts.append((a, b))
    if len(pts) < 2:
        return ""
    # Google Maps directions (multi pin approximation). destination + up to 9 waypoints.
    use = pts[:10]
    destination = f"{use[-1][0]},{use[-1][1]}"
    waypoints = "|".join(f"{a},{b}" for a, b in use[:-1])
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&destination={destination}&waypoints={waypoints}"
    )


def load_archive_public_items(
    repo_root: Path, date_key: str
) -> tuple[list[ArchivePublicItem] | None, str]:
    """ippatsu-pc 側 completion_reports から公開可能項目のみ抽出する。"""
    base = _completion_reports_root(repo_root)
    path = base / f"{date_key}.json"
    if not path.is_file():
        return None, "詳細な現場一覧は未生成です（completion_reports が見つかりません）。"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "詳細な現場一覧は未生成です（completion_reports の読み込みに失敗）。"
    if not isinstance(raw, dict):
        return None, "詳細な現場一覧は未生成です（completion_reports 形式不正）。"
    items = raw.get("items")
    if not isinstance(items, list):
        return None, "詳細な現場一覧は未生成です（items 配列なし）。"
    out: list[ArchivePublicItem] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        src = it.get("source_item")
        if not isinstance(src, dict):
            src = {}
        b_total, r_total = _cut_totals(src)
        status = _to_str(it.get("completion_status")).lower()
        if status not in {"completed", "incomplete"}:
            status = "—"
        out.append(
            ArchivePublicItem(
                management_no=_to_str(src.get("management_no") or it.get("management_no")) or "—",
                label=_to_str(src.get("label") or it.get("label")) or "—",
                completion_status=status,
                incomplete_reason=_to_str(it.get("incomplete_reason")) or "—",
                map_url=_to_str(src.get("map_url")),
                start_lat=_to_str(src.get("start_lat")),
                start_lng=_to_str(src.get("start_lng")),
                end_lat=_to_str(src.get("end_lat")),
                end_lng=_to_str(src.get("end_lng")),
                method=_method_text(src),
                branch_cut_total=b_total,
                root_cut_total=r_total,
                brush_area_m2=_to_str(src.get("brush_area_m2")) or "—",
                bamboo_count=_to_str(src.get("bamboo_count")) or "—",
                vine_locations=_to_str(src.get("vine_locations")) or "—",
                road_width_m=_to_str(src.get("road_width_m")) or "—",
                bucket_available=_yes_no_jp(src.get("bucket_available")),
                crane_required=_yes_no_jp(src.get("crane_required")),
                warning=_to_str(src.get("warning")) or "—",
                note=_to_str(src.get("note")) or "—",
            )
        )
    return out, ""


def _to_float(v: str) -> float | None:
    s = (v or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_survey_public_items(repo_root: Path) -> tuple[list[SurveyPublicItem], str]:
    """ippatsu-pc 側 share/261231.json を読み、公開可能項目だけ抽出する。"""
    path = _survey_source_path(repo_root)
    if not path.is_file():
        return [], "現調待ちリストはまだありません。"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], "現調待ちリストはまだありません。"
    if not isinstance(raw, dict):
        return [], "現調待ちリストはまだありません。"
    items = raw.get("items")
    if not isinstance(items, list):
        return [], "現調待ちリストはまだありません。"
    out: list[SurveyPublicItem] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(
            SurveyPublicItem(
                management_no=_to_str(it.get("management_no")) or "—",
                label=_to_str(it.get("label")) or "—",
                map_url=_to_str(it.get("map_url")),
                start_label=_to_str(it.get("start_label")),
                start_lat=_to_str(it.get("start_lat")),
                start_lng=_to_str(it.get("start_lng")),
                end_label=_to_str(it.get("end_label")),
                end_lat=_to_str(it.get("end_lat")),
                end_lng=_to_str(it.get("end_lng")),
                note=_to_str(it.get("note")) or "—",
            )
        )
    return out, ""


def build_survey_html(
    items: list[SurveyPublicItem],
    empty_note: str,
    report_date_iso: str,
    form_base_url: str = SURVEY_REPORT_FORM_URL,
) -> str:
    cards: list[str] = []
    points: list[dict] = []
    for idx, it in enumerate(items):
        map_btn = ""
        if it.map_url and it.map_url.startswith(("http://", "https://")):
            map_btn = (
                f'<a class="btn btn-map" href="{escape_html(it.map_url)}" '
                'target="_blank" rel="noopener noreferrer">地図を開く</a>'
            )
        two_btn = ""
        two_json = ""
        two_wrap = ""
        start_lat = _to_float(it.start_lat)
        start_lng = _to_float(it.start_lng)
        end_lat = _to_float(it.end_lat)
        end_lng = _to_float(it.end_lng)
        if (
            start_lat is not None
            and start_lng is not None
            and end_lat is not None
            and end_lng is not None
        ):
            two_json_id = f"two-geo-{idx}"
            two_wrap_id = f"two-wrap-{idx}"
            two_map_id = f"share-two-map-{idx}"
            two_btn = (
                f'<button type="button" class="btn btn-map" data-two-open '
                f'data-two-wrap="{two_wrap_id}" data-two-map="{two_map_id}" '
                f'data-two-json="{two_json_id}" aria-expanded="false" '
                f'aria-controls="{two_wrap_id}">2点地図を開く</button>'
            )
            two_geo = {
                "a": {"name": it.start_label or it.label, "lat": start_lat, "lng": start_lng},
                "b": {"name": it.end_label or it.label, "lat": end_lat, "lng": end_lng},
            }
            two_json = (
                f'<script type="application/json" id="{two_json_id}">'
                f'{escape_html(json.dumps(two_geo, ensure_ascii=False))}</script>'
            )
            two_wrap = (
                f'<div class="two-map-wrap" id="{two_wrap_id}" hidden>'
                f'<div id="{two_map_id}" class="share-two-map-canvas" '
                'role="application" aria-label="2点地図"></div></div>'
            )
        note_id = f"note-{idx}"
        note_btn = (
            f'<button type="button" class="btn btn-note" aria-expanded="false" '
            f'aria-controls="{note_id}" data-note-toggle>現場指示</button>'
        )
        note_body = f"備考: {escape_html(it.note)}"
        actions = "".join(x for x in [map_btn, two_btn, note_btn] if x)
        url_done = build_survey_report_url(
            form_base_url,
            it.management_no,
            it.label,
            SURVEY_REPORT_TYPE_COMPLETED,
            report_date_iso,
        )
        url_return = build_survey_report_url(
            form_base_url,
            it.management_no,
            it.label,
            SURVEY_REPORT_TYPE_RETURN_CANDIDATE,
            report_date_iso,
        )
        report_btns = (
            f'<div class="card-actions card-actions-report" role="group" '
            f'aria-label="現調結果の報告">'
            f'<a class="btn btn-report-done" href="{escape_html(url_done)}" '
            f'target="_blank" rel="noopener noreferrer">現調済みを報告</a>'
            f'<a class="btn btn-report-return" href="{escape_html(url_return)}" '
            f'target="_blank" rel="noopener noreferrer">返却候補を報告</a>'
            f"</div>"
        )
        cards.append(
            f"""<article class="card" data-card-index="{idx}">
  <div class="card-head">
    <h2 class="card-title">{escape_html(it.label)}</h2>
    <p class="item-mgmt">{escape_html(it.management_no)}</p>
    <div class="card-actions">{actions}</div>
    {report_btns}
  </div>
  {two_json}
  {two_wrap}
  <div class="note-panel" id="{note_id}" hidden>{note_body}</div>
</article>"""
        )
        p_lat, p_lng = _pick_survey_item_latlng(it)
        f_lat = _to_float(p_lat)
        f_lng = _to_float(p_lng)
        if f_lat is not None and f_lng is not None:
            points.append(
                {
                    "name": it.label,
                    "lat": f_lat,
                    "lng": f_lng,
                    "management_no": it.management_no,
                }
            )
    items_html = "\n".join(cards)
    if not items_html:
        items_html = f'<p class="muted-tiny">{escape_html(empty_note)}</p>'
    if points:
        map_block = """  <section class="map-section" aria-labelledby="map-heading">
    <h2 id="map-heading">全体地図</h2>
    <div id="share-map" role="application" aria-label="全径間の位置"></div>
  </section>
"""
    else:
        map_block = """  <section class="map-section map-empty" aria-labelledby="map-heading">
    <h2 id="map-heading">全体地図</h2>
    <p class="muted-tiny">まとめて表示できる位置情報がありません。</p>
  </section>
"""
    points_js = json.dumps(points, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>現調待ち一覧</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
  crossorigin="">
<style>
:root {{
  --bg: #f4f5f7;
  --card: #fff;
  --text: #1a1a1a;
  --muted: #5c6370;
  --border: #e1e4e8;
  --accent: #2563eb;
  --accent2: #0d9488;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Hiragino Sans",
    "Noto Sans JP", sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  padding: 0.75rem 0.75rem 1.25rem;
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
  color: var(--accent);
  text-decoration: none;
  padding: 0.35rem 0.5rem;
  border-radius: 6px;
}}
.top-bar a:hover, .top-bar a:focus-visible {{
  text-decoration: underline;
  outline: none;
}}
.page-title {{
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 0.35rem;
  padding: 0.5rem 0;
  border-bottom: 2px solid var(--border);
}}
.lead {{
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
  color: var(--muted);
}}
.report-disclaimer {{
  margin: 0 0 0.75rem;
  padding: 0.55rem 0.65rem;
  font-size: 0.82rem;
  line-height: 1.45;
  color: var(--muted);
  background: #f1f5f9;
  border: 1px solid var(--border);
  border-radius: 8px;
}}
.card {{
  background: var(--card);
  border-radius: 10px;
  border: 1px solid var(--border);
  padding: 0.85rem 1rem;
  margin-bottom: 0.75rem;
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
}}
.item-mgmt {{
  margin: -0.15rem 0 0;
  font-size: 0.82rem;
  color: var(--muted);
  font-weight: 600;
}}
.card-head {{
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}}
.card-title {{
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0;
}}
.card-actions {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}}
.btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.45rem 0.75rem;
  font-size: 0.9rem;
  font-weight: 600;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  text-decoration: none;
  min-height: 40px;
  touch-action: manipulation;
}}
.btn-map {{
  background: var(--accent);
  color: #fff;
}}
.btn-map:hover, .btn-map:focus {{ filter: brightness(1.05); }}
.btn-note {{
  background: #fff;
  color: var(--accent2);
  border: 2px solid var(--accent2);
}}
.btn-note[aria-expanded="true"] {{
  background: var(--accent2);
  color: #fff;
}}
.note-panel {{
  margin-top: 0.65rem;
  padding: 0.65rem 0.75rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px dashed var(--border);
  font-size: 0.92rem;
  color: var(--text);
}}
.note-panel[hidden] {{ display: none !important; }}
.two-map-wrap {{
  margin-top: 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  overflow: hidden;
}}
.two-map-wrap[hidden] {{ display: none !important; }}
.share-two-map-canvas {{
  width: 100%;
  height: min(45vh, 320px);
  min-height: 200px;
}}
.leaflet-tooltip.two-tip {{
  font-weight: 600;
  font-size: 0.85rem;
  padding: 2px 6px;
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
}}
.map-section {{
  margin-top: 1.0rem;
  background: var(--card);
  border-radius: 10px;
  border: 1px solid var(--border);
  padding: 0.75rem 1rem 1rem;
  margin-bottom: 0.85rem;
}}
.map-section h2 {{
  font-size: 1.05rem;
  margin: 0 0 0.5rem;
}}
#share-map {{
  width: 100%;
  height: min(55vh, 420px);
  min-height: 220px;
  border-radius: 8px;
  border: 1px solid var(--border);
}}
.map-empty .muted-tiny {{
  margin: 0;
  font-size: 0.88rem;
  color: var(--muted);
}}
.leaflet-container {{ font-family: inherit; }}
.muted-tiny {{
  font-size: 0.88rem;
  color: var(--muted);
}}
.footer-note {{
  margin-top: 1.1rem;
  font-size: 0.8rem;
  color: var(--muted);
  text-align: center;
}}
@media (min-width: 480px) {{
  .card-head {{
    flex-direction: row;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
  }}
  .page-title {{ font-size: 1.4rem; }}
}}
.card-actions-report {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  flex-basis: 100%;
  width: 100%;
  margin-top: 0.35rem;
  padding-top: 0.55rem;
  border-top: 1px dashed var(--border);
}}
.card-actions-report .btn {{
  flex: 1 1 calc(50% - 0.25rem);
  min-width: 9.5rem;
  min-height: 44px;
  font-size: 0.88rem;
}}
.btn-report-done {{
  background: var(--accent);
  color: #fff;
}}
.btn-report-done:hover, .btn-report-done:focus-visible {{
  filter: brightness(1.05);
  outline: none;
}}
.btn-report-return {{
  background: #fffbeb;
  color: #92400e;
  border: 2px solid #f59e0b;
}}
.btn-report-return:hover, .btn-report-return:focus-visible {{
  background: #fef3c7;
  outline: none;
}}
</style>
</head>
<body>
  <nav class="top-bar" aria-label="サイト内リンク">
    <a href="../">ポータルTOP</a>
    <a href="./">現調待ち</a>
    <a href="../archive/">アーカイブ</a>
  </nav>
  <h1 class="page-title">現調待ち一覧</h1>
  <p class="lead">径間ごとに地図・現場指示・報告用のリンクがあります。</p>
  <p class="report-disclaimer">報告ボタンは Google フォームに送信します。送信後、PC側で確認して反映します。押しただけではこの一覧から消えません。</p>
  <main>
{items_html}
{map_block}
  </main>
  <p class="footer-note">このページは <code>scripts/generate_portal.py</code> で再生成できます。</p>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
    crossorigin=""></script>
  <script>
(function () {{
  document.querySelectorAll("[data-note-toggle]").forEach(function(btn) {{
    var id = btn.getAttribute("aria-controls");
    var panel = id ? document.getElementById(id) : null;
    if (!panel) return;
    btn.addEventListener("click", function() {{
      var open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", open ? "false" : "true");
      panel.hidden = open;
    }});
  }});
  function gmaps(lat, lng) {{
    return "https://www.google.com/maps?q=" + encodeURIComponent(lat + "," + lng);
  }}
  var twoMaps = Object.create(null);
  document.querySelectorAll("[data-two-open]").forEach(function(btn) {{
    var wrapId = btn.getAttribute("data-two-wrap");
    var mapId = btn.getAttribute("data-two-map");
    var jsonId = btn.getAttribute("data-two-json");
    var wrap = wrapId ? document.getElementById(wrapId) : null;
    var jsonEl = jsonId ? document.getElementById(jsonId) : null;
    if (!wrap || !jsonEl) return;
    btn.addEventListener("click", function() {{
      var nowOpen = btn.getAttribute("aria-expanded") === "true";
      wrap.hidden = nowOpen;
      btn.setAttribute("aria-expanded", nowOpen ? "false" : "true");
      btn.textContent = nowOpen ? "2点地図を開く" : "2点地図を閉じる";
      if (nowOpen) return;
      var geo = null;
      try {{
        geo = JSON.parse(jsonEl.textContent || "{{}}");
      }} catch (e) {{
        return;
      }}
      if (!geo || !geo.a || !geo.b) return;
      var key = mapId;
      if (!twoMaps[key]) {{
        var mmap = L.map(mapId, {{ scrollWheelZoom: false }});
        twoMaps[key] = mmap;
        L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
          maxZoom: 19,
          attribution: "&copy; OpenStreetMap contributors",
        }}).addTo(mmap);
      }}
      var mmap = twoMaps[key];
      mmap.eachLayer(function(layer) {{
        if (layer instanceof L.Marker || layer instanceof L.Polyline) mmap.removeLayer(layer);
      }});
      function addPoint(p, cls) {{
        var lat = Number(p.lat), lng = Number(p.lng);
        if (!isFinite(lat) || !isFinite(lng)) return null;
        var m = L.marker([lat, lng]).addTo(mmap);
        if (p.name) m.bindTooltip(String(p.name), {{ permanent: true, direction: "top", className: cls }});
        m.on("click", function() {{ window.open(gmaps(lat, lng), "_blank", "noopener,noreferrer"); }});
        return [lat, lng];
      }}
      var a = addPoint(geo.a, "two-tip");
      var b = addPoint(geo.b, "two-tip");
      var pts = [];
      if (a) pts.push(a);
      if (b) pts.push(b);
      if (pts.length === 2) L.polyline(pts, {{ weight: 3, opacity: 0.8 }}).addTo(mmap);
      if (pts.length === 1) mmap.setView(pts[0], 15);
      else if (pts.length > 1) mmap.fitBounds(pts, {{ padding: [24, 24], maxZoom: 16 }});
      setTimeout(function() {{ mmap.invalidateSize(); }}, 60);
    }});
  }});
  var points = {points_js};
  var mapEl = document.getElementById("share-map");
  if (mapEl && Array.isArray(points) && points.length) {{
    var map = L.map("share-map", {{ scrollWheelZoom: false }});
    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }}).addTo(map);
    var bounds = [];
    points.forEach(function(p) {{
      var lat = Number(p.lat), lng = Number(p.lng);
      if (!isFinite(lat) || !isFinite(lng)) return;
      bounds.push([lat, lng]);
      var m = L.marker([lat, lng]).addTo(map);
      var label = (p.name || "現場") + (p.management_no ? (" (" + p.management_no + ")") : "");
      m.bindTooltip(label, {{ permanent: false, direction: "top" }});
    }});
    if (bounds.length === 1) map.setView(bounds[0], 15);
    else if (bounds.length > 1) map.fitBounds(bounds, {{ padding: [28, 28], maxZoom: 16 }});
  }}
}})();
  </script>
</body>
</html>
"""


def build_archive_detail_html(
    entry: ManifestEntry, public_items: list[ArchivePublicItem] | None, detail_note: str
) -> str:
    """アーカイブ詳細（公開可能項目のみ）。通常共有ページの構成へ合わせる。"""
    folder = entry.date
    date_jp = fallback_heading(folder)
    title_disp = entry.title.strip() if entry.title else date_jp
    items_html = ""
    points: list[dict] = []
    if public_items is None:
        items_html = f'<p class="muted-tiny">{escape_html(detail_note)}</p>'
    elif not public_items:
        items_html = '<p class="muted-tiny">この日の現場一覧はありません。</p>'
    else:
        cards: list[str] = []
        for idx, it in enumerate(public_items):
            map_btn = ""
            if it.map_url and it.map_url.startswith(("http://", "https://")):
                map_btn = (
                    f'<a class="btn btn-map" href="{escape_html(it.map_url)}" '
                    'target="_blank" rel="noopener noreferrer">地図を開く</a>'
                )
            start_lat = _to_float(it.start_lat)
            start_lng = _to_float(it.start_lng)
            end_lat = _to_float(it.end_lat)
            end_lng = _to_float(it.end_lng)
            two_btn = ""
            two_json = ""
            two_wrap = ""
            if (
                start_lat is not None
                and start_lng is not None
                and end_lat is not None
                and end_lng is not None
            ):
                two_json_id = f"two-geo-{idx}"
                two_wrap_id = f"two-wrap-{idx}"
                two_map_id = f"share-two-map-{idx}"
                two_btn = (
                    f'<button type="button" class="btn btn-map" data-two-open '
                    f'data-two-wrap="{two_wrap_id}" data-two-map="{two_map_id}" '
                    f'data-two-json="{two_json_id}" aria-expanded="false" '
                    f'aria-controls="{two_wrap_id}">2点地図を開く</button>'
                )
                two_geo = {
                    "a": {"name": it.label, "lat": start_lat, "lng": start_lng},
                    "b": {"name": it.label, "lat": end_lat, "lng": end_lng},
                }
                two_json = (
                    f'<script type="application/json" id="{two_json_id}">'
                    f'{escape_html(json.dumps(two_geo, ensure_ascii=False))}</script>'
                )
                two_wrap = (
                    f'<div class="two-map-wrap" id="{two_wrap_id}" hidden>'
                    f'<div id="{two_map_id}" class="share-two-map-canvas" '
                    'role="application" aria-label="2点地図"></div></div>'
                )

            note_id = f"note-{idx}"
            status_jp = (
                "完了"
                if it.completion_status == "completed"
                else "未完了"
                if it.completion_status == "incomplete"
                else "—"
            )
            reason_line = ""
            if it.completion_status == "incomplete" and it.incomplete_reason != "—":
                reason_line = f"<br>未完了理由: {escape_html(it.incomplete_reason)}"
            warn_line = "" if it.warning == "—" else f"<br>警告: {escape_html(it.warning)}"
            note_body = (
                f"状態: {escape_html(status_jp)}{reason_line}<br>"
                f"処理方法: {escape_html(it.method)}<br>"
                f"備考: {escape_html(it.note)}{warn_line}"
            )
            status_jp = (
                "完了"
                if it.completion_status == "completed"
                else "未完了"
                if it.completion_status == "incomplete"
                else it.completion_status
            )
            status_cls = (
                "status-done" if it.completion_status == "completed" else "status-pending"
            )
            note_btn = (
                f'<button type="button" class="btn btn-note" aria-expanded="false" '
                f'aria-controls="{note_id}" data-note-toggle>現場指示</button>'
            )
            actions = "".join(x for x in [map_btn, two_btn, note_btn] if x)
            cards.append(
                f"""<article class="card" data-card-index="{idx}">
      <div class="card-head">
        <h2 class="card-title">{escape_html(it.label)} <span class="status-pill {status_cls}">{escape_html(status_jp)}</span></h2>
        <p class="item-mgmt">{escape_html(it.management_no)}</p>
        <div class="card-actions">{actions}</div>
      </div>
      {two_json}
      {two_wrap}
      <div class="note-panel" id="{note_id}" hidden>{note_body}</div>
</article>"""
            )
            p_lat, p_lng = _pick_item_latlng(it)
            f_lat = _to_float(p_lat)
            f_lng = _to_float(p_lng)
            if f_lat is not None and f_lng is not None:
                points.append(
                    {
                        "name": it.label,
                        "lat": f_lat,
                        "lng": f_lng,
                        "management_no": it.management_no,
                    }
                )
        items_html = "\n".join(cards)
    map_block = ""
    if points:
        map_block = """  <section class="map-section" aria-labelledby="map-heading">
    <h2 id="map-heading">全体地図</h2>
    <div id="share-map" role="application" aria-label="全径間の位置"></div>
  </section>
"""
    else:
        map_block = """  <section class="map-section map-empty" aria-labelledby="map-heading">
    <h2 id="map-heading">全体地図</h2>
    <p class="muted-tiny">まとめて表示できる位置情報がありません。</p>
  </section>
"""
    points_js = json.dumps(points, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_html(folder)} · アーカイブ詳細</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
  crossorigin="">
<style>
:root {{
  --bg: #f4f5f7;
  --card: #fff;
  --text: #1a1a1a;
  --muted: #5c6370;
  --border: #e1e4e8;
  --accent: #2563eb;
  --accent2: #0d9488;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Hiragino Sans",
    "Noto Sans JP", sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  padding: 0.75rem 0.75rem 1.25rem;
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
  color: var(--accent);
  text-decoration: none;
  padding: 0.35rem 0.5rem;
  border-radius: 6px;
}}
.page-title {{
  font-size: 1.35rem;
  font-weight: 700;
  margin: 0 0 0.8rem;
  padding: 0.5rem 0;
  border-bottom: 2px solid var(--border);
}}
.disclaimer-note {{
  font-size: 0.76rem;
  color: var(--muted);
  margin: -0.35rem 0 0.85rem;
  line-height: 1.45;
}}
.card {{
  background: var(--card);
  border-radius: 10px;
  border: 1px solid var(--border);
  padding: 0.85rem 1rem;
  margin-bottom: 0.75rem;
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
}}
.card-done {{
  opacity: 0.78;
}}
.item-mgmt {{
  margin: -0.15rem 0 0;
  font-size: 0.82rem;
  color: var(--muted);
  font-weight: 600;
}}
.card-head {{
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}}
.card-title {{
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0;
}}
.status-pill {{
  font-size: 0.72rem;
  font-weight: 700;
  border-radius: 999px;
  padding: 0.1rem 0.45rem;
  margin-left: 0.35rem;
  vertical-align: baseline;
}}
.status-done {{
  color: #0f766e;
  background: #ecfeff;
  border: 1px solid #99f6e4;
}}
.status-pending {{
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
}}
.card-actions {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}}
.btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.45rem 0.75rem;
  font-size: 0.9rem;
  font-weight: 600;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  text-decoration: none;
  min-height: 40px;
  touch-action: manipulation;
}}
.btn-map {{
  background: var(--accent);
  color: #fff;
}}
.btn-map:hover, .btn-map:focus {{ filter: brightness(1.05); }}
.btn-note {{
  background: #fff;
  color: var(--accent2);
  border: 2px solid var(--accent2);
}}
.btn-note[aria-expanded="true"] {{
  background: var(--accent2);
  color: #fff;
}}
.note-panel {{
  margin-top: 0.65rem;
  padding: 0.65rem 0.75rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px dashed var(--border);
  font-size: 0.92rem;
  color: var(--text);
}}
.note-panel[hidden] {{ display: none !important; }}
.two-map-wrap {{
  margin-top: 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  overflow: hidden;
}}
.two-map-wrap[hidden] {{ display: none !important; }}
.share-two-map-canvas {{
  width: 100%;
  height: min(45vh, 320px);
  min-height: 200px;
}}
.leaflet-tooltip.two-tip {{
  font-weight: 600;
  font-size: 0.85rem;
  padding: 2px 6px;
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
}}
.map-section {{
  margin-top: 1.0rem;
  background: var(--card);
  border-radius: 10px;
  border: 1px solid var(--border);
  padding: 0.75rem 1rem 1rem;
  margin-bottom: 0.85rem;
}}
.map-section h2 {{
  font-size: 1.05rem;
  margin: 0 0 0.5rem;
}}
#share-map {{
  width: 100%;
  height: min(55vh, 420px);
  min-height: 220px;
  border-radius: 8px;
  border: 1px solid var(--border);
}}
.map-empty .muted-tiny {{
  margin: 0;
  font-size: 0.88rem;
  color: var(--muted);
}}
.leaflet-container {{ font-family: inherit; }}
.footer-note {{
  margin-top: 1.1rem;
  font-size: 0.8rem;
  color: var(--muted);
  text-align: center;
}}
@media (min-width: 480px) {{
  .card-head {{
    flex-direction: row;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
  }}
  .page-title {{ font-size: 1.4rem; }}
}}
</style>
</head>
<body>
  <nav class="top-bar" aria-label="サイト内リンク">
    <a href="../../">ポータルTOP</a>
    <a href="../">アーカイブ</a>
  </nav>
  <h1 class="page-title">{escape_html(date_jp)}</h1>
  <p class="disclaimer-note">完了報告アーカイブ / 個人情報・内部メモは表示していません。</p>
  <main>
{items_html}
{map_block}
  </main>
  <p class="footer-note">このページは <code>scripts/generate_portal.py</code> で再生成できます。</p>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
    crossorigin=""></script>
  <script>
(function () {{
  document.querySelectorAll("[data-note-toggle]").forEach(function(btn) {{
    var id = btn.getAttribute("aria-controls");
    var panel = id ? document.getElementById(id) : null;
    if (!panel) return;
    btn.addEventListener("click", function() {{
      var open = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", open ? "false" : "true");
      panel.hidden = open;
    }});
  }});

  function gmaps(lat, lng) {{
    return "https://www.google.com/maps?q=" + encodeURIComponent(lat + "," + lng);
  }}

  var twoMaps = Object.create(null);
  document.querySelectorAll("[data-two-open]").forEach(function(btn) {{
    var wrapId = btn.getAttribute("data-two-wrap");
    var mapId = btn.getAttribute("data-two-map");
    var jsonId = btn.getAttribute("data-two-json");
    var wrap = wrapId ? document.getElementById(wrapId) : null;
    var jsonEl = jsonId ? document.getElementById(jsonId) : null;
    if (!wrap || !jsonEl) return;
    btn.addEventListener("click", function() {{
      var nowOpen = btn.getAttribute("aria-expanded") === "true";
      wrap.hidden = nowOpen;
      btn.setAttribute("aria-expanded", nowOpen ? "false" : "true");
      btn.textContent = nowOpen ? "2点地図を開く" : "2点地図を閉じる";
      if (nowOpen) return;
      var geo = null;
      try {{
        geo = JSON.parse(jsonEl.textContent || "{{}}");
      }} catch (e) {{
        return;
      }}
      if (!geo || !geo.a || !geo.b) return;
      var key = mapId;
      if (!twoMaps[key]) {{
        var mmap = L.map(mapId, {{ scrollWheelZoom: false }});
        twoMaps[key] = mmap;
        L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
          maxZoom: 19,
          attribution: "&copy; OpenStreetMap contributors",
        }}).addTo(mmap);
      }}
      var mmap = twoMaps[key];
      mmap.eachLayer(function(layer) {{
        if (layer instanceof L.Marker || layer instanceof L.Polyline) mmap.removeLayer(layer);
      }});
      function addPoint(p, cls) {{
        var lat = Number(p.lat), lng = Number(p.lng);
        if (!isFinite(lat) || !isFinite(lng)) return null;
        var m = L.marker([lat, lng]).addTo(mmap);
        if (p.name) m.bindTooltip(String(p.name), {{ permanent: true, direction: "top", className: cls }});
        m.on("click", function() {{ window.open(gmaps(lat, lng), "_blank", "noopener,noreferrer"); }});
        return [lat, lng];
      }}
      var a = addPoint(geo.a, "two-tip");
      var b = addPoint(geo.b, "two-tip");
      var pts = [];
      if (a) pts.push(a);
      if (b) pts.push(b);
      if (pts.length === 2) L.polyline(pts, {{ weight: 3, opacity: 0.8 }}).addTo(mmap);
      if (pts.length === 1) mmap.setView(pts[0], 15);
      else if (pts.length > 1) mmap.fitBounds(pts, {{ padding: [24, 24], maxZoom: 16 }});
      setTimeout(function() {{ mmap.invalidateSize(); }}, 60);
    }});
  }});

  var points = {points_js};
  var mapEl = document.getElementById("share-map");
  if (mapEl && Array.isArray(points) && points.length) {{
    var map = L.map("share-map", {{ scrollWheelZoom: false }});
    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }}).addTo(map);
    var bounds = [];
    points.forEach(function(p) {{
      var lat = Number(p.lat), lng = Number(p.lng);
      if (!isFinite(lat) || !isFinite(lng)) return;
      bounds.push([lat, lng]);
      var m = L.marker([lat, lng]).addTo(map);
      var label = (p.name || "現場") + (p.management_no ? (" (" + p.management_no + ")") : "");
      m.bindTooltip(label, {{ permanent: false, direction: "top" }});
    }});
    if (bounds.length === 1) map.setView(bounds[0], 15);
    else if (bounds.length > 1) map.fitBounds(bounds, {{ padding: [28, 28], maxZoom: 16 }});
  }}
}})();
  </script>
</body>
</html>
"""


def write_archive_detail_pages(
    repo_root: Path, entries: list[ManifestEntry]
) -> list[Path]:
    """manifest entries に応じて portal/archive/<date>/index.html を上書き生成。entries が空なら何もしない。"""
    if not entries:
        return []
    arch_root = repo_root / "portal" / "archive"
    written: list[Path] = []
    for ent in entries:
        day_dir = arch_root / ent.date
        day_dir.mkdir(parents=True, exist_ok=True)
        out_path = day_dir / "index.html"
        pub_items, note = load_archive_public_items(repo_root, ent.date)
        out_path.write_text(
            build_archive_detail_html(ent, pub_items, note),
            encoding="utf-8",
            newline="\n",
        )
        written.append(out_path)
    return written


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
          <a class="portal-menu-item" role="menuitem" href="./survey/">現調待ち</a>
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

    manifest_entries = load_archive_manifest_entries(repo_root)
    manifest_dates = [e.date for e in manifest_entries]
    archived = set(manifest_dates)

    entries: list[tuple[str, str]] = []
    for folder, path in rows:
        if folder in archived:
            continue
        html_text = path.read_text(encoding="utf-8", errors="replace")
        date_line = card_heading(folder, path)
        summary = summarize_share_html(html_text, folder)
        heading = build_portal_heading(date_line, summary)
        entries.append((folder, heading))

    share_by_folder: dict[str, Path] = {f: p for f, p in rows}
    archive_parts: list[
        tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]
    ] = []
    for ment in manifest_entries:
        path = share_by_folder.get(ment.date)
        summary: ShareSummary | None = None
        if path is not None:
            html_text = path.read_text(encoding="utf-8", errors="replace")
            summary = summarize_share_html(html_text, ment.date)
        else:
            print(
                f"Warning: archive manifest lists '{ment.date}' but share/{ment.date}/ "
                "has no index.html; archive list/detail use manifest fields only",
                file=sys.stderr,
            )
        public_items, _ = load_archive_public_items(repo_root, ment.date)
        archive_parts.append((ment, summary, public_items))

    out = build_html(entries)
    out_path = repo_root / "portal" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8", newline="\n")
    print(
        f"Wrote {out_path} ({len(entries)} cards, "
        f"{len(archived)} date(s) hidden on top per manifest)"
    )

    today = date.today()
    recent_parts: list[
        tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]
    ] = []
    monthly_parts: list[
        tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]
    ] = []
    for ment, summary, public_items in archive_parts:
        if is_in_last_seven_days(ment.date, today):
            recent_parts.append((ment, summary, public_items))
        else:
            monthly_parts.append((ment, summary, public_items))
    recent_parts.sort(key=lambda t: sort_key(t[0].date), reverse=True)
    sections = group_archive_sections(monthly_parts)
    arch_html = build_archive_html(recent_parts, sections)
    arch_path = repo_root / "portal" / "archive" / "index.html"
    arch_path.parent.mkdir(parents=True, exist_ok=True)
    arch_path.write_text(arch_html, encoding="utf-8", newline="\n")
    detail_paths = write_archive_detail_pages(repo_root, manifest_entries)
    for dp in detail_paths:
        print(f"Wrote {dp}")
    print(
        f"Wrote {arch_path} (manifest={len(manifest_entries)}, "
        f"archive_rows={len(archive_parts)}, recent={len(recent_parts)}, months={len(sections)}, "
        f"archive_details={len(detail_paths)})"
    )
    survey_items, survey_empty_note = load_survey_public_items(repo_root)
    survey_html = build_survey_html(
        survey_items,
        survey_empty_note,
        date.today().isoformat(),
    )
    survey_path = repo_root / "portal" / "survey" / "index.html"
    survey_path.parent.mkdir(parents=True, exist_ok=True)
    survey_path.write_text(survey_html, encoding="utf-8", newline="\n")
    print(f"Wrote {survey_path} (survey_items={len(survey_items)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
