#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan share/<date>/index.html and regenerate portal/index.html and portal/archive/index.html (stdlib only).

ポータルTOPのカードは share 配下の従来どおり。アーカイブは portal/archive_manifest.json の entries
に登録された6桁日付のみ。アーカイブ一覧・各日付の詳細ページは manifest を正本とし、share が無い日付も
一覧・詳細に出せる（共有ページ削除後もアーカイブ詳細でサマリを残すため）。

manifest の entries[].href は **portal/archive/index.html を基準としたアーカイブ詳細への相対 URL**
（例: ``./260520/``）を推奨する。``../../share/<date>/`` は共有ページ削除後に 404 になるため、登録済み
アーカイブ日付では使わないこと。

portal/archive/<YYMMDD>/ は generate 時に manifest 済み分へ上書き生成する。manifest から date が消えた
古い YYMMDD ディレクトリは自動では削除しない（孤立が残る）。必要なら生成前に 6 桁名フォルダだけ手で整理する。

CLI では ``--data-root <path>`` に ippatsu の ``data`` ディレクトリ（``completion_reports/`` と ``survey/`` を含む）を
渡せる。未指定時は従来どおり ``<share-pages の親>/ippatsu-pc/data`` を参照する。

``--mode full``（既定）: 従来どおり全体再生成（survey・share 注入・manifest 全日付のアーカイブ詳細を含む）。

``--mode completion-archive --date YYMMDD``: 完了報告アーカイブ反映向けの最小生成。
``portal/index.html``・``portal/archive/index.html``・``portal/archive/<date>/index.html`` のみ。
survey・share 注入・他日付のアーカイブ詳細は触らない。
``portal/index.html`` のアクティブ一覧は **share-pages の ``share/<date>/index.html``** を走査し、
``portal/archive_manifest.json`` に載る日付（対象日を含む）を TOP から除外する。
``data/share/*.json`` は参照しない（manifest は ippatsu-pc 側で事前更新される想定）。

``--mode share-update --date YYMMDD``: 共有モードの公開・差し替え向けの最小生成。
``portal/index.html`` と **当該日のみ** ``share/<date>/index.html`` の inject のみ。
survey・アーカイブ一覧・全 archive 詳細・他日付 share inject は触らない。
"""

from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import os
import re
import sys
import unicodedata
from urllib.parse import parse_qs, quote, urlencode, urlparse
from dataclasses import dataclass
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

from portal_immediate_status_client import (
    PORTAL_CASE_STATUS_ENDPOINT_DEFAULT,
    fetch_portal_negotiation_wait_keys,
    portal_immediate_status_enabled,
    render_negotiation_immediate_status_js,
    render_survey_immediate_status_js,
    render_survey_legacy_request_js,
    serialize_promoted_candidates,
)
from typing import Any

# ippatsu-pc の data ディレクトリ（--data-root で上書き）。未指定時は sibling ippatsu-pc/data。
_DATA_ROOT_OVERRIDE: Path | None = None

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

# 共有ページの枝切り・根切り表で集計対象とする区分ラベル（合計行・未確定行は除外）
_SHARE_INSTR_CUT_BAND_LABELS = frozenset(
    ("〜10未満", "〜20未満", "〜30未満", "〜40未満", "〜50未満", "50以上")
)
# prefill 用: 区分表示ラベル → JSON キー（枝・根）
_SHARE_INSTR_CUT_BAND_PREFILL_ROWS: tuple[tuple[str, str, str], ...] = (
    ("〜10未満", "branch_cut_under_10", "root_cut_under_10"),
    ("〜20未満", "branch_cut_10_20", "root_cut_10_20"),
    ("〜30未満", "branch_cut_20_30", "root_cut_20_30"),
    ("〜40未満", "branch_cut_30_40", "root_cut_30_40"),
    ("〜50未満", "branch_cut_40_50", "root_cut_40_50"),
    ("50以上", "branch_cut_over_50", "root_cut_over_50"),
)

# ---------------------------------------------------------------------------
# 現調結果報告（Googleフォーム prefill）
# 報告者 entry.1882173754 / メモ entry.1568902885 はフォーム側入力のため URL に含めない。
# ---------------------------------------------------------------------------
SURVEY_REPORT_FORM_URL = (
    "https://docs.google.com/forms/d/e/1FAIpQLSdhZ7Za1KRpTGVM9odxKbNKfG7rosHWAaTEBHVSIHZsfQiKZQ/viewform"
)
SURVEY_REPORT_ENTRY_MANAGEMENT_NO = "entry.1264151869"
SURVEY_REPORT_ENTRY_LABEL = "entry.1454610165"
SURVEY_REPORT_ENTRY_TYPE = "entry.1400430047"
SURVEY_REPORT_ENTRY_DATE = "entry.983859884"
# フォームの選択肢に合わせた報告種別（日本語）
SURVEY_REPORT_TYPE_JP_COMPLETED = "現調済み"
SURVEY_REPORT_TYPE_JP_RETURN_CANDIDATE = "返却候補"

# 現調済み更新依頼（Supabase Edge Function）。service_role は公開 HTML に出さない。
SURVEY_STATUS_REQUEST_ENDPOINT = (
    "https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/submit-survey-status-request"
)
# B-plan routes through deployed submit-survey-status-request (GET/POST overlay).
PORTAL_CASE_STATUS_ENDPOINT = SURVEY_STATUS_REQUEST_ENDPOINT


def _jwt_role_from_api_key(key: str) -> str | None:
    """JWT 形式の Supabase API key から role を読む（service_role 誤埋め込み防止）。"""
    parts = key.split(".")
    if len(parts) != 3:
        return None
    try:
        pad = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(pad))
        role = payload.get("role")
        return str(role) if role is not None else None
    except (json.JSONDecodeError, ValueError, OSError):
        return None


def survey_status_request_api_key() -> str:
    """ポータル HTML 用 apikey（publishable/anon のみ）。service_role は使わない。"""
    for name in ("PORTAL_SURVEY_REQUEST_API_KEY", "SUPABASE_ANON_KEY"):
        raw = (os.environ.get(name) or "").strip()
        if not raw:
            continue
        if _jwt_role_from_api_key(raw) == "service_role":
            print(
                f"warning: {name} looks like service_role; "
                "skipped for portal HTML (use anon/publishable only).",
                file=sys.stderr,
            )
            continue
        return raw
    return ""

# ---------------------------------------------------------------------------
# 現場共有 — 詳細修正（Googleフォーム prefill / V2・6区分枝根）
# 現調待ち（SURVEY_REPORT_*）とは独立。docs/share_detail_edit_form_apps_script.md 参照。
# ---------------------------------------------------------------------------
SHARE_DETAIL_EDIT_FORM_URL = (
    "https://docs.google.com/forms/d/e/1FAIpQLSftmxlaA3vwt1s-AT7MOia5hHy3dtL5vbcsvgZHUinq9ETRQg/viewform"
)
SHARE_DETAIL_EDIT_ENTRY_DATE = "entry.1582884252"
SHARE_DETAIL_EDIT_ENTRY_MANAGEMENT_NO = "entry.2102936974"
SHARE_DETAIL_EDIT_ENTRY_LABEL = "entry.932009684"
SHARE_DETAIL_EDIT_ENTRY_WORK_METHOD = "entry.579262382"
SHARE_DETAIL_EDIT_ENTRY_BUCKET_TRUCK = "entry.2099732396"
SHARE_DETAIL_EDIT_ENTRY_ROAD_WIDTH = "entry.1713335536"
SHARE_DETAIL_EDIT_ENTRY_SLOPE = "entry.539982619"
SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_UNDER_10 = "entry.948358914"
SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_10_20 = "entry.740813394"
SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_20_30 = "entry.74377314"
SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_30_40 = "entry.957344080"
SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_40_50 = "entry.382023163"
SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_OVER_50 = "entry.288483164"
SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_UNDER_10 = "entry.1467113295"
SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_10_20 = "entry.108281366"
SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_20_30 = "entry.77416071"
SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_30_40 = "entry.792549802"
SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_40_50 = "entry.1363589096"
SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_OVER_50 = "entry.388844699"
SHARE_DETAIL_EDIT_ENTRY_BUSH_AREA = "entry.133683289"
SHARE_DETAIL_EDIT_ENTRY_BAMBOO_COUNT = "entry.1908811234"
SHARE_DETAIL_EDIT_ENTRY_VINE_COUNT = "entry.1406858047"
SHARE_DETAIL_EDIT_ENTRY_NOTE = "entry.1367667439"

# 未確定修正の表示上書き（Apps Script Web アプリ JSON）。空のときは fetch しない。
SHARE_DETAIL_EDIT_API_URL = (
    "https://script.google.com/macros/s/AKfycbzLtv-yZP5QNjXQSEybhxBTmWrNaujJJfyb_okMcuSzjKyREFthJTwI_Y5fc0PKfGuOnA/exec"
)
SHARE_DETAIL_EDIT_API_TOKEN = "ippatsu_share_detail_edit_202605_long_token"

_SHARE_LIVE_EDIT_BEGIN = "<!-- share-live-edit-inject:begin -->"
_SHARE_LIVE_EDIT_END = "<!-- share-live-edit-inject:end -->"

_SHARE_DETAIL_EDIT_BTN_TITLE = (
    "共有ページの表示内容の修正をフォームへ送ります（送信後も即時反映されません）"
)
_SHARE_DETAIL_EDIT_CARD_CSS = """
.detail-edit-footer {
  margin-top: 0.75rem;
  padding-top: 0.55rem;
  border-top: 1px dashed var(--border);
}
.detail-edit-footer--fallback {
  margin: 0.5rem 0 0;
  padding-top: 0.45rem;
  border-top: 1px dashed var(--border);
}
.btn-detail-edit--panel {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  padding: 0.42rem 0.65rem;
  min-height: 44px;
  font-size: 0.82rem;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  text-decoration: none;
  touch-action: manipulation;
  background: #f8fafc;
  color: #334155;
  border: 1px solid #94a3b8;
  line-height: 1.25;
  max-width: min(100%, 280px);
}
.btn-detail-edit--panel:hover,
.btn-detail-edit--panel:focus-visible {
  background: #f1f5f9;
  outline: none;
}
.note-panel .btn-detail-edit--panel {
  width: 100%;
  max-width: 100%;
}
.detail-edit-footer--fallback .btn-detail-edit--panel {
  font-size: 0.8rem;
  min-height: 44px;
}
"""


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


def normalize_management_no(raw: str) -> str | None:
    """ippatsu-pc ``app/share/supabase_case_import.normalize_management_no`` と同じ規則。"""
    if raw is None:
        return None
    s = unicodedata.normalize("NFKC", str(raw)).strip()
    s = s.replace("\u3000", " ")
    digits = re.sub(r"\D+", "", s)
    if not digits:
        return None
    n = len(digits)
    if n <= 5:
        prefix = "514"
        body = digits.zfill(5)
    elif n == 6:
        head = digits[0]
        if head == "5":
            prefix = "515"
        elif head == "4":
            prefix = "514"
        else:
            return None
        body = digits[1:]
    elif n == 8:
        prefix = digits[:3]
        body = digits[3:]
        if prefix not in {"514", "515"}:
            return None
    else:
        return None
    if len(body) != 5:
        return None
    return f"{prefix} {body}"


def management_no_key(raw: str) -> str | None:
    """ippatsu-pc ``app/share/supabase_case_import.management_no_key`` と同じ規則。"""
    s = str(raw or "").strip()
    if not s or s == "—":
        return None
    norm = normalize_management_no(s)
    if norm is not None:
        return re.sub(r"\s+", "", norm)
    digits = re.sub(r"\D+", "", unicodedata.normalize("NFKC", s))
    return digits or None


def build_survey_report_url(
    base_url: str,
    management_no: str,
    label: str,
    report_type_jp: str,
    report_date_iso: str,
) -> str:
    """Googleフォーム prefill 用クエリ（entry ID）。報告者・メモは URL に含めない。"""
    b = (base_url or "").strip() or SURVEY_REPORT_FORM_URL
    params: dict[str, str] = {
        SURVEY_REPORT_ENTRY_MANAGEMENT_NO: management_no,
        SURVEY_REPORT_ENTRY_LABEL: label,
        SURVEY_REPORT_ENTRY_TYPE: report_type_jp,
    }
    if report_date_iso:
        params[SURVEY_REPORT_ENTRY_DATE] = report_date_iso
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
    instructions_html: str = ""
    detail_prefill: ShareDetailEditPrefill | None = None


@dataclass(frozen=True)
class ShareDetailEditPrefill:
    """詳細修正フォーム prefill 用（アーカイブ item または共有 HTML カードから組み立て）。V2: 枝根は6区分。"""

    management_no: str
    label: str
    method: str
    bucket_truck: str
    road_width: str
    slope: str
    branch_cut_under_10: str
    branch_cut_10_20: str
    branch_cut_20_30: str
    branch_cut_30_40: str
    branch_cut_40_50: str
    branch_cut_over_50: str
    root_cut_under_10: str
    root_cut_10_20: str
    root_cut_20_30: str
    root_cut_30_40: str
    root_cut_40_50: str
    root_cut_over_50: str
    bush_area: str
    bamboo_count: str
    vine_count: str
    note: str


def _share_detail_edit_entry_id_list() -> tuple[str, ...]:
    return (
        SHARE_DETAIL_EDIT_ENTRY_DATE,
        SHARE_DETAIL_EDIT_ENTRY_MANAGEMENT_NO,
        SHARE_DETAIL_EDIT_ENTRY_LABEL,
        SHARE_DETAIL_EDIT_ENTRY_WORK_METHOD,
        SHARE_DETAIL_EDIT_ENTRY_BUCKET_TRUCK,
        SHARE_DETAIL_EDIT_ENTRY_ROAD_WIDTH,
        SHARE_DETAIL_EDIT_ENTRY_SLOPE,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_UNDER_10,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_10_20,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_20_30,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_30_40,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_40_50,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_OVER_50,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_UNDER_10,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_10_20,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_20_30,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_30_40,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_40_50,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_OVER_50,
        SHARE_DETAIL_EDIT_ENTRY_BUSH_AREA,
        SHARE_DETAIL_EDIT_ENTRY_BAMBOO_COUNT,
        SHARE_DETAIL_EDIT_ENTRY_VINE_COUNT,
        SHARE_DETAIL_EDIT_ENTRY_NOTE,
    )


def share_detail_edit_form_enabled() -> bool:
    """フォーム URL と全 entry ID が揃っているときのみ True（未設定時はボタン非表示）。"""
    base = (SHARE_DETAIL_EDIT_FORM_URL or "").strip()
    if not base:
        return False
    return all((eid or "").strip() for eid in _share_detail_edit_entry_id_list())


def build_share_detail_edit_prefill_url(prefill: ShareDetailEditPrefill, date_key: str) -> str | None:
    """詳細修正 prefill URL。報告者は付与しない。"""
    if not share_detail_edit_form_enabled():
        return None
    dk = (date_key or "").strip()
    params: dict[str, str] = {
        SHARE_DETAIL_EDIT_ENTRY_DATE: dk,
        SHARE_DETAIL_EDIT_ENTRY_MANAGEMENT_NO: prefill.management_no,
        SHARE_DETAIL_EDIT_ENTRY_LABEL: prefill.label,
        SHARE_DETAIL_EDIT_ENTRY_WORK_METHOD: prefill.method,
        SHARE_DETAIL_EDIT_ENTRY_BUCKET_TRUCK: prefill.bucket_truck,
        SHARE_DETAIL_EDIT_ENTRY_ROAD_WIDTH: prefill.road_width,
        SHARE_DETAIL_EDIT_ENTRY_SLOPE: prefill.slope,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_UNDER_10: prefill.branch_cut_under_10,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_10_20: prefill.branch_cut_10_20,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_20_30: prefill.branch_cut_20_30,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_30_40: prefill.branch_cut_30_40,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_40_50: prefill.branch_cut_40_50,
        SHARE_DETAIL_EDIT_ENTRY_BRANCH_CUT_OVER_50: prefill.branch_cut_over_50,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_UNDER_10: prefill.root_cut_under_10,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_10_20: prefill.root_cut_10_20,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_20_30: prefill.root_cut_20_30,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_30_40: prefill.root_cut_30_40,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_40_50: prefill.root_cut_40_50,
        SHARE_DETAIL_EDIT_ENTRY_ROOT_CUT_OVER_50: prefill.root_cut_over_50,
        SHARE_DETAIL_EDIT_ENTRY_BUSH_AREA: prefill.bush_area,
        SHARE_DETAIL_EDIT_ENTRY_BAMBOO_COUNT: prefill.bamboo_count,
        SHARE_DETAIL_EDIT_ENTRY_VINE_COUNT: prefill.vine_count,
        SHARE_DETAIL_EDIT_ENTRY_NOTE: prefill.note,
    }
    b = (SHARE_DETAIL_EDIT_FORM_URL or "").strip()
    q = urlencode(params, quote_via=quote, safe="")
    joiner = "&" if "?" in b else "?"
    return f"{b.rstrip('?')}{joiner}{q}"


def _empty_cut_prefill_strings() -> dict[str, str]:
    return {
        "branch_cut_under_10": "",
        "branch_cut_10_20": "",
        "branch_cut_20_30": "",
        "branch_cut_30_40": "",
        "branch_cut_40_50": "",
        "branch_cut_over_50": "",
        "root_cut_under_10": "",
        "root_cut_10_20": "",
        "root_cut_20_30": "",
        "root_cut_30_40": "",
        "root_cut_40_50": "",
        "root_cut_over_50": "",
    }


def _share_detail_prefill_from_archive_item(item: ArchivePublicItem) -> ShareDetailEditPrefill:
    """completion_reports の source_item 由来 prefill（無い場合は集計フィールドのみ）。"""
    if item.detail_prefill is not None:
        return item.detail_prefill
    nt = (item.note or "").strip()
    if nt == "—":
        nt = ""
    z = _empty_cut_prefill_strings()
    return ShareDetailEditPrefill(
        management_no=(item.management_no or "").strip(),
        label=(item.label or "").strip(),
        method=(item.method or "").strip(),
        bucket_truck=(item.bucket_available or "").strip(),
        road_width=(item.road_width_m or "").strip(),
        slope="",
        branch_cut_under_10=z["branch_cut_under_10"],
        branch_cut_10_20=z["branch_cut_10_20"],
        branch_cut_20_30=z["branch_cut_20_30"],
        branch_cut_30_40=z["branch_cut_30_40"],
        branch_cut_40_50=z["branch_cut_40_50"],
        branch_cut_over_50=z["branch_cut_over_50"],
        root_cut_under_10=z["root_cut_under_10"],
        root_cut_10_20=z["root_cut_10_20"],
        root_cut_20_30=z["root_cut_20_30"],
        root_cut_30_40=z["root_cut_30_40"],
        root_cut_40_50=z["root_cut_40_50"],
        root_cut_over_50=z["root_cut_over_50"],
        bush_area=(item.brush_area_m2 or "").strip(),
        bamboo_count=(item.bamboo_count or "").strip(),
        vine_count=(item.vine_locations or "").strip(),
        note=nt,
    )


def build_share_detail_edit_url(item: ArchivePublicItem, date_key: str) -> str | None:
    """アーカイブ詳細カード用の詳細修正 prefill URL。"""
    return build_share_detail_edit_prefill_url(_share_detail_prefill_from_archive_item(item), date_key)


def _parse_share_summary_rows(article_html: str) -> dict[str, str]:
    cap = article_html.find("instr-cut-caption")
    head = article_html[:cap] if cap >= 0 else article_html
    out: dict[str, str] = {}
    for m in re.finditer(r"<tr><th>([^<]+)</th><td>([^<]*)</td></tr>", head):
        k = html_lib.unescape(m.group(1).strip())
        out[k] = html_lib.unescape(m.group(2).strip())
    return out


def _parse_share_cut_table_totals(article_html: str) -> tuple[int, int]:
    m = re.search(r'class="instr-table instr-cut"[^>]*>([\s\S]*?)</table>', article_html)
    if not m:
        return 0, 0
    inner = m.group(1)
    br = rt = 0
    for row in re.finditer(r"<th[^>]*>([^<]+)</th><td>(\d+)</td><td>(\d+)</td>", inner):
        label = html_lib.unescape(row.group(1)).strip()
        if label not in _SHARE_INSTR_CUT_BAND_LABELS:
            continue
        br += int(row.group(2))
        rt += int(row.group(3))
    return br, rt


def _parse_share_instr_cut_band_prefill(article_html: str) -> dict[str, str]:
    """`.instr-cut` の6区分行から枝・根の表示値を取り出す（合計・未確定行は無視）。"""
    out = _empty_cut_prefill_strings()
    m = re.search(r'class="instr-table instr-cut"[^>]*>([\s\S]*?)</table>', article_html)
    if not m:
        return out
    inner = m.group(1)
    label_to_keys = {lab: (bk, rk) for lab, bk, rk in _SHARE_INSTR_CUT_BAND_PREFILL_ROWS}
    for row in re.finditer(r"<th[^>]*>([^<]+)</th><td>([^<]*)</td><td>([^<]*)</td>", inner):
        label = html_lib.unescape(row.group(1)).strip()
        if label not in label_to_keys:
            continue
        bk, rk = label_to_keys[label]
        btxt = html_lib.unescape(row.group(2).strip())
        rtxt = html_lib.unescape(row.group(3).strip())
        out[bk] = btxt
        out[rk] = rtxt
    return out


def _parse_share_other_rows(article_html: str) -> dict[str, str]:
    m = re.search(r'class="instr-table instr-other"[^>]*>([\s\S]*?)</table>', article_html)
    if not m:
        return {}
    out: dict[str, str] = {}
    for row in re.finditer(r"<tr><th>([^<]+)</th><td>([^<]*)</td></tr>", m.group(1)):
        k = html_lib.unescape(row.group(1).strip())
        out[k] = html_lib.unescape(row.group(2).strip())
    return out


def parse_share_card_article_for_detail_edit(article_html: str) -> ShareDetailEditPrefill | None:
    """共有 index.html の1カード断片から prefill を抽出（HTMLは正本のまま読むのみ）。"""
    mt = re.search(r'<h2 class="card-title">([^<]*)</h2>', article_html)
    mm = re.search(r'<p class="item-mgmt">([^<]*)</p>', article_html)
    if not mt or not mm:
        return None
    label = html_lib.unescape(mt.group(1).strip())
    management_no = html_lib.unescape(mm.group(1).strip())
    summary = _parse_share_summary_rows(article_html)
    method = summary.get("処理方法", "")
    bucket_truck = summary.get("B車", "")
    road_width = summary.get("道幅", "")
    slope = summary.get("傾斜", "")
    if slope in {"—", "―", ""}:
        slope = ""
    other = _parse_share_other_rows(article_html)
    bush_area = other.get("柴伐採面積", "")
    bamboo_count = other.get("竹伐採本数", "")
    vine_count = other.get("つる伐採箇所数", "")
    cuts = _parse_share_instr_cut_band_prefill(article_html)
    note = ""
    nm = re.search(r'<div class="instr-note"[^>]*>([\s\S]*?)</div>', article_html)
    if nm:
        raw = nm.group(1)
        raw = re.sub(r"<[^>]+>", " ", raw)
        note = html_lib.unescape(" ".join(raw.split())).strip()
    return ShareDetailEditPrefill(
        management_no=management_no,
        label=label,
        method=method,
        bucket_truck=bucket_truck,
        road_width=road_width,
        slope=slope,
        branch_cut_under_10=cuts["branch_cut_under_10"],
        branch_cut_10_20=cuts["branch_cut_10_20"],
        branch_cut_20_30=cuts["branch_cut_20_30"],
        branch_cut_30_40=cuts["branch_cut_30_40"],
        branch_cut_40_50=cuts["branch_cut_40_50"],
        branch_cut_over_50=cuts["branch_cut_over_50"],
        root_cut_under_10=cuts["root_cut_under_10"],
        root_cut_10_20=cuts["root_cut_10_20"],
        root_cut_20_30=cuts["root_cut_20_30"],
        root_cut_30_40=cuts["root_cut_30_40"],
        root_cut_40_50=cuts["root_cut_40_50"],
        root_cut_over_50=cuts["root_cut_over_50"],
        bush_area=bush_area,
        bamboo_count=bamboo_count,
        vine_count=vine_count,
        note=note,
    )


def _share_detail_edit_footer_inner_html(url: str) -> str:
    """現場指示パネル末尾のリンクのみ（パネル内・フォールバック共通）。"""
    t = escape_html(_SHARE_DETAIL_EDIT_BTN_TITLE)
    return (
        f'<a class="btn btn-detail-edit btn-detail-edit--panel" href="{escape_html(url)}" '
        f'target="_blank" rel="noopener noreferrer" title="{t}">詳細を修正</a>'
    )


def _share_detail_edit_footer_html(url: str, *, fallback: bool = False) -> str:
    cls = "detail-edit-footer detail-edit-footer--fallback" if fallback else "detail-edit-footer"
    return f'<div class="{cls}">' + _share_detail_edit_footer_inner_html(url) + "</div>"


def _share_detail_edit_link_html(url: str) -> str:
    """アーカイブ詳細など、共有メイン以外でカードアクション行に単体リンクを置く場合用。"""
    t = escape_html(_SHARE_DETAIL_EDIT_BTN_TITLE)
    return (
        f'<a class="btn btn-detail-edit btn-detail-edit--panel" href="{escape_html(url)}" '
        f'target="_blank" rel="noopener noreferrer" title="{t}">詳細を修正</a>'
    )


def _inject_detail_edit_footer_into_note_panel(chunk: str, footer_html: str) -> str | None:
    """1カード断片の note-panel 直前の閉じ </div> の前に footer を挿入。失敗時は None。"""
    if 'class="note-panel"' not in chunk:
        return None
    idx = chunk.rfind("</article>")
    if idx < 0:
        return None
    prefix = chunk[:idx]
    last_div = prefix.rfind("</div>")
    if last_div < 0:
        return None
    return prefix[:last_div] + footer_html + prefix[last_div:] + chunk[idx:]


def _inject_detail_edit_footer_fallback_before_two_geo(chunk: str, url: str) -> str:
    """note-panel が無いカード用: two-geo script の直前に控えめに挿入。"""
    wrapped = _share_detail_edit_footer_html(url, fallback=True)
    new_c, n_sub = re.subn(
        r"(</div>\s*</div>\s*)(<script type=\"application/json\" id=\"two-geo-)",
        r"\1" + wrapped + r"\n  \2",
        chunk,
        count=1,
    )
    return new_c if n_sub else chunk


def apply_share_detail_edit_to_share_html(html: str, date_key: str) -> str:
    """share/<date>/index.html に詳細修正リンクを注入（正本 JSON は触らない）。"""
    if not share_detail_edit_form_enabled():
        return html
    out = html
    # 旧生成 HTML の style に残った説明用ルール・フォールバックの min-height を整理
    out = re.sub(r"\.detail-edit-hint\s*\{[^}]*\}\s*", "", out)
    out = re.sub(
        r"(\.detail-edit-footer--fallback\s*\.btn-detail-edit--panel\s*\{[^}]*min-height:\s*)40px",
        r"\g<1>44px",
        out,
    )
    out = re.sub(
        r"\s*<a class=\"btn btn-detail-edit[^\"]*\"[^>]*>[\s\S]*?詳細(?:修正を報告|を修正)\s*</a>",
        "",
        out,
    )
    out = re.sub(
        r'<div class="detail-edit-footer[^>]*>[\s\S]*?</div>\s*',
        "",
        out,
    )
    if ".detail-edit-footer {" not in out:
        out = out.replace("</style>", _SHARE_DETAIL_EDIT_CARD_CSS + "\n</style>", 1)
    parts = re.split(r"(?=<article class=\"card\")", out)
    rebuilt: list[str] = [parts[0]]
    for chunk in parts[1:]:
        if not chunk.startswith("<article"):
            rebuilt.append(chunk)
            continue
        pre = parse_share_card_article_for_detail_edit(chunk)
        if pre is None:
            rebuilt.append(chunk)
            continue
        url = build_share_detail_edit_prefill_url(pre, date_key)
        if not url:
            rebuilt.append(chunk)
            continue
        footer = _share_detail_edit_footer_html(url, fallback=False)
        placed = _inject_detail_edit_footer_into_note_panel(chunk, footer)
        if placed is not None:
            rebuilt.append(placed)
        else:
            rebuilt.append(_inject_detail_edit_footer_fallback_before_two_geo(chunk, url))
    return "".join(rebuilt)


def _strip_share_live_edit_identity_attrs(html: str) -> str:
    return re.sub(
        r'\s+data-date="[^"]*"\s+data-management-no-key="[^"]*"\s+data-management-no="[^"]*"',
        "",
        html,
    )


def _strip_share_live_edit_inject_block(html: str) -> str:
    if _SHARE_LIVE_EDIT_BEGIN not in html:
        return html
    return re.sub(
        re.escape(_SHARE_LIVE_EDIT_BEGIN) + r"[\s\S]*?" + re.escape(_SHARE_LIVE_EDIT_END),
        "",
        html,
        count=1,
    )


def _inject_body_data_share_page_date(html: str, date_key: str) -> str:
    dk = escape_html((date_key or "").strip())

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1) or ""
        inner = re.sub(r'\s+data-share-page-date="[^"]*"', "", inner, flags=re.I)
        return f'<body data-share-page-date="{dk}"{inner}>'

    return re.sub(r"<body([^>]*)>", repl, html, count=1, flags=re.I)


def _inject_article_card_identity_attrs(html: str, date_key: str) -> str:
    parts = re.split(r"(?=<article class=\"card\")", html)
    rebuilt: list[str] = [parts[0]]
    dk = escape_html((date_key or "").strip())
    for chunk in parts[1:]:
        if not chunk.startswith("<article"):
            rebuilt.append(chunk)
            continue
        mm = re.search(r'<p class="item-mgmt">([^<]*)</p>', chunk)
        if not mm:
            rebuilt.append(chunk)
            continue
        mgmt = html_lib.unescape(mm.group(1)).strip()
        key = re.sub(r"\s+", "", mgmt)
        esc_mgmt = escape_html(mgmt)
        esc_key = escape_html(key)

        def open_repl(m: re.Match[str]) -> str:
            tag_start, rest, closing = m.group(1), m.group(2) or "", m.group(3)
            if "data-management-no-key=" in tag_start + rest:
                return m.group(0)
            return f'{tag_start}{rest} data-date="{dk}" data-management-no-key="{esc_key}" data-management-no="{esc_mgmt}"{closing}'

        new_c, n_sub = re.subn(
            r"^(<article\s+class=\"card\")([^>]*)(>)",
            open_repl,
            chunk,
            count=1,
            flags=re.M,
        )
        rebuilt.append(new_c if n_sub else chunk)
    return "".join(rebuilt)


_SHARE_LIVE_EDIT_CARD_CSS = """
.share-pending-overlay-banner {
  margin: 0 0 0.55rem;
  padding: 0.45rem 0.55rem;
  font-size: 0.8rem;
  line-height: 1.45;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 8px;
}
.share-pending-overlay-banner[hidden] { display: none !important; }
.share-pending-overlay-title {
  display: block;
  font-weight: 700;
}
.share-pending-overlay-sub {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.76rem;
  color: #a16207;
  font-weight: 500;
}
.instr-cut-pending-total th,
.instr-cut-pending-total td {
  background: #fffbeb;
  font-weight: 600;
}
"""


_SHARE_LIVE_EDIT_RUNNER_JS = r"""
(function () {
  function esc(t) {
    var d = document.createElement("div");
    d.textContent = t == null ? "" : String(t);
    return d.innerHTML;
  }
  function normKey(s) {
    return String(s || "").replace(/\s+/g, "");
  }
  function cfg() {
    var el = document.getElementById("share-detail-edit-api-config");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent || "{}");
    } catch (e) {
      return null;
    }
  }
  function setSummaryCell(panel, label, value) {
    var rows = panel.querySelectorAll(".instr-summary tbody tr");
    for (var i = 0; i < rows.length; i++) {
      var th = rows[i].querySelector("th");
      var td = rows[i].querySelector("td");
      if (!th || !td) continue;
      if (String(th.textContent || "").trim() === label) {
        td.textContent = value == null ? "" : String(value);
        return;
      }
    }
  }
  function setOtherCell(panel, label, value) {
    var rows = panel.querySelectorAll(".instr-other tbody tr");
    for (var i = 0; i < rows.length; i++) {
      var th = rows[i].querySelector("th");
      var td = rows[i].querySelector("td");
      if (!th || !td) continue;
      if (String(th.textContent || "").trim() === label) {
        td.textContent = value == null ? "" : String(value);
        return;
      }
    }
  }
  function applyCutTotals(panel, branch, root) {
    var tb = panel.querySelector(".instr-cut tbody");
    if (!tb) return;
    var prev = tb.querySelectorAll("tr.instr-cut-pending-total");
    for (var i = 0; i < prev.length; i++) {
      prev[i].parentNode.removeChild(prev[i]);
    }
    var bStr = branch != null && String(branch).length ? String(branch) : "";
    var rStr = root != null && String(root).length ? String(root) : "";
    if (!bStr && !rStr) return;
    var bCell = bStr ? esc(bStr) : "\u2014";
    var rCell = rStr ? esc(rStr) : "\u2014";
    var tr = document.createElement("tr");
    tr.className = "instr-cut-pending-total";
    tr.innerHTML =
      '<th scope="row">\u5408\u8a08\uff08\u672a\u78ba\u5b9a\u4fee\u6b63\uff09</th><td>' +
      bCell +
      "</td><td>" +
      rCell +
      "</td>";
    tb.appendChild(tr);
  }
  function ensureBanner(article) {
    var b = article.querySelector(".share-pending-overlay-banner");
    if (!b) {
      b = document.createElement("div");
      b.className = "share-pending-overlay-banner";
      b.setAttribute("role", "status");
      b.innerHTML =
        '<span class="share-pending-overlay-title">\u73fe\u5834\u4fee\u6b63\u3042\u308a\uff08\u672a\u78ba\u5b9a\uff09</span>' +
        '<span class="share-pending-overlay-sub">\u4f1a\u793e\u78ba\u8a8d\u524d\u306e\u4fee\u6b63\u5185\u5bb9\u3092\u8868\u793a\u4e2d</span>';
      var head = article.querySelector(".card-head");
      if (head && head.parentNode === article) {
        article.insertBefore(b, head);
      } else {
        article.insertBefore(b, article.firstChild);
      }
    }
    b.hidden = false;
  }
  var V2_BRANCH_KEYS = [
    "branch_cut_under_10",
    "branch_cut_10_20",
    "branch_cut_20_30",
    "branch_cut_30_40",
    "branch_cut_40_50",
    "branch_cut_over_50",
  ];
  var V2_ROOT_KEYS = [
    "root_cut_under_10",
    "root_cut_10_20",
    "root_cut_20_30",
    "root_cut_30_40",
    "root_cut_40_50",
    "root_cut_over_50",
  ];
  function hasV2CutFields(f) {
    if (!f || typeof f !== "object") return false;
    var i;
    for (i = 0; i < V2_BRANCH_KEYS.length; i++) {
      if (V2_BRANCH_KEYS[i] in f) return true;
    }
    for (i = 0; i < V2_ROOT_KEYS.length; i++) {
      if (V2_ROOT_KEYS[i] in f) return true;
    }
    return false;
  }
  function parseInt0(s) {
    var t = String(s == null ? "" : s)
      .trim()
      .replace(/[^\d-]/g, "");
    if (!t) return 0;
    var n = parseInt(t, 10);
    return isNaN(n) ? 0 : n;
  }
  var CUT_LABELS = [
    "\u301c10\u672a\u6e80",
    "\u301c20\u672a\u6e80",
    "\u301c30\u672a\u6e80",
    "\u301c40\u672a\u6e80",
    "\u301c50\u672a\u6e80",
    "50\u4ee5\u4e0a",
  ];
  var CUT_B_BY_LABEL = {
    "\u301c10\u672a\u6e80": "branch_cut_under_10",
    "\u301c20\u672a\u6e80": "branch_cut_10_20",
    "\u301c30\u672a\u6e80": "branch_cut_20_30",
    "\u301c40\u672a\u6e80": "branch_cut_30_40",
    "\u301c50\u672a\u6e80": "branch_cut_40_50",
    "50\u4ee5\u4e0a": "branch_cut_over_50",
  };
  var CUT_R_BY_LABEL = {
    "\u301c10\u672a\u6e80": "root_cut_under_10",
    "\u301c20\u672a\u6e80": "root_cut_10_20",
    "\u301c30\u672a\u6e80": "root_cut_20_30",
    "\u301c40\u672a\u6e80": "root_cut_30_40",
    "\u301c50\u672a\u6e80": "root_cut_40_50",
    "50\u4ee5\u4e0a": "root_cut_over_50",
  };
  function applyCutBandsFromFields(panel, f) {
    var tb = panel.querySelector(".instr-cut tbody");
    if (!tb) return;
    var prev = tb.querySelectorAll("tr.instr-cut-pending-total");
    for (var i = 0; i < prev.length; i++) {
      prev[i].parentNode.removeChild(prev[i]);
    }
    var trs = tb.getElementsByTagName("tr");
    var j, tr, th, tds, lab, bk, rk;
    for (j = 0; j < trs.length; j++) {
      tr = trs[j];
      if (tr.classList.contains("instr-cut-total")) continue;
      if (tr.classList.contains("instr-cut-pending-total")) continue;
      th = tr.querySelector("th");
      tds = tr.querySelectorAll("td");
      if (!th || tds.length < 2) continue;
      lab = String(th.textContent || "").trim();
      bk = CUT_B_BY_LABEL[lab];
      rk = CUT_R_BY_LABEL[lab];
      if (bk && bk in f) tds[0].textContent = String(f[bk] == null ? "" : f[bk]);
      if (rk && rk in f) tds[1].textContent = String(f[rk] == null ? "" : f[rk]);
    }
    recalcInstrCutTotal(panel);
  }
  function recalcInstrCutTotal(panel) {
    var tb = panel.querySelector(".instr-cut tbody");
    if (!tb) return;
    var totalRow = tb.querySelector("tr.instr-cut-total");
    if (!totalRow) return;
    var sumB = 0;
    var sumR = 0;
    var trs = tb.getElementsByTagName("tr");
    var li, j, tr, th, tds, lab;
    for (li = 0; li < CUT_LABELS.length; li++) {
      lab = CUT_LABELS[li];
      for (j = 0; j < trs.length; j++) {
        tr = trs[j];
        if (tr.classList.contains("instr-cut-total")) continue;
        if (tr.classList.contains("instr-cut-pending-total")) continue;
        th = tr.querySelector("th");
        tds = tr.querySelectorAll("td");
        if (!th || tds.length < 2) continue;
        if (String(th.textContent || "").trim() !== lab) continue;
        sumB += parseInt0(tds[0].textContent);
        sumR += parseInt0(tds[1].textContent);
      }
    }
    var tdt = totalRow.querySelectorAll("td");
    if (tdt.length >= 2) {
      tdt[0].textContent = String(sumB);
      tdt[1].textContent = String(sumR);
    }
  }
  function applyNoteHtml(panel, htmlStr) {
    var n = panel.querySelector(".instr-note");
    if (!n) return;
    n.innerHTML = "<strong>\u5099\u8003</strong><br>" + (htmlStr || "");
  }
  function logWarn(msg, detail) {
    try {
      if (detail !== undefined) {
        console.warn("[share-live-edit]", msg, detail);
      } else {
        console.warn("[share-live-edit]", msg);
      }
    } catch (e) {}
  }
  function logInfo(msg, detail) {
    try {
      if (detail !== undefined) {
        console.info("[share-live-edit]", msg, detail);
      } else {
        console.info("[share-live-edit]", msg);
      }
    } catch (e) {}
  }
  function isApiOk(v) {
    if (v === true || v === 1) return true;
    if (typeof v === "string") {
      var t = v.trim().toLowerCase();
      return t === "true" || t === "yes" || t === "1";
    }
    return false;
  }
  function editsArray(data) {
    var e = data && data.edits;
    if (Array.isArray(e)) return e;
    if (e && typeof e === "object") {
      try {
        return Object.keys(e).map(function (k) {
          return e[k];
        });
      } catch (err) {
        return [];
      }
    }
    return [];
  }
  function pickEditsByKey(data, pageDate) {
    var best = {};
    var list = editsArray(data);
    var pd = String(pageDate || "").trim();
    for (var i = 0; i < list.length; i++) {
      var ed = list[i];
      if (!ed) continue;
      var d = String(ed.date != null ? ed.date : "").trim();
      if (d !== pd) continue;
      var k = normKey(ed.management_no_key || ed.management_no || "");
      if (!k) continue;
      var ts = String(ed.timestamp || ed.id || "");
      if (!best[k] || ts > String(best[k].timestamp || best[k].id || "")) {
        best[k] = ed;
      }
    }
    return best;
  }
  function applyEditToArticle(article, ed) {
    var panel = article.querySelector(".note-panel");
    if (!panel) {
      logWarn("note-panel missing on card; cannot apply overlay", article);
      return;
    }
    ensureBanner(article);
    var f = ed.fields || {};
    if ("work_method" in f) setSummaryCell(panel, "\u51e6\u7406\u65b9\u6cd5", f.work_method);
    if ("bucket_truck" in f) setSummaryCell(panel, "B\u8eca", f.bucket_truck);
    if ("road_width" in f) setSummaryCell(panel, "\u9053\u5e45", f.road_width);
    if ("slope" in f) setSummaryCell(panel, "\u50be\u659c", f.slope);
    if (hasV2CutFields(f)) {
      applyCutBandsFromFields(panel, f);
    } else if ("branch_count" in f || "root_count" in f) {
      applyCutTotals(
        panel,
        "branch_count" in f ? f.branch_count : "",
        "root_count" in f ? f.root_count : ""
      );
    }
    if ("bush_area" in f) {
      setOtherCell(panel, "\u67f4\u4f10\u63a1\u9762\u7a4d", f.bush_area);
    }
    if ("bamboo_count" in f) {
      setOtherCell(panel, "\u7af9\u4f10\u63a1\u672c\u6570", f.bamboo_count);
    }
    if ("vine_count" in f) {
      setOtherCell(panel, "\u3064\u308b\u4f10\u63a1\u7b87\u6240\u6570", f.vine_count);
    }
    if ("note" in f) applyNoteHtml(panel, esc(f.note));
  }
  function handlePayload(data, pageDate) {
    var pd = String(pageDate || "").trim();
    if (!data || typeof data !== "object") {
      logWarn("JSONP payload is not an object", data);
      return;
    }
    if (!isApiOk(data.ok)) {
      logWarn("API ok flag is false or missing", { ok: data.ok, keys: Object.keys(data) });
      return;
    }
    var byKey = pickEditsByKey(data, pd);
    var list = editsArray(data);
    var forPage = 0;
    for (var j = 0; j < list.length; j++) {
      var ed0 = list[j];
      if (ed0 && String(ed0.date != null ? ed0.date : "").trim() === pd) forPage++;
    }
    var cardKeys = [];
    document.querySelectorAll("article.card[data-management-no-key]").forEach(function (a) {
      var kk = normKey(a.getAttribute("data-management-no-key"));
      if (kk) cardKeys.push(kk);
    });
    if (forPage > 0 && Object.keys(byKey).length === 0) {
      var rel0 = list
        .filter(function (e) {
          return e && String(e.date != null ? e.date : "").trim() === pd;
        })
        .slice(0, 6)
        .map(function (e) {
          return {
            date: e.date,
            management_no_key: e.management_no_key,
            management_no: e.management_no
          };
        });
      logWarn("edits for page date but no usable management_no_key", {
        pageDate: pd,
        editsForPageSample: rel0
      });
    }
    var applied = 0;
    document.querySelectorAll("article.card[data-management-no-key]").forEach(function (article) {
      var k = normKey(article.getAttribute("data-management-no-key"));
      if (!k || !byKey[k]) return;
      try {
        applyEditToArticle(article, byKey[k]);
        applied++;
      } catch (e) {
        logWarn("applyEditToArticle threw", e);
      }
    });
    if (forPage > 0 && applied === 0) {
      var rel = list
        .filter(function (e) {
          return e && String(e.date != null ? e.date : "").trim() === pd;
        })
        .slice(0, 8)
        .map(function (e) {
          return {
            date: e.date,
            management_no_key: e.management_no_key,
            management_no: e.management_no
          };
        });
      logWarn("No card matched API edits for this page", {
        pageDate: pd,
        cardKeys: cardKeys.slice(0, 12),
        apiKeysFromPicker: Object.keys(byKey),
        editsForPageSample: rel
      });
    }
    try {
      logInfo("jsonp payload handled", {
        pageDate: pd,
        editsTotal: list.length,
        forPage: forPage,
        applied: applied
      });
    } catch (e3) {}
  }
  function run() {
    var c = cfg();
    if (!c) {
      logWarn("share-detail-edit-api-config missing or invalid JSON");
      return;
    }
    var apiUrl = (c && c.url) || "";
    if (!String(apiUrl).trim()) {
      logWarn("API URL empty in config; skip JSONP load");
      return;
    }
    var token = (c && c.token) || "";
    var pageDate = String(document.body.getAttribute("data-share-page-date") || "").trim();
    if (!pageDate) {
      logWarn("body[data-share-page-date] missing; skip");
      return;
    }
    var sep = apiUrl.indexOf("?") >= 0 ? "&" : "?";
    var handlerId =
      "h" + String(Date.now()) + "_" + String(Math.floor(Math.random() * 1e9));
    var cbName = "__ippatsuShareLiveEditNs." + handlerId;
    window.__ippatsuShareLiveEditNs = window.__ippatsuShareLiveEditNs || {};
    var s = document.createElement("script");
    var tid = 0;
    var done = false;
    function finish() {
      if (done) return;
      done = true;
      if (tid) clearTimeout(tid);
      try {
        delete window.__ippatsuShareLiveEditNs[handlerId];
      } catch (e2) {}
      if (s && s.parentNode) s.parentNode.removeChild(s);
    }
    window.__ippatsuShareLiveEditNs[handlerId] = function (data) {
      if (done) return;
      try {
        handlePayload(data, pageDate);
      } catch (e) {
        logWarn("JSONP callback threw", e);
      } finally {
        var fin = function () {
          finish();
        };
        if (typeof requestAnimationFrame === "function") {
          requestAnimationFrame(fin);
        } else {
          setTimeout(fin, 0);
        }
      }
    };
    var url =
      apiUrl +
      sep +
      "token=" +
      encodeURIComponent(token) +
      "&callback=" +
      encodeURIComponent(cbName) +
      "&_ts=" +
      String(Date.now());
    s.async = true;
    s.src = url;
    s.charset = "utf-8";
    tid = setTimeout(function () {
      logWarn("JSONP timeout (check Apps Script JSONP deploy + callback param)");
      finish();
    }, 30000);
    s.onerror = function () {
      logWarn("JSONP script failed to load (network, 404, or non-JavaScript response)");
      finish();
    };
    var head = document.head || document.getElementsByTagName("head")[0] || document.documentElement;
    head.appendChild(s);
  }
  function scheduleRun() {
    function go() {
      try {
        run();
      } catch (e) {
        logWarn("run threw", e);
      }
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        if (typeof requestAnimationFrame === "function") {
          requestAnimationFrame(go);
        } else {
          setTimeout(go, 0);
        }
      });
    } else {
      if (typeof requestAnimationFrame === "function") {
        requestAnimationFrame(go);
      } else {
        setTimeout(go, 0);
      }
    }
  }
  scheduleRun();
})();
"""


def _build_share_live_edit_inject_html(api_url: str, api_token: str) -> str:
    cfg_obj = {"url": (api_url or "").strip(), "token": (api_token or "").strip()}
    cfg_json = json.dumps(cfg_obj, ensure_ascii=False)
    cfg_json = cfg_json.replace("<", "\\u003c")
    parts = [
        _SHARE_LIVE_EDIT_BEGIN,
        "<!-- share-live-edit: JSONP load (CORS-safe); Apps Script must echo callback when token=...&callback=... -->",
        "<style>",
        _SHARE_LIVE_EDIT_CARD_CSS,
        "</style>",
        '<script type="application/json" id="share-detail-edit-api-config">',
        cfg_json,
        "</script>",
        "<script>",
        _SHARE_LIVE_EDIT_RUNNER_JS,
        "</script>",
        _SHARE_LIVE_EDIT_END,
    ]
    return "\n".join(parts)


def apply_share_live_edit_to_share_html(html: str, date_key: str) -> str:
    """未確定修正オーバーレイ用の data 属性・クライアント JS を注入（正本 JSON は触らない）。"""
    out = _strip_share_live_edit_inject_block(html)
    out = _strip_share_live_edit_identity_attrs(out)
    out = _inject_body_data_share_page_date(out, date_key)
    out = _inject_article_card_identity_attrs(out, date_key)
    inject = _build_share_live_edit_inject_html(
        SHARE_DETAIL_EDIT_API_URL, SHARE_DETAIL_EDIT_API_TOKEN
    )
    if "</body>" in out:
        out = out.replace("</body>", inject + "\n</body>", 1)
    else:
        out = out + "\n" + inject
    return out


def _share_detail_edit_api_config_obj() -> dict[str, str]:
    return {
        "url": (SHARE_DETAIL_EDIT_API_URL or "").strip(),
        "token": (SHARE_DETAIL_EDIT_API_TOKEN or "").strip(),
    }


def _share_live_edit_api_config_matches_html(html: str) -> bool:
    """HTML 内の API 設定 JSON が generate_portal.py 定数と一致するか。"""
    m = re.search(
        r'<script\s+type="application/json"\s+id="share-detail-edit-api-config"\s*>\s*'
        r"(\{[^<]+\})\s*</script>",
        html,
        re.I,
    )
    if not m:
        return False
    try:
        got = json.loads(m.group(1))
    except json.JSONDecodeError:
        return False
    exp = _share_detail_edit_api_config_obj()
    return got.get("url") == exp.get("url") and got.get("token") == exp.get("token")


def _share_live_edit_layer_complete(html: str) -> bool:
    """未確定修正オーバーレイに必要なマークアップが揃っているか。"""
    if _SHARE_LIVE_EDIT_BEGIN not in html or _SHARE_LIVE_EDIT_END not in html:
        return False
    if 'id="share-detail-edit-api-config"' not in html:
        return False
    if not re.search(r"<body[^>]*\sdata-share-page-date=\"[^\"]+\"", html, re.I):
        return False
    if "<article class=\"card\"" in html and 'data-management-no-key="' not in html:
        return False
    if (SHARE_DETAIL_EDIT_API_URL or "").strip():
        return _share_live_edit_api_config_matches_html(html)
    return True


def ensure_share_detail_edit_on_share_html(html: str, date_key: str) -> str:
    """詳細修正リンク・未確定修正オーバーレイを idempotent に適用する。"""
    out = _strip_share_live_edit_inject_block(html)
    out = _strip_share_live_edit_identity_attrs(out)
    if share_detail_edit_form_enabled():
        out = apply_share_detail_edit_to_share_html(out, date_key)
    return apply_share_live_edit_to_share_html(out, date_key)


def inject_share_detail_edit_into_share_pages(repo_root: Path) -> int:
    """share/<6桁>/index.html へ詳細修正ボタン・未確定修正オーバーレイ用マークアップを書き込む。"""
    root = repo_root / "share"
    if not root.is_dir():
        return 0
    n = 0
    for sub in sorted(root.iterdir(), key=lambda p: p.name):
        if not sub.is_dir() or not re.fullmatch(r"\d{6}", sub.name):
            continue
        if sub.name.lower() == "sample":
            continue
        idx = sub / "index.html"
        if not idx.is_file():
            continue
        try:
            raw = idx.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        new_t = ensure_share_detail_edit_on_share_html(raw, sub.name)
        needs_write = new_t != raw or not _share_live_edit_layer_complete(raw)
        if not needs_write:
            continue
        idx.write_text(new_t, encoding="utf-8", newline="\n")
        n += 1
        action = "updated" if new_t != raw else "repaired"
        print(f"Wrote {idx} (share detail-edit + live overlay: {action})")
    return n


def inject_share_detail_edit_into_share_page_for_date(
    repo_root: Path, date_key: str
) -> int:
    """``share/<date>/index.html`` のみ詳細修正注入（share-update 用）。"""
    if not re.fullmatch(r"\d{6}", date_key):
        return 0
    idx = repo_root / "share" / date_key / "index.html"
    if not idx.is_file():
        return 0
    try:
        raw = idx.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    new_t = ensure_share_detail_edit_on_share_html(raw, date_key)
    needs_write = new_t != raw or not _share_live_edit_layer_complete(raw)
    if not needs_write:
        return 0
    idx.write_text(new_t, encoding="utf-8", newline="\n")
    action = "updated" if new_t != raw else "repaired"
    print(f"Wrote {idx} (share detail-edit + live overlay: {action})")
    return 1


@dataclass(frozen=True)
class SurveyPublicItem:
    management_no: str
    management_no_key: str
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


def archive_list_detail_href(date_key: str) -> str:
    """portal/archive/index.html 上の「アーカイブ詳細を開く」先。共有ページ有無に依存しない。"""
    return f"./{date_key}/"


def format_archive_row_article(
    entry: ManifestEntry,
    share_summary: ShareSummary | None,
    public_items: list[ArchivePublicItem] | None,
) -> str:
    """1行分のアーカイブカード（data-search 付き）。主リンクは常にアーカイブ詳細（共有ページ URL は使わない）。"""
    folder = entry.date
    date_jp = fallback_heading(folder)
    ctx = build_archive_row_context(entry, share_summary, public_items)
    search_attr = escape_html(ctx.search_blob)
    href = archive_list_detail_href(folder)
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
    <a href="../negotiation/">交渉待ち</a>
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


def _bucket_label_archive(bucket: object) -> str:
    if bucket is True:
        return "可"
    if bucket is False:
        return "不可"
    if isinstance(bucket, str) and bucket.strip() == "一部可能":
        return "一部可能"
    return "未設定"


def _fmt_m2_archive(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}㎡"
    return f"{v:g}㎡"


def _share_detail_prefill_from_source_item(
    src: dict, *, note_fallback: str = ""
) -> ShareDetailEditPrefill:
    """completion_reports の source_item から詳細修正 prefill を組み立てる。"""
    nt = _to_str(src.get("note")) or note_fallback
    if nt == "—":
        nt = ""
    rw = src.get("road_width_m")
    road_width = f"{float(rw):g}m" if rw is not None and _to_str(rw) else ""
    return ShareDetailEditPrefill(
        management_no=_to_str(src.get("management_no")),
        label=_to_str(src.get("label")),
        method=_method_text(src),
        bucket_truck=_bucket_label_archive(src.get("bucket_available")),
        road_width=road_width,
        slope=_to_str(src.get("slope")),
        branch_cut_under_10=str(_as_num(src.get("branch_cut_under_10"))),
        branch_cut_10_20=str(_as_num(src.get("branch_cut_10_20"))),
        branch_cut_20_30=str(_as_num(src.get("branch_cut_20_30"))),
        branch_cut_30_40=str(_as_num(src.get("branch_cut_30_40"))),
        branch_cut_40_50=str(_as_num(src.get("branch_cut_40_50"))),
        branch_cut_over_50=str(_as_num(src.get("branch_cut_over_50"))),
        root_cut_under_10=str(_as_num(src.get("root_cut_under_10"))),
        root_cut_10_20=str(_as_num(src.get("root_cut_10_20"))),
        root_cut_20_30=str(_as_num(src.get("root_cut_20_30"))),
        root_cut_30_40=str(_as_num(src.get("root_cut_30_40"))),
        root_cut_40_50=str(_as_num(src.get("root_cut_40_50"))),
        root_cut_over_50=str(_as_num(src.get("root_cut_over_50"))),
        bush_area=str(_as_num(src.get("brush_area_m2"))),
        bamboo_count=str(_as_num(src.get("bamboo_count"))),
        vine_count=str(_as_num(src.get("vine_locations"))),
        note=nt,
    )


def build_archive_instructions_html_from_source(src: dict) -> str:
    """共有ページと同形式の現場指示表（completion_reports の source_item 由来）。"""
    work = _method_text(src)
    cut_rows: list[str] = []
    branch_sum = 0
    root_sum = 0
    for label, br_key, rt_key in _SHARE_INSTR_CUT_BAND_PREFILL_ROWS:
        bv = _as_num(src.get(br_key))
        rv = _as_num(src.get(rt_key))
        branch_sum += bv
        root_sum += rv
        cut_rows.append(
            f"<tr><th>{escape_html(label)}</th>"
            f"<td>{bv}</td><td>{rv}</td></tr>"
        )
    cut_rows.append(
        f'<tr class="instr-cut-total"><th scope="row">{escape_html("合計")}</th>'
        f"<td>{branch_sum}</td><td>{root_sum}</td></tr>"
    )
    bucket_txt = _bucket_label_archive(src.get("bucket_available"))
    rw_raw = src.get("road_width_m")
    if rw_raw is not None and _to_str(rw_raw):
        rw = f"{float(rw_raw):g}m"
    else:
        rw = "未設定"
    slope_disp = _to_str(src.get("slope")) or "—"
    brush = float(_as_num(src.get("brush_area_m2")))
    bamboo = _as_num(src.get("bamboo_count"))
    vine = _as_num(src.get("vine_locations"))
    summary_tbl = (
        '<table class="instr-table instr-summary"><tbody>'
        f"<tr><th>処理方法</th><td>{escape_html(work)}</td></tr>"
        f"<tr><th>B車</th><td>{escape_html(bucket_txt)}</td></tr>"
        f"<tr><th>道幅</th><td>{escape_html(rw)}</td></tr>"
        f"<tr><th>傾斜</th><td>{escape_html(slope_disp)}</td></tr>"
        "</tbody></table>"
    )
    cut_tbl = (
        '<table class="instr-table instr-cut">'
        '<thead><tr><th scope="col">区分</th>'
        '<th scope="col">枝切り</th><th scope="col">根切り</th></tr></thead><tbody>'
        + "".join(cut_rows)
        + "</tbody></table>"
    )
    other_tbl = (
        '<table class="instr-table instr-other"><tbody>'
        f"<tr><th>柴伐採面積</th><td>{escape_html(_fmt_m2_archive(brush))}</td></tr>"
        f"<tr><th>竹伐採本数</th><td>{bamboo}本</td></tr>"
        f"<tr><th>つる伐採箇所数</th><td>{vine}箇所</td></tr>"
        "</tbody></table>"
    )
    return (
        '<div class="instr-scroll">'
        + summary_tbl
        + '<p class="instr-cut-caption">枝切り・根切り（本数）</p>'
        + cut_tbl
        + '<p class="instr-cut-caption">その他伐採</p>'
        + other_tbl
        + "</div>"
    )


def _completion_reports_root(repo_root: Path) -> Path:
    if _DATA_ROOT_OVERRIDE is not None:
        return _DATA_ROOT_OVERRIDE / "completion_reports"
    return repo_root.parent / "ippatsu-pc" / "data" / "completion_reports"


def _survey_source_path(repo_root: Path) -> Path:
    """現調待ちポータル用。正本は data/survey/queue.json（261231.json は参照しない）。"""
    if _DATA_ROOT_OVERRIDE is not None:
        return _DATA_ROOT_OVERRIDE / "survey" / "queue.json"
    return repo_root.parent / "ippatsu-pc" / "data" / "survey" / "queue.json"


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


def _survey_queue_field_str(v: object) -> str:
    """queue.json の status / survey_status 用。None・空は空文字。"""
    if v is None:
        return ""
    return str(v).strip()


def _survey_done_is_true(v: object) -> bool:
    """survey_done が真とみなすか。未設定・偽は False。"""
    if v is True:
        return True
    if v is False or v is None:
        return False
    s = _survey_queue_field_str(v).lower()
    return s in ("true", "1", "yes", "on")


def _survey_exclude_reason(item: dict) -> str | None:
    """現調待ちポータルから除外する主理由。表示対象なら None。"""
    if _survey_done_is_true(item.get("survey_done")):
        return "survey_done"
    if _survey_queue_field_str(item.get("survey_status")) == "現調済み":
        return "survey_status_done"
    if _survey_queue_field_str(item.get("status")) == "対応中":
        return "status_in_progress"
    return None


def is_pending_survey_item(item: dict) -> bool:
    """queue.json の1件が現調待ちポータルに載せるべきか。

    交渉待ち相当（``is_negotiation_wait_item``）は現調待ちに出さない。
    """
    if is_negotiation_wait_item(item):
        return False
    return _survey_exclude_reason(item) is None


def is_negotiation_wait_item(item: dict) -> bool:
    """queue.json の1件が交渉待ちポータル（M11）に載せるべきか。

    判定条件（いずれかが真）:
      - ``survey_done`` が真（_survey_done_is_true 経由で受理する表現を含む）
      - ``survey_status`` == "現調済み"
      - ``status`` == "対応中"

    M8 の現調待ち除外理由（_survey_exclude_reason）と同条件で構成しているが、
    将来どちらかが独立に変わっても壊れないよう判定基準をここで再宣言する。
    ``is_pending_survey_item`` は本関数が真の行を除外する。
    """
    if _survey_done_is_true(item.get("survey_done")):
        return True
    if _survey_queue_field_str(item.get("survey_status")) == "現調済み":
        return True
    if _survey_queue_field_str(item.get("status")) == "対応中":
        return True
    return False


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
        note_txt = _to_str(src.get("note")) or "—"
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
                note=note_txt,
                instructions_html=build_archive_instructions_html_from_source(src),
                detail_prefill=_share_detail_prefill_from_source_item(
                    src, note_fallback=note_txt if note_txt != "—" else ""
                ),
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


def _empty_survey_load_stats() -> dict[str, Any]:
    return {
        "total": 0,
        "visible": 0,
        "filtered": 0,
        "exclude_reasons": {},
    }


def load_survey_public_items(
    repo_root: Path,
    *,
    exclude_portal_overlay_keys: set[str] | None = None,
) -> tuple[list[SurveyPublicItem], str, dict[str, Any]]:
    """ippatsu-pc 側 data/survey/queue.json を読み、現調待ち表示対象だけ抽出する。

    ``exclude_portal_overlay_keys``: Supabase overlay で negotiation_wait の
    management_no_key。静的 survey HTML から除外する（案件データは削除しない）。
    """
    path = _survey_source_path(repo_root)
    empty_msg = "現調待ちリストはまだありません。"
    if not path.is_file():
        return [], empty_msg, _empty_survey_load_stats()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], empty_msg, _empty_survey_load_stats()
    if not isinstance(raw, dict):
        return [], empty_msg, _empty_survey_load_stats()
    items = raw.get("items")
    if not isinstance(items, list):
        return [], empty_msg, _empty_survey_load_stats()
    out: list[SurveyPublicItem] = []
    exclude_reasons: dict[str, int] = {}
    overlay_exclude = exclude_portal_overlay_keys or set()
    total = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        total += 1
        if not is_pending_survey_item(it):
            if is_negotiation_wait_item(it):
                exclude_reasons["negotiation_wait"] = (
                    exclude_reasons.get("negotiation_wait", 0) + 1
                )
            else:
                reason = _survey_exclude_reason(it)
                if reason:
                    exclude_reasons[reason] = exclude_reasons.get(reason, 0) + 1
            continue
        mno = _to_str(it.get("management_no")) or "—"
        mno_key = management_no_key(mno) if mno != "—" else None
        if mno_key and mno_key in overlay_exclude:
            exclude_reasons["portal_status_overlay"] = (
                exclude_reasons.get("portal_status_overlay", 0) + 1
            )
            continue
        out.append(
            SurveyPublicItem(
                management_no=mno,
                management_no_key=mno_key or "",
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
    stats: dict[str, Any] = {
        "total": total,
        "visible": len(out),
        "filtered": total - len(out),
        "exclude_reasons": exclude_reasons,
    }
    if not out:
        return [], empty_msg, stats
    return out, "", stats


def load_survey_promoted_candidate_items(
    repo_root: Path,
) -> list[SurveyPublicItem]:
    """交渉待ちページの即時昇格カード用メタデータ（現調待ち相当のみ）。

    overlay 除外前の候補。静的 survey から外した案件も昇格カード表示に使う。
    """
    items, _, _ = load_survey_public_items(repo_root, exclude_portal_overlay_keys=set())
    return items


def load_negotiation_public_items(
    repo_root: Path,
) -> tuple[list[SurveyPublicItem], str, dict[str, Any]]:
    """ippatsu-pc 側 data/survey/queue.json を読み、交渉待ち表示対象だけ抽出する（M11）。

    SurveyPublicItem を再利用する。判定は is_negotiation_wait_item に委譲する。
    現調待ちローダ（load_survey_public_items）と並行して queue.json を読み直すが、
    stdlib・小ファイル前提なので I/O 重複は許容する。M8 ローダを壊さないこと優先。
    """
    path = _survey_source_path(repo_root)
    empty_msg = "交渉待ちリストはまだありません。"
    if not path.is_file():
        return [], empty_msg, _empty_survey_load_stats()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], empty_msg, _empty_survey_load_stats()
    if not isinstance(raw, dict):
        return [], empty_msg, _empty_survey_load_stats()
    items = raw.get("items")
    if not isinstance(items, list):
        return [], empty_msg, _empty_survey_load_stats()
    out: list[SurveyPublicItem] = []
    total = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        total += 1
        if not is_negotiation_wait_item(it):
            continue
        mno = _to_str(it.get("management_no")) or "—"
        mno_key = management_no_key(mno) if mno != "—" else None
        out.append(
            SurveyPublicItem(
                management_no=mno,
                management_no_key=mno_key or "",
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
    stats: dict[str, Any] = {
        "total": total,
        "visible": len(out),
        "filtered": total - len(out),
        "exclude_reasons": {},
    }
    if not out:
        return [], empty_msg, stats
    return out, "", stats


def build_survey_html(
    items: list[SurveyPublicItem],
    empty_note: str,
    report_date_iso: str,
    form_base_url: str = SURVEY_REPORT_FORM_URL,
    status_request_endpoint: str = SURVEY_STATUS_REQUEST_ENDPOINT,
    status_request_api_key: str = "",
    portal_status_endpoint: str = PORTAL_CASE_STATUS_ENDPOINT,
    immediate_status: bool | None = None,
    *,
    initial_hidden_overlay_keys: set[str] | None = None,
) -> str:
    use_immediate = (
        immediate_status
        if immediate_status is not None
        else portal_immediate_status_enabled()
    )
    hidden_overlay_keys = initial_hidden_overlay_keys or set()
    if use_immediate:
        survey_mark_hint = (
            "押すと交渉待ちページへ即時に移動します（誤操作は交渉待ちから戻せます）"
        )
        survey_requested_action = "mark_survey_done"
        survey_disclaimer = (
            "「現調済みにする」を押すと交渉待ちへ即時反映します（portal status overlay）。"
            "「返却候補にする」はモック表示です。正本データにはまだ反映しません。"
            "従来の PC 承認待ち方式は PORTAL_IMMEDIATE_STATUS=0 で再生成できます。"
        )
    else:
        survey_mark_hint = "押すとPC側の承認待ちになります（更新依頼を送信）"
        survey_requested_action = "mark_survey_completed"
        survey_disclaimer = (
            "「現調済みにする」は Supabase へ更新依頼（PC反映待ち）を送信します。"
            "いずれも押しただけではこの一覧から消えません。"
        )
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
        portal_request_btns = ""
        if it.management_no_key:
            portal_request_btns = (
                '<div class="card-actions card-actions-portal-request" role="group" '
                'aria-label="現調待ちから交渉待ちへ反映">'
                '<button type="button" class="btn btn-survey-mark-done" '
                'data-survey-mark-done>現調済みにする</button>'
                '<button type="button" class="btn btn-survey-mark-return-candidate" '
                'data-return-candidate-mark>返却候補にする</button>'
                '<p class="survey-mark-hint muted-tiny">'
                f"{survey_mark_hint}"
                "</p>"
                '<p class="survey-mark-status muted-tiny" data-survey-mark-status '
                'hidden role="status"></p>'
                '<p class="return-candidate-status muted-tiny" data-return-candidate-status '
                'hidden role="status"></p>'
                "</div>"
            )
        hidden_attr = ""
        if (
            it.management_no_key
            and it.management_no_key in hidden_overlay_keys
        ):
            hidden_attr = ' hidden data-portal-moved="negotiation"'
        cards.append(
            f"""<article class="card survey-update-card" data-card-index="{idx}"
  data-management-no-key="{escape_html(it.management_no_key)}"
  data-management-no="{escape_html(it.management_no)}"
  data-label="{escape_html(it.label)}"
  data-requested-action="{survey_requested_action}"{hidden_attr}>
  <div class="card-head">
    <h2 class="card-title">{escape_html(it.label)}</h2>
    <p class="item-mgmt">{escape_html(it.management_no)}</p>
    <div class="card-actions">{actions}</div>
    {portal_request_btns}
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
    map_block = """  <section class="return-candidate-section" aria-labelledby="return-candidate-heading">
    <h2 id="return-candidate-heading">返却待ちリスト</h2>
    <p class="muted-tiny return-candidate-note">※ モック表示です。返却待ちの正本反映は未実装です。</p>
    <div id="return-candidate-list" class="return-candidate-list" role="list"></div>
    <p id="return-candidate-empty" class="muted-tiny">返却候補はありません。</p>
  </section>
"""
    points_js = json.dumps(points, ensure_ascii=False)
    if use_immediate:
        survey_portal_js = render_survey_immediate_status_js(
            portal_status_endpoint, status_request_api_key
        )
    else:
        survey_portal_js = render_survey_legacy_request_js(
            status_request_endpoint, status_request_api_key
        )
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
.card-actions-portal-request {{
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
  flex-basis: 100%;
  width: 100%;
  margin-top: 0.35rem;
  padding-top: 0.55rem;
  border-top: 1px dashed var(--border);
}}
.btn-survey-mark-done {{
  min-height: 44px;
  background: #ecfdf5;
  color: #047857;
  border: 2px solid #6ee7b7;
}}
.btn-survey-mark-done:hover, .btn-survey-mark-done:focus-visible {{
  background: #d1fae5;
  outline: none;
}}
.btn-survey-mark-done:disabled {{
  opacity: 0.8;
  cursor: default;
}}
.btn-survey-mark-return-candidate {{
  min-height: 44px;
  background: #fffbeb;
  color: #92400e;
  border: 2px solid #f59e0b;
}}
.btn-survey-mark-return-candidate:hover, .btn-survey-mark-return-candidate:focus-visible {{
  background: #fef3c7;
  outline: none;
}}
.btn-survey-mark-return-candidate:disabled {{
  opacity: 0.8;
  cursor: default;
}}
.survey-mark-hint {{
  margin: 0;
  line-height: 1.4;
}}
.survey-mark-status {{
  margin: 0;
  color: #047857;
  font-weight: 600;
}}
.survey-mark-status.is-error {{
  color: #b45309;
}}
.survey-mark-status[hidden] {{ display: none !important; }}
.return-candidate-status {{
  margin: 0;
  color: #92400e;
  font-weight: 600;
}}
.return-candidate-status.is-error {{
  color: #b45309;
}}
.return-candidate-status[hidden] {{ display: none !important; }}
.survey-update-card.survey-mark-sent {{
  border-color: #a7f3d0;
}}
.survey-update-card.return-candidate-marked {{
  border-color: #f59e0b;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.18);
}}
</style>
</head>
<body>
  <nav class="top-bar" aria-label="サイト内リンク">
    <a href="../">ポータルTOP</a>
    <a href="./">現調待ち</a>
    <a href="../negotiation/">交渉待ち</a>
    <a href="../archive/">アーカイブ</a>
  </nav>
  <h1 class="page-title">現調待ち一覧</h1>
  <p class="lead">径間ごとに地図・現場指示・報告用のリンクがあります。（表示 {len(items)} 件）</p>
  <p class="report-disclaimer">{survey_disclaimer}</p>
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
  // Portal status overlay (B-plan) or legacy pending request (A-plan). Never embed service_role.
{survey_portal_js}
}})();
  </script>
</body>
</html>
"""


def build_negotiation_html(
    items: list[SurveyPublicItem],
    empty_note: str,
    promoted_candidates: list[SurveyPublicItem] | None = None,
    portal_status_endpoint: str = PORTAL_CASE_STATUS_ENDPOINT,
    status_request_api_key: str = "",
    immediate_status: bool | None = None,
) -> str:
    """交渉待ちページ（M11 + B-plan immediate status draft）。

    - 静的生成: queue.json の交渉待ち相当案件。
    - B-plan: apikey + update-portal-case-status で即時昇格/戻し。
    - promoted_candidates: 現調待ち静的候補（即時昇格カード用）。
    """
    use_immediate = (
        immediate_status
        if immediate_status is not None
        else portal_immediate_status_enabled()
    )
    if use_immediate:
        negotiation_disclaimer = (
            "「現調待ちに戻す」は誤操作取り消し用です。"
            "押すと portal status overlay を解除し、現調待ちページへ戻ります。"
            "Google フォーム報告は現調待ちページから行ってください。"
        )
    else:
        negotiation_disclaimer = (
            "このページは閲覧用です。状態を変更するボタン（Supabase送信・Googleフォーム）はありません。"
            "「現調待ちに戻す」は未実装のため無効化しています。"
        )
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
        note_id = f"neg-note-{idx}"
        note_btn = (
            f'<button type="button" class="btn btn-note" aria-expanded="false" '
            f'aria-controls="{note_id}" data-note-toggle>現場指示</button>'
        )
        note_body = f"備考: {escape_html(it.note)}"
        actions = "".join(x for x in [map_btn, two_btn, note_btn] if x)
        if use_immediate and it.management_no_key:
            revert_block = (
                '<div class="card-actions card-actions-revert" role="group" '
                'aria-label="現調待ちに戻す">'
                '<button type="button" class="btn btn-revert" data-negotiation-revert>'
                "現調待ちに戻す"
                "</button>"
                '<p class="revert-hint muted-tiny">誤操作時は現調待ち一覧へ戻せます。</p>'
                '<p class="negotiation-revert-status muted-tiny" '
                'data-negotiation-revert-status hidden role="status"></p>'
                "</div>"
            )
        else:
            revert_block = (
                '<div class="card-actions card-actions-revert" role="group" '
                'aria-label="現調待ちに戻す（未実装）">'
                '<button type="button" class="btn btn-revert-disabled" '
                'disabled aria-disabled="true" '
                'title="現調待ちへ戻す機能は未実装です">'
                "現調待ちに戻す（未実装）"
                "</button>"
                '<p class="revert-hint muted-tiny">'
                "この操作はまだ実装されていません。誤操作防止のため無効化しています。"
                "</p>"
                "</div>"
            )
        cards.append(
            f"""<article class="card negotiation-card" data-card-index="{idx}"
  data-management-no-key="{escape_html(it.management_no_key)}"
  data-management-no="{escape_html(it.management_no)}"
  data-label="{escape_html(it.label)}">
  <div class="card-head">
    <h2 class="card-title">{escape_html(it.label)}</h2>
    <p class="item-mgmt">{escape_html(it.management_no)}</p>
    <div class="card-actions">{actions}</div>
    {revert_block}
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
    map_block = """  <section class="return-candidate-section" aria-labelledby="return-candidate-heading">
    <h2 id="return-candidate-heading">返却待ちリスト</h2>
    <p class="muted-tiny return-candidate-note">※ モック表示です。返却待ちの正本反映は未実装です。</p>
    <div id="return-candidate-list" class="return-candidate-list" role="list"></div>
    <p id="return-candidate-empty" class="muted-tiny">返却候補はありません。</p>
  </section>
"""
    points_js = json.dumps(points, ensure_ascii=False)
    candidates_json = serialize_promoted_candidates(promoted_candidates or [])
    negotiation_portal_js = ""
    if use_immediate:
        negotiation_portal_js = render_negotiation_immediate_status_js(
            portal_status_endpoint,
            status_request_api_key,
            candidates_json,
        )
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>交渉待ち一覧</title>
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
.card-actions-revert {{
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
  flex-basis: 100%;
  width: 100%;
  margin-top: 0.35rem;
  padding-top: 0.55rem;
  border-top: 1px dashed var(--border);
}}
.btn-revert {{
  background: #fff7ed;
  color: #9a3412;
  border: 2px solid #fdba74;
}}
.btn-revert:hover {{
  background: #ffedd5;
}}
.btn-revert-disabled {{
  background: #f1f5f9;
  color: #64748b;
  border: 2px dashed #94a3b8;
  cursor: not-allowed;
  opacity: 0.85;
}}
.btn-revert-disabled:disabled {{
  cursor: not-allowed;
}}
.revert-hint {{
  margin: 0;
  line-height: 1.4;
}}
.return-candidate-section {{
  margin-top: 1.0rem;
  background: var(--card);
  border-radius: 10px;
  border: 1px solid var(--border);
  padding: 0.75rem 1rem 1rem;
  margin-bottom: 0.85rem;
}}
.return-candidate-section h2 {{
  font-size: 1.05rem;
  margin: 0 0 0.5rem;
}}
.return-candidate-note {{
  margin: 0 0 0.55rem;
}}
.return-candidate-list {{
  display: grid;
  gap: 0.55rem;
}}
.return-candidate-item {{
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.55rem 0.6rem;
  background: #fffef8;
}}
.return-candidate-item-head {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.6rem;
}}
.return-candidate-item-title {{
  margin: 0;
  font-size: 0.94rem;
  font-weight: 700;
}}
.return-candidate-item-mgmt {{
  margin: 0.2rem 0 0;
  font-size: 0.8rem;
  color: var(--muted);
}}
.return-candidate-item-meta {{
  margin: 0.35rem 0 0;
  font-size: 0.79rem;
  color: #92400e;
}}
.btn-return-candidate-clear {{
  background: #fff;
  color: #92400e;
  border: 1px solid #f59e0b;
  min-height: 36px;
  padding: 0.35rem 0.6rem;
  font-size: 0.82rem;
}}
.btn-return-candidate-clear:hover,
.btn-return-candidate-clear:focus-visible {{
  background: #fef3c7;
  outline: none;
}}
</style>
</head>
<body>
  <nav class="top-bar" aria-label="サイト内リンク">
    <a href="../">ポータルTOP</a>
    <a href="../survey/">現調待ち</a>
    <a href="./">交渉待ち</a>
    <a href="../archive/">アーカイブ</a>
  </nav>
  <h1 class="page-title">交渉待ち一覧</h1>
  <p class="lead">現調済み・対応中の案件です。地主交渉に進む案件を確認します。（表示 {len(items)} 件）</p>
  <p class="report-disclaimer">{negotiation_disclaimer}</p>
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
  // Portal status overlay (B-plan immediate). Never embed service_role.
{negotiation_portal_js}
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
                else it.completion_status
            )
            reason_line = ""
            if it.completion_status == "incomplete" and it.incomplete_reason != "—":
                reason_line = (
                    f'<p class="archive-status-line">未完了理由: '
                    f"{escape_html(it.incomplete_reason)}</p>"
                )
            warn_line = ""
            if it.warning != "—":
                warn_line = (
                    f'<p class="archive-warn-line">警告: {escape_html(it.warning)}</p>'
                )
            status_header = (
                f'<p class="archive-status-line">状態: {escape_html(status_jp)}</p>'
            )
            instr_block = (it.instructions_html or "").strip()
            if not instr_block:
                instr_block = (
                    f"<p>処理方法: {escape_html(it.method)}</p>"
                    f"<p>備考: {escape_html(it.note)}</p>"
                )
            note_block = ""
            nt = (it.note or "").strip()
            if nt and nt != "—":
                note_esc = escape_html(nt).replace("\n", "<br>")
                note_block = (
                    f'<div class="instr-note"><strong>備考</strong><br>{note_esc}</div>'
                )
            note_body = status_header + reason_line + warn_line + instr_block + note_block
            status_cls = (
                "status-done" if it.completion_status == "completed" else "status-pending"
            )
            note_btn = (
                f'<button type="button" class="btn btn-note" aria-expanded="false" '
                f'aria-controls="{note_id}" data-note-toggle>現場指示</button>'
            )
            detail_edit_btn = ""
            if share_detail_edit_form_enabled():
                edit_url = build_share_detail_edit_url(it, folder)
                if edit_url:
                    detail_edit_btn = _share_detail_edit_link_html(edit_url)
            actions = "".join(x for x in [map_btn, two_btn, note_btn, detail_edit_btn] if x)
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
.btn-detail-edit {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 0.75rem;
  font-size: 0.88rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
  min-height: 44px;
  touch-action: manipulation;
  background: #eff6ff;
  color: #1e3a8a;
  border: 2px solid #2563eb;
  line-height: 1.25;
}}
.card-actions .btn-detail-edit {{
  flex: 1 1 100%;
  max-width: 100%;
}}
.btn-detail-edit:hover, .btn-detail-edit:focus-visible {{
  filter: brightness(1.03);
  outline: none;
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
.archive-status-line,
.archive-warn-line {{
  margin: 0 0 0.5rem;
  font-size: 0.88rem;
}}
.archive-warn-line {{ color: #b45309; }}
.instr-scroll {{
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}}
.instr-table {{
  width: 100%;
  min-width: min(100%, 320px);
  border-collapse: collapse;
  font-size: 0.88rem;
  margin-bottom: 0.65rem;
}}
.instr-table th,
.instr-table td {{
  border: 1px solid var(--border);
  padding: 0.45rem 0.55rem;
  text-align: left;
  vertical-align: top;
}}
.instr-table th {{
  background: #f1f5f9;
  font-weight: 600;
  white-space: nowrap;
}}
.instr-cut-caption {{
  margin: 0.5rem 0 0.35rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--muted);
}}
.instr-cut-total th,
.instr-cut-total td {{
  font-weight: 600;
  background: #f1f5f9;
}}
.instr-note {{
  margin-top: 0.65rem;
  padding-top: 0.55rem;
  border-top: 1px dashed var(--border);
  font-size: 0.92rem;
}}
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
          <a class="portal-menu-item" role="menuitem" href="./negotiation/">交渉待ち</a>
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


PORTAL_MODE_FULL = "full"
PORTAL_MODE_COMPLETION_ARCHIVE = "completion-archive"
PORTAL_MODE_SHARE_UPDATE = "share-update"


def _parse_six_digit_date(value: str) -> str | None:
    """6桁日付キーを正規化。不正なら None。"""
    d = (value or "").strip()
    if len(d) == 6 and d.isdigit():
        return d
    return None


def main() -> int:
    global _DATA_ROOT_OVERRIDE

    parser = argparse.ArgumentParser(
        description=(
            "Regenerate portal HTML from share/ and ippatsu completion_reports / survey queue."
        ),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Path to the ippatsu-pc 'data' directory (contains completion_reports/ and survey/). "
            "Default: <parent of this repo>/ippatsu-pc/data"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=(
            PORTAL_MODE_FULL,
            PORTAL_MODE_COMPLETION_ARCHIVE,
            PORTAL_MODE_SHARE_UPDATE,
        ),
        default=PORTAL_MODE_FULL,
        help=(
            "full: full portal regen (default). "
            "completion-archive: minimal regen for completion report archive sync "
            "(requires --date). "
            "share-update: minimal regen for share-mode publish (requires --date)."
        ),
    )
    parser.add_argument(
        "--date",
        default=None,
        metavar="YYMMDD",
        help=(
            "Target 6-digit date; required when --mode completion-archive "
            "or share-update"
        ),
    )
    ns = parser.parse_args()
    _DATA_ROOT_OVERRIDE = None
    if ns.data_root is not None:
        dr = ns.data_root.expanduser().resolve()
        if not dr.is_dir():
            print(f"Error: --data-root is not a directory: {dr}", file=sys.stderr)
            return 1
        _DATA_ROOT_OVERRIDE = dr

    mode = ns.mode
    target_date: str | None = None
    if mode in (PORTAL_MODE_COMPLETION_ARCHIVE, PORTAL_MODE_SHARE_UPDATE):
        target_date = _parse_six_digit_date(ns.date or "")
        if target_date is None:
            print(
                f"Error: --mode {mode} requires --date YYMMDD (6 digits).",
                file=sys.stderr,
            )
            return 1
    completion_date = (
        target_date if mode == PORTAL_MODE_COMPLETION_ARCHIVE else None
    )

    repo_root = Path(__file__).resolve().parent.parent
    share_dir = repo_root / "share"
    if not share_dir.is_dir():
        print(f"Missing directory: {share_dir}", file=sys.stderr)
        return 1

    if mode == PORTAL_MODE_FULL:
        # ippatsu-pc からの HTML コピー直後でも、ポータル生成前に必ず注入する。
        inject_share_detail_edit_into_share_pages(repo_root)

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
        if mode == PORTAL_MODE_COMPLETION_ARCHIVE and folder == target_date:
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

    if mode == PORTAL_MODE_SHARE_UPDATE:
        assert target_date is not None
        n_inj = inject_share_detail_edit_into_share_page_for_date(
            repo_root, target_date
        )
        print(
            f"share-update mode (date={target_date}): "
            "skipped portal/survey/index.html, portal/negotiation/index.html, "
            "portal/archive/*, other share inject; "
            f"target share inject: {n_inj} file(s)"
        )
        return 0

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
    if mode == PORTAL_MODE_COMPLETION_ARCHIVE:
        detail_entries = [e for e in manifest_entries if e.date == completion_date]
        if not detail_entries:
            print(
                f"Warning: archive manifest has no entry for '{completion_date}'; "
                "skipping portal/archive/<date>/index.html "
                "(merge archive_manifest.json before generate_portal).",
                file=sys.stderr,
            )
    else:
        detail_entries = manifest_entries
    detail_paths = write_archive_detail_pages(repo_root, detail_entries)
    for dp in detail_paths:
        print(f"Wrote {dp}")
    print(
        f"Wrote {arch_path} (manifest={len(manifest_entries)}, "
        f"archive_rows={len(archive_parts)}, recent={len(recent_parts)}, months={len(sections)}, "
        f"archive_details={len(detail_paths)})"
    )
    if mode == PORTAL_MODE_FULL:
        portal_api_key = survey_status_request_api_key()
        if not portal_api_key:
            print(
                "warning: survey portal apikey not set; "
                "set PORTAL_SURVEY_REQUEST_API_KEY or SUPABASE_ANON_KEY "
                "when generating (送信ボタンは無効化されます).",
                file=sys.stderr,
            )
        overlay_neg_keys: set[str] = set()
        if portal_api_key and portal_immediate_status_enabled():
            overlay_neg_keys = fetch_portal_negotiation_wait_keys(
                PORTAL_CASE_STATUS_ENDPOINT, portal_api_key
            )
            if overlay_neg_keys:
                print(
                    f"portal overlay: excluding {len(overlay_neg_keys)} "
                    "negotiation_wait key(s) from static survey list",
                    file=sys.stderr,
                )
        survey_items, survey_empty_note, survey_stats = load_survey_public_items(
            repo_root,
            exclude_portal_overlay_keys=overlay_neg_keys,
        )
        promoted_candidates = load_survey_promoted_candidate_items(repo_root)
        survey_html = build_survey_html(
            survey_items,
            survey_empty_note,
            date.today().isoformat(),
            status_request_api_key=portal_api_key,
            portal_status_endpoint=PORTAL_CASE_STATUS_ENDPOINT,
            initial_hidden_overlay_keys=overlay_neg_keys,
        )
        survey_path = repo_root / "portal" / "survey" / "index.html"
        survey_path.parent.mkdir(parents=True, exist_ok=True)
        survey_path.write_text(survey_html, encoding="utf-8", newline="\n")
        print(
            f"Wrote {survey_path} (survey_items={len(survey_items)}, "
            f"survey_items_total={survey_stats['total']}, "
            f"visible={survey_stats['visible']}, "
            f"filtered={survey_stats['filtered']})"
        )
        if survey_stats.get("exclude_reasons"):
            print(f"  survey_exclude_reasons: {survey_stats['exclude_reasons']}")
        # M11 + B-plan: 交渉待ちページ。即時 status overlay（apikey は publishable/anon のみ）。
        negotiation_items, negotiation_empty_note, negotiation_stats = (
            load_negotiation_public_items(repo_root)
        )
        negotiation_html = build_negotiation_html(
            negotiation_items,
            negotiation_empty_note,
            promoted_candidates=promoted_candidates,
            status_request_api_key=portal_api_key,
            portal_status_endpoint=PORTAL_CASE_STATUS_ENDPOINT,
        )
        negotiation_path = repo_root / "portal" / "negotiation" / "index.html"
        negotiation_path.parent.mkdir(parents=True, exist_ok=True)
        negotiation_path.write_text(
            negotiation_html, encoding="utf-8", newline="\n"
        )
        print(
            f"Wrote {negotiation_path} "
            f"(negotiation_items={len(negotiation_items)}, "
            f"negotiation_items_total={negotiation_stats['total']}, "
            f"visible={negotiation_stats['visible']}, "
            f"filtered={negotiation_stats['filtered']})"
        )
        inject_share_detail_edit_into_share_pages(repo_root)
    else:
        print(
            f"completion-archive mode (date={completion_date}): "
            "skipped portal/survey/index.html, portal/negotiation/index.html, "
            "and share inject; "
            f"wrote {len(detail_paths)} archive detail page(s) only for target date"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
