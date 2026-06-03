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

CLI では ``--data-root <path>`` に ippatsu の ``data`` ディレクトリ（``survey/`` 等）を渡せる。

完了報告アーカイブ詳細は ``--completion-reports-root <path>`` で **副本 JSON のルート**
（例: ippatsu-pc ``output/completion_reports_export``）を明示する。未指定時は
``<data-root>/completion_reports`` または既定 ``ippatsu-pc/data/completion_reports`` に
フォールバックし **legacy fallback** 警告を出す。Supabase 正本モードの公開前運用では
``--completion-reports-root`` を必須にすること（``--strict-completion-reports-root`` で未指定時に停止）。
``data/completion_reports`` の先行最新化は行わない。

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

限定再生成（いずれも ``--data-root`` 可。CLI 起動時に ``.env`` を読み込む）:

``--mode survey-only``: ``portal/survey/index.html`` のみ。
``--mode archive-only``: ``portal/archive/index.html`` のみ。
``--mode portal-top-only``: ``portal/index.html`` のみ。
``--mode negotiation-only``: ``portal/negotiation/index.html`` のみ。

各限定 mode は生成後に HTML スモーク検証を行い、想定外の portal HTML 変更を検出する。
"""

from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import math
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
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
    render_survey_multipin_js,
    serialize_promoted_candidates,
)
from typing import Any

# ippatsu-pc の data ディレクトリ（--data-root で上書き）。未指定時は sibling ippatsu-pc/data。
_DATA_ROOT_OVERRIDE: Path | None = None
# completion_reports 副本 JSON ルート（--completion-reports-root）。YYMMDD.json が直下にあるディレクトリ。
_COMPLETION_REPORTS_ROOT_OVERRIDE: Path | None = None
_STRICT_COMPLETION_REPORTS_ROOT: bool = False
_STRICT_COMPLETION_REPORTS_MISSING: bool = False
_STRICT_COMPLETION_REPORTS_SUMMARY_MISMATCH: bool = False

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


def survey_status_request_api_key(repo_root: Path | None = None) -> str:
    """ポータル HTML 用 apikey（publishable/anon のみ）。service_role は使わない。"""
    for name in (
        "PORTAL_SURVEY_REQUEST_API_KEY",
        "PORTAL_STATUS_API_KEY",
        "SUPABASE_ANON_KEY",
    ):
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
    if repo_root is not None:
        for rel in (
            "portal/negotiation/index.html",
            "portal/survey/index.html",
            "portal/calendar/index.html",
        ):
            path = repo_root / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            m = _PORTAL_STATUS_API_KEY_RE.search(text)
            if not m:
                m = _PORTAL_CALENDAR_API_KEY_RE.search(text)
            if m:
                key = m.group(1)
                if _jwt_role_from_api_key(key) != "service_role":
                    return key
    return ""


PORTAL_CALENDAR_API_ENDPOINT = (
    "https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/company-calendar-events"
)
PORTAL_ORIGIN = "https://pakchee0529.github.io"

_PORTAL_CALENDAR_API_KEY_RE = re.compile(
    r'const PORTAL_CALENDAR_API_KEY = "([^"]+)"'
)
_PORTAL_STATUS_API_KEY_RE = re.compile(
    r'var PORTAL_STATUS_API_KEY = "([^"]+)"'
)


def portal_calendar_api_key(repo_root: Path | None = None) -> str:
    """TOP/calendar 用 apikey（publishable/anon のみ）。"""
    for name in (
        "PORTAL_CALENDAR_API_KEY",
        "PORTAL_SURVEY_REQUEST_API_KEY",
        "SUPABASE_ANON_KEY",
    ):
        raw = (os.environ.get(name) or "").strip()
        if not raw:
            continue
        if _jwt_role_from_api_key(raw) == "service_role":
            print(
                f"warning: {name} looks like service_role; "
                "skipped for portal calendar HTML (use anon/publishable only).",
                file=sys.stderr,
            )
            continue
        return raw
    if repo_root is not None:
        cal_path = repo_root / "portal" / "calendar" / "index.html"
        if cal_path.is_file():
            text = cal_path.read_text(encoding="utf-8", errors="replace")
            m = _PORTAL_CALENDAR_API_KEY_RE.search(text)
            if m:
                key = m.group(1)
                if _jwt_role_from_api_key(key) != "service_role":
                    return key
    return ""


PORTAL_TOP_TODAY_SCHEDULE_CSS = """
.today-schedule {
  margin-bottom: 1.25rem;
  padding: 1rem 1rem 0.85rem;
  background: var(--card-b);
  border: 1px solid var(--border-b);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(20, 32, 51, 0.06);
}
.today-schedule-heading {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
  line-height: 1.35;
}
.today-schedule-note {
  margin: 0 0 0.75rem;
  font-size: 0.82rem;
  color: var(--muted-b);
}
.today-schedule-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.today-schedule-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.55rem 0.65rem;
  border-radius: 8px;
  border: 1px solid transparent;
  border-left-width: 3px;
  font-size: 0.9rem;
  line-height: 1.4;
}
.today-schedule-item.company {
  background: #dbeafe;
  border-color: rgba(37, 99, 235, 0.22);
  border-left-color: #2563eb;
  color: #1e3a8a;
}
.today-schedule-item.absent {
  background: #ffe4e6;
  border-color: rgba(225, 29, 72, 0.22);
  border-left-color: #e11d48;
  color: #9f1239;
}
.today-schedule-item.business_trip {
  background: #ede9fe;
  border-color: rgba(124, 58, 237, 0.22);
  border-left-color: #7c3aed;
  color: #5b21b6;
}
.today-schedule-item.holiday {
  background: #fef3c7;
  border-color: rgba(217, 119, 6, 0.25);
  border-left-color: #d97706;
  color: #92400e;
}
.today-schedule-item.other {
  background: #e2e8f0;
  border-color: rgba(71, 85, 105, 0.22);
  border-left-color: #475569;
  color: #334155;
}
.today-schedule-badge {
  flex-shrink: 0;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.55);
  line-height: 1.2;
}
.today-schedule-body {
  flex: 1;
  min-width: 0;
}
.today-schedule-title {
  font-weight: 700;
  word-break: break-word;
}
.today-schedule-person {
  font-size: 0.8rem;
  opacity: 0.9;
  margin-top: 0.1rem;
}
.today-schedule-empty,
.today-schedule-status {
  margin: 0;
  padding: 0.65rem 0.5rem;
  font-size: 0.9rem;
  color: var(--muted-b);
  text-align: center;
  background: var(--bg-b);
  border-radius: 8px;
}
.today-schedule-status.is-error {
  color: #9f1239;
  background: #fff1f2;
}
.today-schedule-more {
  margin: 0.65rem 0 0;
  font-size: 0.82rem;
  text-align: right;
}
.today-schedule-more a {
  color: var(--accent-b);
  font-weight: 600;
  text-decoration: none;
}
.today-schedule-more a:hover,
.today-schedule-more a:focus-visible {
  text-decoration: underline;
  outline: none;
}
"""


def build_portal_today_schedule_js(calendar_api_key: str) -> str:
    endpoint_js = json.dumps(PORTAL_CALENDAR_API_ENDPOINT)
    api_key_js = json.dumps(calendar_api_key)
    origin_js = json.dumps(PORTAL_ORIGIN)
    return f"""(function () {{
  var CALENDAR_API_ENDPOINT = {endpoint_js};
  var PORTAL_CALENDAR_API_KEY = {api_key_js};
  var PORTAL_ORIGIN = {origin_js};

  var TODAY_SCHEDULE_TYPE_LABELS = {{
    company: "社内",
    absent: "休み",
    business_trip: "出張",
    holiday: "祝日",
    other: "その他"
  }};

  var TODAY_SCHEDULE_TYPE_ORDER = {{
    company: 0,
    business_trip: 1,
    absent: 2,
    holiday: 3,
    other: 4
  }};

  function toLocalYMD(d) {{
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + day;
  }}

  function normalizeTodayEvent(raw) {{
    return {{
      type: raw.type || "other",
      dateStart: raw.dateStart || raw.date_start || "",
      dateEnd: raw.dateEnd || raw.date_end || raw.dateStart || raw.date_start || "",
      title: raw.title != null ? String(raw.title).trim() : "",
      person: raw.person != null ? String(raw.person).trim() : ""
    }};
  }}

  function isEventOnDate(ev, ymd) {{
    var start = ev.dateStart;
    var end = ev.dateEnd || start;
    if (!start) return false;
    return start <= ymd && ymd <= end;
  }}

  function sortTodayEvents(events) {{
    return events.slice().sort(function (a, b) {{
      var ta = TODAY_SCHEDULE_TYPE_ORDER[a.type] != null ? TODAY_SCHEDULE_TYPE_ORDER[a.type] : 9;
      var tb = TODAY_SCHEDULE_TYPE_ORDER[b.type] != null ? TODAY_SCHEDULE_TYPE_ORDER[b.type] : 9;
      if (ta !== tb) return ta - tb;
      return String(a.dateStart).localeCompare(String(b.dateStart));
    }});
  }}

  function renderTodayScheduleStatus(message, extraClass) {{
    var root = document.getElementById("today-schedule-root");
    if (!root) return;
    root.innerHTML = "";
    var el = document.createElement("p");
    el.className = "today-schedule-status" + (extraClass ? " " + extraClass : "");
    el.textContent = message;
    root.appendChild(el);
  }}

  function getTodayScheduleTitle(ev) {{
    if (ev.type === "absent") {{
      var person = ev.person || "";
      var title = ev.title || "";
      if (person) return person + " 休み";
      if (title) return title;
      return "休み";
    }}
    return ev.title || "（無題）";
  }}

  function renderTodaySchedule(events) {{
    var root = document.getElementById("today-schedule-root");
    if (!root) return;
    root.innerHTML = "";
    if (!events || !events.length) {{
      var empty = document.createElement("p");
      empty.className = "today-schedule-empty";
      empty.textContent = "本日の予定はありません";
      root.appendChild(empty);
      return;
    }}
    var list = document.createElement("ul");
    list.className = "today-schedule-list";
    list.setAttribute("role", "list");
    events.forEach(function (ev) {{
      var type = ev.type || "other";
      var li = document.createElement("li");
      li.className = "today-schedule-item " + type;
      li.setAttribute("role", "listitem");
      var badge = document.createElement("span");
      badge.className = "today-schedule-badge";
      badge.textContent = TODAY_SCHEDULE_TYPE_LABELS[type] || "その他";
      var body = document.createElement("div");
      body.className = "today-schedule-body";
      var titleEl = document.createElement("div");
      titleEl.className = "today-schedule-title";
      titleEl.textContent = getTodayScheduleTitle(ev);
      body.appendChild(titleEl);
      if (ev.type === "absent" && ev.title && ev.person) {{
        var sub = document.createElement("div");
        sub.className = "today-schedule-person";
        sub.textContent = ev.title;
        body.appendChild(sub);
      }} else if (ev.person && ev.type !== "absent") {{
        var personEl = document.createElement("div");
        personEl.className = "today-schedule-person";
        personEl.textContent = ev.person;
        body.appendChild(personEl);
      }}
      li.appendChild(badge);
      li.appendChild(body);
      list.appendChild(li);
    }});
    root.appendChild(list);
  }}

  function fetchCalendarMonth(year, month) {{
    var url =
      CALENDAR_API_ENDPOINT +
      "?year=" +
      encodeURIComponent(year) +
      "&month=" +
      encodeURIComponent(month);
    return fetch(url, {{
      method: "GET",
      headers: {{
        apikey: PORTAL_CALENDAR_API_KEY,
        Origin: PORTAL_ORIGIN
      }}
    }}).then(function (res) {{
      return res.json().then(function (data) {{
        if (!res.ok || !data.ok) {{
          throw new Error(data.error || "fetch_failed");
        }}
        return (data.events || []).map(normalizeTodayEvent);
      }});
    }});
  }}

  function loadTodaySchedule() {{
    renderTodayScheduleStatus("本日の予定を読み込み中...");
    var now = new Date();
    var todayYmd = toLocalYMD(now);
    var year = now.getFullYear();
    var month = now.getMonth() + 1;

    if (!PORTAL_CALENDAR_API_KEY || !CALENDAR_API_ENDPOINT) {{
      renderTodayScheduleStatus("本日の予定を取得できませんでした", "is-error");
      return;
    }}

    fetchCalendarMonth(year, month)
      .then(function (monthEvents) {{
        var todayEvents = monthEvents.filter(function (ev) {{
          if (ev.type === "health") return false;
          return isEventOnDate(ev, todayYmd);
        }});
        renderTodaySchedule(sortTodayEvents(todayEvents));
      }})
      .catch(function () {{
        renderTodayScheduleStatus("本日の予定を取得できませんでした", "is-error");
      }});
  }}

  document.addEventListener("visibilitychange", function () {{
    if (document.visibilityState === "visible") {{
      loadTodaySchedule();
    }}
  }});
  window.addEventListener("pageshow", loadTodaySchedule);
  loadTodaySchedule();
}})();"""


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


# 2点地図: 周辺電柱（GPS.json）— 生成時に1回だけ読み込む
_GPS_POLES_CACHE: list[tuple[str, float, float]] | None = None
_NEARBY_POLE_RADIUS_M = 160.0
_NEARBY_POLE_ENDPOINT_EXCLUDE_M = 3.0
_NEARBY_POLE_BBOX_PAD_DEG = 0.003


def gps_json_path(repo_root: Path) -> Path:
    return repo_root.parent / "ippatsu-pc" / "app" / "resources" / "data" / "GPS.json"


def load_gps_poles(repo_root: Path) -> list[tuple[str, float, float]]:
    """GPS.json を name, lat, lng のリストに展開（キャッシュ付き）。"""
    global _GPS_POLES_CACHE
    if _GPS_POLES_CACHE is not None:
        return _GPS_POLES_CACHE
    path = gps_json_path(repo_root)
    if not path.is_file():
        raise FileNotFoundError(f"GPS.json not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"GPS.json must be a JSON object, got {type(raw).__name__}")
    poles: list[tuple[str, float, float]] = []
    for name, coord in raw.items():
        if not isinstance(name, str) or not isinstance(coord, str):
            continue
        parts = coord.split(",")
        if len(parts) != 2:
            continue
        lat = _to_float(parts[0].strip())
        lng = _to_float(parts[1].strip())
        if lat is None or lng is None:
            continue
        poles.append((name.strip(), lat, lng))
    _GPS_POLES_CACHE = poles
    return poles


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def nearby_poles_for_two_point(
    poles: list[tuple[str, float, float]],
    a_lat: float,
    a_lng: float,
    b_lat: float,
    b_lng: float,
    *,
    radius_m: float = _NEARBY_POLE_RADIUS_M,
) -> list[dict[str, Any]]:
    """始点・終点・中点のいずれかから radius_m 以内の電柱（端点±3m は除外）。"""
    mid_lat = (a_lat + b_lat) / 2.0
    mid_lng = (a_lng + b_lng) / 2.0
    anchors = ((a_lat, a_lng), (b_lat, b_lng), (mid_lat, mid_lng))
    pad = _NEARBY_POLE_BBOX_PAD_DEG
    min_lat = min(a_lat, b_lat, mid_lat) - pad
    max_lat = max(a_lat, b_lat, mid_lat) + pad
    min_lng = min(a_lng, b_lng, mid_lng) - pad
    max_lng = max(a_lng, b_lng, mid_lng) + pad
    seen: set[tuple[str, float, float]] = set()
    out: list[dict[str, Any]] = []
    for name, lat, lng in poles:
        if lat < min_lat or lat > max_lat or lng < min_lng or lng > max_lng:
            continue
        if (
            min(haversine_m(lat, lng, a_lat, a_lng), haversine_m(lat, lng, b_lat, b_lng))
            <= _NEARBY_POLE_ENDPOINT_EXCLUDE_M
        ):
            continue
        dist = min(haversine_m(lat, lng, al, ag) for al, ag in anchors)
        if dist > radius_m:
            continue
        key = (name, round(lat, 5), round(lng, 5))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "name": name,
                "lat": lat,
                "lng": lng,
                "distance_m": round(dist, 1),
            }
        )
    out.sort(key=lambda row: float(row["distance_m"]))
    return out


def json_for_script_tag(data: Any) -> str:
    """application/json 用（HTML エスケープせず、< のみ \\u003c）。"""
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def format_two_geo_script(two_json_id: str, two_geo: dict[str, Any]) -> str:
    return (
        f'<script type="application/json" id="{two_json_id}">'
        f"{json_for_script_tag(two_geo)}</script>"
    )


def build_two_geo_payload(
    *,
    a_name: str,
    a_lat: float,
    a_lng: float,
    b_name: str,
    b_lat: float,
    b_lng: float,
    gps_poles: list[tuple[str, float, float]] | None = None,
) -> dict[str, Any]:
    geo: dict[str, Any] = {
        "a": {"name": a_name, "lat": a_lat, "lng": a_lng},
        "b": {"name": b_name, "lat": b_lat, "lng": b_lng},
    }
    if gps_poles is not None:
        nearby = nearby_poles_for_two_point(gps_poles, a_lat, a_lng, b_lat, b_lng)
        filtered_nearby: list[dict[str, Any]] = []
        for p in nearby:
            if not isinstance(p, dict):
                continue
            plat = p.get("lat")
            plng = p.get("lng")
            lat_v = plat if isinstance(plat, (int, float)) else _to_float(plat)
            lng_v = plng if isinstance(plng, (int, float)) else _to_float(plng)
            if _valid_jp_latlng(lat_v, lng_v):
                filtered_nearby.append(p)
        geo["nearby"] = filtered_nearby
    return geo


def two_map_click_handler_js() -> str:
    """Leaflet 2点地図 + 周辺電柱（geo.nearby 任意）。"""
    return """
  var twoMaps = Object.create(null);
  document.querySelectorAll("[data-two-open]").forEach(function(btn) {
    var wrapId = btn.getAttribute("data-two-wrap");
    var mapId = btn.getAttribute("data-two-map");
    var jsonId = btn.getAttribute("data-two-json");
    var wrap = wrapId ? document.getElementById(wrapId) : null;
    var jsonEl = jsonId ? document.getElementById(jsonId) : null;
    if (!wrap || !jsonEl) return;
    btn.addEventListener("click", function() {
      var nowOpen = btn.getAttribute("aria-expanded") === "true";
      wrap.hidden = nowOpen;
      btn.setAttribute("aria-expanded", nowOpen ? "false" : "true");
      btn.textContent = nowOpen ? "2点地図を表示" : "2点地図を閉じる";
      if (nowOpen) return;
      var geo = null;
      try {
        geo = JSON.parse(jsonEl.textContent || "{}");
      } catch (e) {
        return;
      }
      if (!geo || !geo.a || !geo.b) return;
      var key = mapId;
      if (!twoMaps[key]) {
        var mmap = L.map(mapId, { scrollWheelZoom: false });
        twoMaps[key] = mmap;
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: "&copy; OpenStreetMap contributors",
        }).addTo(mmap);
      }
      var mmap = twoMaps[key];
      mmap.eachLayer(function(layer) {
        if (layer instanceof L.Marker || layer instanceof L.Polyline || layer instanceof L.CircleMarker) {
          mmap.removeLayer(layer);
        }
      });
      function addEndpoint(p, cls) {
        var lat = Number(p.lat), lng = Number(p.lng);
        if (!isFinite(lat) || !isFinite(lng)) return null;
        var m = L.marker([lat, lng]).addTo(mmap);
        if (p.name) {
          m.bindTooltip(String(p.name), {
            permanent: true,
            direction: "top",
            className: cls,
            offset: [0, -6],
          });
        }
        m.on("click", function() {
          window.open(gmaps(lat, lng), "_blank", "noopener,noreferrer");
        });
        return [lat, lng];
      }
      function addNearbyPole(p) {
        var lat = Number(p.lat), lng = Number(p.lng);
        if (!isFinite(lat) || !isFinite(lng)) return null;
        var m = L.circleMarker([lat, lng], {
          radius: 5,
          weight: 2,
          opacity: 0.9,
          fillOpacity: 0.75,
          color: "#64748b",
          fillColor: "#94a3b8",
        }).addTo(mmap);
        if (p.name) {
          m.bindTooltip(String(p.name), {
            permanent: true,
            direction: "top",
            className: "two-tip-nearby",
            offset: [0, -4],
          });
        }
        m.on("click", function() {
          window.open(gmaps(lat, lng), "_blank", "noopener,noreferrer");
        });
        return [lat, lng];
      }
      var aPt = addEndpoint(geo.a, "two-tip-endpoint");
      var bPt = addEndpoint(geo.b, "two-tip-endpoint");
      var boundsPts = [];
      if (aPt) boundsPts.push(aPt);
      if (bPt) boundsPts.push(bPt);
      if (aPt && bPt) {
        L.polyline([aPt, bPt], { weight: 3, opacity: 0.85, color: "#2563eb" }).addTo(mmap);
      }
      if (Array.isArray(geo.nearby)) {
        geo.nearby.forEach(function(p) {
          var pt = addNearbyPole(p);
          if (pt) boundsPts.push(pt);
        });
      }
      if (boundsPts.length === 1) {
        mmap.setView(boundsPts[0], 17);
      } else if (boundsPts.length > 1) {
        mmap.fitBounds(boundsPts, {
          paddingTopLeft: [40, 70],
          paddingBottomRight: [40, 70],
          maxZoom: 18,
        });
      }
      setTimeout(function() { mmap.invalidateSize(); }, 60);
    });
  });
"""


def two_map_tooltip_css() -> str:
    return """
.leaflet-tooltip.two-tip-endpoint {
  font-weight: 700;
  font-size: 0.88rem;
  padding: 3px 8px;
  border: 1px solid #2563eb;
  background: #eff6ff;
  color: #1e3a8a;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18);
  white-space: nowrap;
}
.leaflet-tooltip.two-tip-nearby {
  font-weight: 500;
  font-size: 0.76rem;
  padding: 2px 6px;
  border: 1px solid #94a3b8;
  background: #f8fafc;
  color: #334155;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
  white-space: nowrap;
}
.leaflet-tooltip.two-tip {
  font-weight: 600;
  font-size: 0.85rem;
  padding: 2px 6px;
  border: none;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
}
"""


def survey_case_action_row_css() -> str:
    """案件操作ボタン横並び（survey カード用）。"""
    return """
.survey-case-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  width: 100%;
  align-items: stretch;
}
.survey-case-action-row .btn-survey-mark-done,
.survey-case-action-row .btn-survey-mark-return-candidate {
  flex: 1 1 calc(50% - 0.25rem);
  min-width: 8.5rem;
  margin: 0;
}
"""


def render_portal_subpage_menu_css(*, archive: bool = False) -> str:
    """ハンバーガーメニュー（survey / archive / negotiation 下位ページ共通）。"""
    if archive:
        t, c, b, a = "--text-b", "--card-b", "--border-b", "--accent-b"
    else:
        t, c, b, a = "--text", "--card", "--border", "--accent"
    return f"""
.portal-page-header {{
  margin-bottom: 0.35rem;
}}
.portal-page-header-row {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}}
.portal-page-header-row .page-title {{
  flex: 1;
  min-width: 0;
  margin: 0 0 0.35rem;
  padding: 0.5rem 0;
  border-bottom: 2px solid var({b});
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
  color: var({t});
  background: var({c});
  border: 1px solid var({b});
  border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(20, 32, 51, 0.06);
}}
.portal-menu-btn:hover,
.portal-menu-btn:focus-visible {{
  border-color: var({a});
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
  z-index: 30;
  min-width: 12.5rem;
  padding: 0.35rem 0;
  background: var({c});
  border: 1px solid var({b});
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
  color: var({t});
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
  background: #f1f5f9;
  outline: none;
}}
.portal-menu-item.is-current {{
  font-weight: 700;
  background: #f1f5f9;
}}
"""


def render_portal_subpage_header(page_title: str, *, page: str) -> str:
    """page: survey | negotiation | archive"""
    items: list[tuple[str, str, str | None]] = [
        ("../", "ポータルTOP", None),
        ("../calendar/", "社内カレンダー", None),
        ("../survey/", "現調待ち", "survey"),
        ("../negotiation/", "交渉待ち", "negotiation"),
        ("../archive/", "アーカイブ", "archive"),
    ]
    link_lines: list[str] = []
    for href, label, page_id in items:
        is_current = page_id == page
        href_use = "./" if is_current else href
        cls = "portal-menu-item is-current" if is_current else "portal-menu-item"
        current_attr = ' aria-current="page"' if is_current else ""
        link_lines.append(
            f'          <a class="{cls}" role="menuitem" href="{escape_html(href_use)}"'
            f'{current_attr}>{escape_html(label)}</a>'
        )
    links = "\n".join(link_lines)
    return f"""  <header class="portal-page-header">
    <div class="portal-page-header-row">
      <h1 class="page-title">{escape_html(page_title)}</h1>
      <div class="portal-menu-wrap">
        <button type="button" class="portal-menu-btn" id="portal-menu-btn" aria-expanded="false" aria-haspopup="true" aria-controls="portal-menu-panel" aria-label="サイトメニューを開く">
          <span class="portal-menu-icon" aria-hidden="true">☰</span>
          <span class="portal-menu-label">メニュー</span>
        </button>
        <nav id="portal-menu-panel" class="portal-menu-panel" role="menu" hidden>
{links}
        </nav>
      </div>
    </div>
  </header>"""


def render_negotiation_return_candidate_css() -> str:
    return """
.return-candidate-section {
  margin-top: 1.0rem;
  background: var(--card);
  border-radius: 10px;
  border: 1px solid var(--border);
  padding: 0.75rem 1rem 1rem;
  margin-bottom: 0.85rem;
}
.return-candidate-section h2 {
  font-size: 1.05rem;
  margin: 0 0 0.5rem;
}
.return-candidate-note {
  margin: 0 0 0.55rem;
}
.return-candidate-list {
  display: grid;
  gap: 0.55rem;
}
.return-candidate-item {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.55rem 0.6rem;
  background: #fffef8;
}
.return-candidate-item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.6rem;
}
.return-candidate-item-title {
  margin: 0;
  font-size: 0.94rem;
  font-weight: 700;
}
.return-candidate-item-mgmt {
  margin: 0.2rem 0 0;
  font-size: 0.8rem;
  color: var(--muted);
}
.return-candidate-item-meta {
  margin: 0.35rem 0 0;
  font-size: 0.79rem;
  color: #92400e;
}
.btn-return-candidate-clear {
  background: #fff;
  color: #92400e;
  border: 1px solid #f59e0b;
  min-height: 36px;
  padding: 0.35rem 0.6rem;
  font-size: 0.82rem;
}
.btn-return-candidate-clear:hover,
.btn-return-candidate-clear:focus-visible {
  background: #fef3c7;
  outline: none;
}
"""


def render_negotiation_return_candidate_section() -> str:
    return """
  <section class="return-candidate-section" aria-labelledby="return-candidate-heading">
    <h2 id="return-candidate-heading">返却候補（overlay補助）</h2>
    <p class="muted-tiny return-candidate-note">補助情報です。返却待ちの正本表示は上段の Supabase return_wait を参照してください。</p>
    <div id="return-candidate-list" class="return-candidate-list" role="list"></div>
    <p id="return-candidate-empty" class="muted-tiny">返却候補はありません。</p>
  </section>
"""


def render_negotiation_return_wait_section(
    items: list[SurveyPublicItem],
    smoke: ReturnWaitSmoke,
    *,
    use_immediate: bool,
) -> str:
    cards: list[str] = []
    points: list[dict] = []
    for it in items:
        if use_immediate and (it.management_no_key or "").strip():
            revert_block = (
                '<div class="card-actions card-actions-revert" role="group" '
                'aria-label="現調待ちに戻す">'
                '<button type="button" class="btn btn-revert" data-negotiation-revert>'
                "現調待ちに戻す"
                "</button>"
                '<p class="revert-hint muted-tiny">返却待ちから現調待ち一覧へ戻せます。</p>'
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
                "</div>"
            )
        cards.append(
            f"""    <article class="card negotiation-card return-wait-card" role="listitem"
      data-management-no-key="{escape_html(it.management_no_key)}"
      data-management-no="{escape_html(it.management_no)}"
      data-label="{escape_html(it.label or '—')}">
      <div class="card-head">
        <div>
          <h3 class="card-title">{escape_html(it.label or "—")}</h3>
          <p class="item-mgmt">{escape_html(it.management_no or "—")}</p>
        </div>
        {revert_block}
      </div>
      <p class="return-candidate-item-meta">正本: cases.status=return_wait</p>
    </article>"""
        )
    cards_html = (
        "\n".join(cards)
        if cards
        else '    <p class="muted-tiny">Supabase正本の返却待ちはありません。</p>'
    )
    summary = (
        f"DB {smoke.db_return_wait_count} 件 / 表示 {smoke.displayed_return_wait_count} 件 / "
        f"overlay補助 {smoke.overlay_return_candidate_count} 件"
    )
    return f"""
  <section class="return-candidate-section" aria-labelledby="return-wait-heading">
    <h2 id="return-wait-heading">返却待ち（正本）</h2>
    <p class="muted-tiny return-candidate-note">{escape_html(summary)}</p>
    <div class="return-candidate-list" role="list">
{cards_html}
    </div>
  </section>
"""


def render_portal_subpage_menu_js() -> str:
    return """
(function () {
  var btn = document.getElementById("portal-menu-btn");
  var panel = document.getElementById("portal-menu-panel");
  if (!btn || !panel) return;
  function setOpen(open) {
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  }
  btn.addEventListener("click", function (ev) {
    ev.stopPropagation();
    setOpen(panel.hidden);
  });
  document.addEventListener("click", function () {
    setOpen(false);
  });
  panel.addEventListener("click", function (ev) {
    ev.stopPropagation();
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") setOpen(false);
  });
})();
"""


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
    planned_incomplete_count: int | None = None
    reported_at: str | None = None
    href: str | None = None
    display_suffix: str | None = None


@dataclass(frozen=True)
class PlannedIncompleteItem:
    """当日予定・未完了（items とは別。完了扱いではない）。"""

    key: str
    management_no: str
    label: str
    incomplete_reason: str
    current_status: str
    active_display: str
    completion_report_ref_display: str
    note: str
    map_url: str


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
class ReturnWaitSmoke:
    db_return_wait_count: int
    displayed_return_wait_count: int
    overlay_return_candidate_count: int
    duplicate_management_no_count: int
    warnings_count: int
    db_return_wait_management_no_keys: list[str]
    displayed_management_no_keys: list[str]


@dataclass(frozen=True)
class StatusSmoke:
    db_count: int
    displayed_count: int
    legacy_count: int
    duplicate_management_no_count: int
    warnings_count: int
    db_management_no_keys: list[str]
    displayed_management_no_keys: list[str]
    status: str


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
        planned_incomplete_count=_coerce_manifest_int(d.get("planned_incomplete_count")),
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
    if _prefer_export_derived_manifest_counts() and public_items is not None:
        item_n = len(public_items)
    else:
        item_n = (
            entry.item_count
            if entry.item_count is not None
            else (
                len(public_items)
                if public_items
                else (share_summary.item_count if share_summary else 0)
            )
        )
        if entry.completed_count is not None:
            completed = entry.completed_count
        if entry.incomplete_count is not None:
            incomplete = entry.incomplete_count
    pi = entry.planned_incomplete_count
    if pi is not None and pi > 0:
        status_summary = f"完了 {completed}件 / 当日未完了 {pi}件"
        tokens.append("当日未完了")
    else:
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
    pi = entry.planned_incomplete_count or 0
    if pi > 0:
        count_display = f"完了 {ctx.item_count}件 / 当日未完了 {pi}件"
        status_block = ""
    else:
        count_display = f"{ctx.item_count}件"
        status_block = (
            f'<div class="archive-status">{escape_html(ctx.status_summary)}</div>'
        )
    return f"""    <article class="archive-row" data-search="{search_attr}">
      <div class="archive-row-top">
        <div class="archive-main">{escape_html(ctx.span_summary)}</div>
        <div class="archive-count">{escape_html(count_display)}</div>
      </div>
      <div class="archive-meta">{escape_html(date_jp)} <span class="archive-dkey">({escape_html(folder)})</span></div>
      {status_block}
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

    subpage_header = render_portal_subpage_header("現場共有アーカイブ", page="archive")
    subpage_menu_css = render_portal_subpage_menu_css(archive=True)
    subpage_menu_js = render_portal_subpage_menu_js()

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
{subpage_menu_css}
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
{subpage_header}
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
  <script>
{subpage_menu_js}
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
    if _COMPLETION_REPORTS_ROOT_OVERRIDE is not None:
        return _COMPLETION_REPORTS_ROOT_OVERRIDE.resolve()
    if _DATA_ROOT_OVERRIDE is not None:
        return (_DATA_ROOT_OVERRIDE / "completion_reports").resolve()
    return (
        repo_root.parent / "ippatsu-pc" / "data" / "completion_reports"
    ).resolve()


def _completion_reports_root_source_label() -> str:
    if _COMPLETION_REPORTS_ROOT_OVERRIDE is not None:
        return "explicit"
    if _DATA_ROOT_OVERRIDE is not None:
        return "legacy_fallback_via_data_root"
    return "legacy_fallback_default"


def _print_completion_reports_root_info(
    repo_root: Path,
    *,
    strict_root: bool,
) -> int:
    """completion_reports 読込ルートをログ出力。strict 時は明示 root 必須。"""
    root = _completion_reports_root(repo_root)
    source = _completion_reports_root_source_label()
    if _COMPLETION_REPORTS_ROOT_OVERRIDE is None:
        print(
            "Warning: --completion-reports-root not set; using legacy fallback "
            f"({source}): {root}",
            file=sys.stderr,
        )
        print(
            "  For Supabase SOT / pre-publish portal generation, pass "
            "--completion-reports-root to output/completion_reports_export "
            "(do not refresh data/completion_reports before publish).",
            file=sys.stderr,
        )
        if strict_root:
            print(
                "Error: --strict-completion-reports-root requires "
                "--completion-reports-root.",
                file=sys.stderr,
            )
            return 1
    else:
        if not root.is_dir():
            print(
                f"Error: --completion-reports-root is not a directory: {root}",
                file=sys.stderr,
            )
            return 1
        print(f"completion_reports_root={root} (source={source})")
    _print_export_summary_if_present(root)
    return 0


def _print_export_summary_if_present(cr_root: Path) -> None:
    summary_path = cr_root / "export_summary.json"
    if not summary_path.is_file():
        return
    try:
        raw = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"Warning: could not read export_summary.json: {exc}",
            file=sys.stderr,
        )
        return
    if not isinstance(raw, dict):
        return
    exported_at = raw.get("exported_at") or raw.get("generated_at")
    if exported_at:
        print(f"export_summary.exported_at={exported_at}")
    dates = raw.get("dates")
    if not isinstance(dates, list):
        return
    print(f"export_summary: {len(dates)} date(s) in {summary_path.name}")
    for ent in dates:
        if not isinstance(ent, dict):
            continue
        dk = ent.get("date_key") or ent.get("date") or "?"
        ic = ent.get("item_count")
        cc = ent.get("case_count")
        print(f"  export_summary date={dk} item_count={ic} case_count={cc}")


def _export_summary_item_count(cr_root: Path, date_key: str) -> int | None:
    summary_path = cr_root / "export_summary.json"
    if not summary_path.is_file():
        return None
    try:
        raw = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    dates = raw.get("dates") if isinstance(raw, dict) else None
    if not isinstance(dates, list):
        return None
    for ent in dates:
        if not isinstance(ent, dict):
            continue
        dk = ent.get("date_key") or ent.get("date")
        if str(dk) == date_key:
            ic = ent.get("item_count")
            if isinstance(ic, int):
                return ic
            if isinstance(ic, str) and ic.isdigit():
                return int(ic)
    return None


def _prefer_export_derived_manifest_counts() -> bool:
    """--completion-reports-root 指定時は export 読取件数を manifest/一覧に優先。"""
    return _COMPLETION_REPORTS_ROOT_OVERRIDE is not None


def _refresh_manifest_title_item_suffix(title: str | None, item_n: int) -> str | None:
    if not title:
        return title
    t = title.strip()
    if re.search(r"\d+件\s*$", t):
        return re.sub(r"\d+件\s*$", f"{item_n}件", t)
    return title


def sync_archive_manifest_counts_from_completion_export(
    repo_root: Path,
) -> list[str]:
    """explicit completion-reports-root 時、読取副本の件数で archive_manifest.json を更新。"""
    if not _prefer_export_derived_manifest_counts():
        return []
    path = repo_root / "portal" / "archive_manifest.json"
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: could not sync archive_manifest.json: {exc}", file=sys.stderr)
        return []
    if not isinstance(raw, dict):
        return []
    entries = raw.get("entries")
    if not isinstance(entries, list):
        return []
    changed: list[str] = []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        date_key = ent.get("date")
        if not isinstance(date_key, str) or not re.fullmatch(r"\d{6}", date_key.strip()):
            continue
        date_key = date_key.strip()
        pub_items, _ = load_archive_public_items(repo_root, date_key)
        if pub_items is None:
            continue
        item_n = len(pub_items)
        completed = incomplete = 0
        for it in pub_items:
            st = (it.completion_status or "").strip()
            if st == "completed":
                completed += 1
            elif st == "incomplete":
                incomplete += 1
        prev_item = ent.get("item_count")
        prev_completed = ent.get("completed_count")
        prev_incomplete = ent.get("incomplete_count")
        planned_n = _planned_incomplete_count_for_date(repo_root, date_key)
        prev_planned = ent.get("planned_incomplete_count")
        if (
            prev_item == item_n
            and prev_completed == completed
            and prev_incomplete == incomplete
            and prev_planned == (planned_n if planned_n else None)
        ):
            continue
        ent["item_count"] = item_n
        ent["completed_count"] = completed
        ent["incomplete_count"] = incomplete
        if planned_n > 0:
            ent["planned_incomplete_count"] = planned_n
        elif "planned_incomplete_count" in ent:
            ent.pop("planned_incomplete_count", None)
        title = ent.get("title")
        if isinstance(title, str):
            ent["title"] = _refresh_manifest_title_item_suffix(title, item_n)
        changed.append(date_key)
    if not changed:
        return []
    path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return changed


def _check_archive_items_vs_export_summary(
    repo_root: Path,
    date_key: str,
    item_count: int,
    *,
    strict_mismatch: bool,
) -> None:
    expected = _export_summary_item_count(_completion_reports_root(repo_root), date_key)
    if expected is None:
        return
    if expected == item_count:
        return
    msg = (
        f"Warning: archive {date_key} loaded {item_count} item(s) but "
        f"export_summary item_count={expected}"
    )
    if strict_mismatch:
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)
    print(msg, file=sys.stderr)


def _survey_source_path(repo_root: Path) -> Path:
    """現調待ちポータル用 legacy/cache パス（正本は Supabase + GPS.json。261231.json は参照しない）。"""
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
    """queue.json の1件が現調待ちポータルに載せるべきか。"""
    return _survey_exclude_reason(item) is None


def is_negotiation_wait_item(item: dict) -> bool:
    """queue.json の1件が交渉待ちポータル（M11）に載せるべきか。

    判定条件（いずれかが真）:
      - ``survey_done`` が真（_survey_done_is_true 経由で受理する表現を含む）
      - ``survey_status`` == "現調済み"
      - ``status`` == "対応中"

    M8 の現調待ち除外理由（_survey_exclude_reason）と同条件で構成しているが、
    将来どちらかが独立に変わっても壊れないよう判定基準をここで再宣言する。
    現状は is_pending_survey_item と相補的に動くため、両方 True になることはない。
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


def load_archive_planned_incomplete(
    repo_root: Path, date_key: str
) -> list[PlannedIncompleteItem]:
    """副本 JSON の planned_but_incomplete[]（items とは別読取）。"""
    base = _completion_reports_root(repo_root)
    path = base / f"{date_key}.json"
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, dict):
        return []
    arr = raw.get("planned_but_incomplete")
    if not isinstance(arr, list):
        return []
    out: list[PlannedIncompleteItem] = []
    for ent in arr:
        if not isinstance(ent, dict):
            continue
        key = _to_str(ent.get("key")) or _to_str(ent.get("management_no"))
        mno = _to_str(ent.get("management_no")) or "—"
        label = _to_str(ent.get("label")) or "—"
        ref = ent.get("completion_report_ref")
        ref_disp = "なし" if ref is None or not _to_str(ref) else _to_str(ref)
        active = ent.get("active")
        if active is True:
            active_disp = "true"
        elif active is False:
            active_disp = "false"
        else:
            active_disp = _to_str(active) or "—"
        src = ent.get("source_item") if isinstance(ent.get("source_item"), dict) else {}
        map_url = _to_str(src.get("map_url"))
        out.append(
            PlannedIncompleteItem(
                key=key or management_no_key(mno) or mno,
                management_no=mno,
                label=label,
                incomplete_reason=_to_str(ent.get("incomplete_reason")) or "—",
                current_status=_to_str(ent.get("current_status")) or "—",
                active_display=active_disp,
                completion_report_ref_display=ref_disp,
                note=_to_str(ent.get("note"))
                or "当日予定・未完了。完了扱いではありません。",
                map_url=map_url,
            )
        )
    return out


def _planned_incomplete_count_for_date(repo_root: Path, date_key: str) -> int:
    return len(load_archive_planned_incomplete(repo_root, date_key))


def build_planned_incomplete_section_html(
    items: list[PlannedIncompleteItem],
) -> str:
    if not items:
        return ""
    cards: list[str] = []
    for idx, it in enumerate(items):
        map_btn = ""
        if it.map_url.startswith(("http://", "https://")):
            map_btn = (
                f'<a class="btn btn-map" href="{escape_html(it.map_url)}" '
                'target="_blank" rel="noopener noreferrer">地図を開く</a>'
            )
        reason_line = ""
        if it.incomplete_reason and it.incomplete_reason != "—":
            reason_line = (
                f'<p class="archive-status-line">未完了理由: '
                f"{escape_html(it.incomplete_reason)}</p>"
            )
        cards.append(
            f"""<article class="card card-planned-incomplete" data-planned-index="{idx}">
      <div class="card-head">
        <h2 class="card-title">{escape_html(it.label)} <span class="status-pill status-pending">未完了</span></h2>
        <p class="item-mgmt">{escape_html(it.management_no)}</p>
        <div class="card-actions">{map_btn}</div>
      </div>
      {reason_line}
</article>"""
        )
    cards_str = "\n".join(cards)
    return f"""  <section class="planned-incomplete-section" aria-labelledby="planned-incomplete-heading">
    <h2 id="planned-incomplete-heading" class="archive-section-heading">当日予定・未完了</h2>
    <p class="disclaimer-note">この枠は、当日予定に含まれていたが完了しなかった案件です。現在の進行状況は各ポータル一覧の正本を参照してください。</p>
{cards_str}
  </section>
"""


def _to_float(v: str) -> float | None:
    s = (v or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# 業務対象範囲（奈良/和歌山/三重周辺）を広めに取った妥当緯度経度。
# この範囲外（国外・0,0・lat/lng取り違え等）は地図UIへ出さない。
_PORTAL_LAT_MIN = 33.0
_PORTAL_LAT_MAX = 36.0
_PORTAL_LNG_MIN = 134.0
_PORTAL_LNG_MAX = 137.0

# 不正座標の警告を生成中に収集する（management_no, 理由）。
_MAP_COORD_WARNINGS: list[tuple[str, str]] = []


def _reset_map_coord_warnings() -> None:
    _MAP_COORD_WARNINGS.clear()


def _record_map_coord_warning(management_no: str, reason: str) -> None:
    _MAP_COORD_WARNINGS.append((management_no or "—", reason))


def _drain_map_coord_warnings() -> list[tuple[str, str]]:
    out = list(_MAP_COORD_WARNINGS)
    _MAP_COORD_WARNINGS.clear()
    return out


def _valid_jp_latlng(lat: float | None, lng: float | None) -> bool:
    """日本国内・業務範囲の妥当な緯度経度か。None/0/範囲外は False。"""
    if lat is None or lng is None:
        return False
    if lat == 0.0 or lng == 0.0:
        return False
    if not (_PORTAL_LAT_MIN <= lat <= _PORTAL_LAT_MAX):
        return False
    if not (_PORTAL_LNG_MIN <= lng <= _PORTAL_LNG_MAX):
        return False
    return True


_SURVEY_ARTICLE_MULTIPIN_RE = re.compile(
    r'(<article[^>]*data-management-no-key="([^"]+)"[^>]*?)'
    r'data-multipin-lat="([^"]+)"([^>]*?)data-multipin-lng="([^"]+)"',
    re.MULTILINE | re.DOTALL,
)


def _multipin_data_attrs(lat: float, lng: float) -> str:
    """HTML 出力直前の最終ガード。範囲外なら空文字（属性を出さない）。"""
    if not _valid_jp_latlng(lat, lng):
        return ""
    return f' data-multipin-lat="{lat}" data-multipin-lng="{lng}"'


def find_survey_html_multipin_violations(html: str) -> list[dict[str, Any]]:
    """生成済み survey HTML 内の #share-map 用 multipin 座標を検査。"""
    violations: list[dict[str, Any]] = []
    for m in _SURVEY_ARTICLE_MULTIPIN_RE.finditer(html):
        key = m.group(2)
        try:
            lat = float(m.group(3))
            lng = float(m.group(5))
        except ValueError:
            violations.append(
                {
                    "management_no_key": key,
                    "lat": m.group(3),
                    "lng": m.group(5),
                    "reason": "non_numeric",
                    "html_line": html[: m.start()].count("\n") + 1,
                }
            )
            continue
        if not _valid_jp_latlng(lat, lng):
            chunk = html[max(0, m.start() - 500) : m.end()]
            label_m = re.search(r'data-label="([^"]*)"', chunk)
            mgmt_m = re.search(r'data-management-no="([^"]*)"', chunk)
            violations.append(
                {
                    "management_no_key": key,
                    "management_no": mgmt_m.group(1) if mgmt_m else "",
                    "label": label_m.group(1) if label_m else "",
                    "lat": lat,
                    "lng": lng,
                    "reason": "out_of_jp_portal_bounds",
                    "html_line": html[: m.start()].count("\n") + 1,
                }
            )
    return violations


def finalize_survey_map_html(html: str) -> str:
    """HTML 書き込み直前: 範囲外 multipin 属性を除去（二重ガード）。"""
    violations = find_survey_html_multipin_violations(html)
    if not violations:
        return html
    for v in violations:
        _record_map_coord_warning(
            str(v.get("management_no") or v.get("management_no_key") or "?"),
            "html_output_stripped_invalid_multipin "
            f"lat={v.get('lat')} lng={v.get('lng')} line={v.get('html_line')}",
        )

    def _strip_bad(match: re.Match[str]) -> str:
        try:
            lat = float(match.group(3))
            lng = float(match.group(5))
        except ValueError:
            return match.group(1) + match.group(4)
        if _valid_jp_latlng(lat, lng):
            return match.group(0)
        return match.group(1) + match.group(4)

    return _SURVEY_ARTICLE_MULTIPIN_RE.sub(_strip_bad, html)


def _validated_single_latlng(
    item: "SurveyPublicItem", *, record: bool = True
) -> tuple[float, float] | None:
    """カードの単点座標を妥当性チェック付きで返す。不正なら None。"""
    a, b = _pick_survey_item_latlng(item)
    lat = _to_float(a)
    lng = _to_float(b)
    if lat is None and lng is None:
        return None
    if _valid_jp_latlng(lat, lng):
        return (lat, lng)  # type: ignore[return-value]
    if record:
        _record_map_coord_warning(
            item.management_no,
            f"single_latlng_out_of_range lat={lat} lng={lng}",
        )
    return None


def _validated_two_latlng(
    item: "SurveyPublicItem", *, record: bool = True
) -> tuple[float, float, float, float] | None:
    """開始/終了の2点座標を妥当性チェック付きで返す。どちらか不正なら None。"""
    s_lat = _to_float(item.start_lat)
    s_lng = _to_float(item.start_lng)
    e_lat = _to_float(item.end_lat)
    e_lng = _to_float(item.end_lng)
    if s_lat is None and s_lng is None and e_lat is None and e_lng is None:
        return None
    if _valid_jp_latlng(s_lat, s_lng) and _valid_jp_latlng(e_lat, e_lng):
        return (s_lat, s_lng, e_lat, e_lng)  # type: ignore[return-value]
    if record:
        _record_map_coord_warning(
            item.management_no,
            "two_point_latlng_out_of_range "
            f"start=({s_lat},{s_lng}) end=({e_lat},{e_lng})",
        )
    return None


def _empty_survey_load_stats() -> dict[str, Any]:
    return {
        "total": 0,
        "visible": 0,
        "filtered": 0,
        "exclude_reasons": {},
    }


def _load_survey_public_items_legacy(
    repo_root: Path,
) -> tuple[list[SurveyPublicItem], str, dict[str, Any]]:
    """legacy: queue.json 由来の現調待ち抽出（補助件数比較のみ）。"""
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
    total = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        total += 1
        reason = _survey_exclude_reason(it)
        if reason:
            exclude_reasons[reason] = exclude_reasons.get(reason, 0) + 1
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
        "exclude_reasons": exclude_reasons,
    }
    if not out:
        return [], empty_msg, stats
    return out, "", stats


def _load_negotiation_public_items_legacy(
    repo_root: Path,
) -> tuple[list[SurveyPublicItem], str, dict[str, Any]]:
    """legacy: queue.json 由来の交渉待ち抽出（補助件数比較のみ）。"""
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


def _fetch_cases_by_status_from_supabase(status: str) -> list[dict[str, Any]] | None:
    creds = _supabase_rest_ready()
    if creds is None:
        return None
    url, key = creds
    endpoint = (
        f"{url.rstrip('/')}/rest/v1/cases"
        "?select=*"
        f"&status=eq.{quote(status, safe='')}"
        "&active=eq.true"
        "&order=management_no_key.asc"
    )
    req = urllib.request.Request(
        endpoint,
        method="GET",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        print(f"warning: {status} fetch failed: {e}", file=sys.stderr)
        return []
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(f"warning: {status} fetch invalid JSON", file=sys.stderr)
        return []
    if not isinstance(data, list):
        print(f"warning: {status} fetch response is not a list", file=sys.stderr)
        return []
    out: list[dict[str, Any]] = []
    for row in data:
        if isinstance(row, dict):
            out.append(row)
    return out


def _load_status_public_items(
    *,
    status: str,
    legacy_count: int,
    empty_msg: str,
) -> tuple[list[SurveyPublicItem], str, dict[str, Any], StatusSmoke]:
    rows = _fetch_cases_by_status_from_supabase(status)
    if rows is None:
        smoke = StatusSmoke(
            db_count=0,
            displayed_count=0,
            legacy_count=legacy_count,
            duplicate_management_no_count=0,
            warnings_count=1,
            db_management_no_keys=[],
            displayed_management_no_keys=[],
            status=status,
        )
        print(
            f"warning: {status} primary source unavailable "
            "(SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing)",
            file=sys.stderr,
        )
        return [], empty_msg, _empty_survey_load_stats(), smoke
    items: list[SurveyPublicItem] = []
    db_keys: list[str] = []
    for row in rows:
        mno = _to_str(row.get("management_no")) or "—"
        key = _to_str(row.get("management_no_key")) or (management_no_key(mno) or "")
        db_keys.append(key)
        items.append(
            SurveyPublicItem(
                management_no=mno,
                management_no_key=key,
                label=_to_str(row.get("label")) or "—",
                map_url=_to_str(row.get("map_url")),
                start_label=_to_str(row.get("start_label")),
                start_lat=_to_str(row.get("start_lat")),
                start_lng=_to_str(row.get("start_lng")),
                end_label=_to_str(row.get("end_label")),
                end_lat=_to_str(row.get("end_lat")),
                end_lng=_to_str(row.get("end_lng")),
                note=_to_str(row.get("note")) or "—",
            )
        )
    db_keys_sorted = sorted(k for k in db_keys if k)
    shown_keys_sorted = sorted(
        {
            str(it.management_no_key or "").strip()
            for it in items
            if str(it.management_no_key or "").strip()
        }
    )
    dup_count = max(len(db_keys_sorted) - len(shown_keys_sorted), 0)
    warnings = 1 if dup_count > 0 else 0
    smoke = StatusSmoke(
        db_count=len(db_keys_sorted),
        displayed_count=len(shown_keys_sorted),
        legacy_count=legacy_count,
        duplicate_management_no_count=dup_count,
        warnings_count=warnings,
        db_management_no_keys=db_keys_sorted,
        displayed_management_no_keys=shown_keys_sorted,
        status=status,
    )
    stats: dict[str, Any] = {
        "total": len(rows),
        "visible": len(items),
        "filtered": max(len(rows) - len(items), 0),
        "exclude_reasons": {},
        "db_count": smoke.db_count,
        "displayed_count": smoke.displayed_count,
        "legacy_count": smoke.legacy_count,
        "db_management_no_keys": smoke.db_management_no_keys,
        "displayed_management_no_keys": smoke.displayed_management_no_keys,
    }
    if not items:
        return [], empty_msg, stats, smoke
    return items, "", stats, smoke


def _legacy_queue_item_keys(items: list[SurveyPublicItem]) -> set[str]:
    return {
        str(it.management_no_key or "").strip()
        for it in items
        if str(it.management_no_key or "").strip()
    }


def _record_legacy_queue_audit(
    primary_items: list[SurveyPublicItem],
    legacy_items: list[SurveyPublicItem],
) -> tuple[list[SurveyPublicItem], dict[str, Any]]:
    """queue.json は件数比較・差分警告のみ。座標・カード表示フィールドは変更しない。"""
    primary_keys = _legacy_queue_item_keys(primary_items)
    legacy_keys = _legacy_queue_item_keys(legacy_items)
    queue_only = sorted(legacy_keys - primary_keys)
    primary_only = sorted(primary_keys - legacy_keys)
    if queue_only:
        sample = ",".join(queue_only[:8])
        _record_map_coord_warning(
            "",
            f"legacy_queue_keys_not_in_supabase count={len(queue_only)} sample={sample}",
        )
    if legacy_keys and len(legacy_keys) != len(primary_keys):
        _record_map_coord_warning(
            "",
            "legacy_queue_key_count_mismatch "
            f"legacy={len(legacy_keys)} supabase={len(primary_keys)}",
        )
    audit: dict[str, Any] = {
        "legacy_queue_key_count": len(legacy_keys),
        "legacy_queue_keys_only_in_queue": queue_only,
        "legacy_queue_keys_only_in_primary": primary_only,
    }
    return primary_items, audit


def _supplement_map_fields_from_gps(
    items: list[SurveyPublicItem], repo_root: Path
) -> list[SurveyPublicItem]:
    """地図座標の主ソース: GPS.json（Supabase 行に座標が無い案件を label で補完）。"""
    gps_path = gps_json_path(repo_root)
    pc_root = repo_root.parent / "ippatsu-pc"
    if not gps_path.is_file() or not pc_root.is_dir():
        return items
    try:
        if str(pc_root) not in sys.path:
            sys.path.insert(0, str(pc_root))
        from app.core.loader import load_pole_coords  # noqa: PLC0415
        from tools.preview_survey_wait_additions_20260529 import (  # noqa: PLC0415
            share_gps_autofill,
        )
    except ImportError:
        return items
    pole_coords, _ = load_pole_coords(gps_path)
    if not pole_coords:
        return items
    out: list[SurveyPublicItem] = []
    for it in items:
        if _validated_two_latlng(it, record=False) is not None:
            out.append(it)
            continue
        label = (it.label or "").strip()
        if not label or label == "—":
            out.append(it)
            continue
        gps = share_gps_autofill(label, pole_coords)

        def _gps_num(v: object) -> float | None:
            if isinstance(v, (int, float)):
                return float(v)
            return _to_float(v)

        s_lat = _gps_num(gps.get("start_lat"))
        s_lng = _gps_num(gps.get("start_lng"))
        e_lat = _gps_num(gps.get("end_lat"))
        e_lng = _gps_num(gps.get("end_lng"))
        if not (_valid_jp_latlng(s_lat, s_lng) and _valid_jp_latlng(e_lat, e_lng)):
            out.append(it)
            continue
        out.append(
            SurveyPublicItem(
                management_no=it.management_no,
                management_no_key=it.management_no_key,
                label=it.label,
                map_url=_to_str(gps.get("map_url")) or "",
                start_label=_to_str(gps.get("start_label")) or "",
                start_lat=str(s_lat),
                start_lng=str(s_lng),
                end_label=_to_str(gps.get("end_label")) or "",
                end_lat=str(e_lat),
                end_lng=str(e_lng),
                note=it.note,
            )
        )
    return out


def load_survey_public_items(
    repo_root: Path,
) -> tuple[list[SurveyPublicItem], str, dict[str, Any]]:
    """現調待ち主ソース: Supabase cases.status=survey_wait。queue.json は補助件数。"""
    _reset_map_coord_warnings()
    legacy_items, _, _legacy_stats = _load_survey_public_items_legacy(repo_root)
    items, empty, stats, smoke = _load_status_public_items(
        status="survey_wait",
        legacy_count=len(legacy_items),
        empty_msg="現調待ちリストはまだありません。",
    )
    items, legacy_audit = _record_legacy_queue_audit(items, legacy_items)
    items = _supplement_map_fields_from_gps(items, repo_root)
    stats.update(legacy_audit)
    stats["legacy_source"] = "queue.json (audit only)"
    stats["gps_map_field_primary"] = True
    stats["source_of_truth"] = "supabase cases.status=survey_wait"
    stats["legacy_map_field_fallback_enabled"] = False
    stats["duplicate_management_no_count"] = smoke.duplicate_management_no_count
    return items, empty, stats


def load_negotiation_public_items(
    repo_root: Path,
) -> tuple[list[SurveyPublicItem], str, dict[str, Any]]:
    """交渉待ち主ソース: Supabase cases.status=negotiation_wait。queue.json は補助件数。"""
    _reset_map_coord_warnings()
    legacy_items, _, _legacy_stats = _load_negotiation_public_items_legacy(repo_root)
    items, empty, stats, smoke = _load_status_public_items(
        status="negotiation_wait",
        legacy_count=len(legacy_items),
        empty_msg="交渉待ちリストはまだありません。",
    )
    items, legacy_audit = _record_legacy_queue_audit(items, legacy_items)
    stats.update(legacy_audit)
    stats["legacy_source"] = "queue.json (audit only)"
    stats["source_of_truth"] = "supabase cases.status=negotiation_wait"
    stats["legacy_map_field_fallback_enabled"] = False
    stats["duplicate_management_no_count"] = smoke.duplicate_management_no_count
    return items, empty, stats


def _supabase_rest_ready() -> tuple[str, str] | None:
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    return url, key


def _fetch_return_wait_cases_from_supabase() -> list[dict[str, Any]] | None:
    creds = _supabase_rest_ready()
    if creds is None:
        return None
    url, key = creds
    endpoint = (
        f"{url.rstrip('/')}/rest/v1/cases"
        "?select=*"
        "&status=eq.return_wait"
        "&active=eq.true"
        "&archive_state=is.null"
        "&returned_at=is.null"
        "&completed_at=is.null"
        "&order=management_no_key.asc"
    )
    req = urllib.request.Request(
        endpoint,
        method="GET",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        print(f"warning: return_wait fetch failed: {e}", file=sys.stderr)
        return []
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print("warning: return_wait fetch invalid JSON", file=sys.stderr)
        return []
    if not isinstance(data, list):
        print("warning: return_wait fetch response is not a list", file=sys.stderr)
        return []
    out: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        out.append(row)
    return out


def _fetch_overlay_return_candidate_count(endpoint: str, api_key: str) -> int:
    ep = (endpoint or "").strip()
    key = (api_key or "").strip()
    if not ep or not key:
        return 0
    req = urllib.request.Request(
        ep + "?list=return_candidates",
        method="GET",
        headers={"apikey": key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return 0
    if not isinstance(data, dict):
        return 0
    rows = data.get("return_candidates")
    if not isinstance(rows, list):
        return 0
    return sum(1 for r in rows if isinstance(r, dict))


def load_return_wait_public_items(
    *,
    portal_status_endpoint: str,
    portal_api_key: str,
) -> tuple[list[SurveyPublicItem], ReturnWaitSmoke]:
    rows = _fetch_return_wait_cases_from_supabase()
    if rows is None:
        smoke = ReturnWaitSmoke(
            db_return_wait_count=0,
            displayed_return_wait_count=0,
            overlay_return_candidate_count=_fetch_overlay_return_candidate_count(
                portal_status_endpoint, portal_api_key
            ),
            duplicate_management_no_count=0,
            warnings_count=1,
            db_return_wait_management_no_keys=[],
            displayed_management_no_keys=[],
        )
        print(
            "warning: return_wait primary source unavailable "
            "(SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing)",
            file=sys.stderr,
        )
        return [], smoke

    items: list[SurveyPublicItem] = []
    db_keys: list[str] = []
    for row in rows:
        mno = _to_str(row.get("management_no")) or "—"
        key = _to_str(row.get("management_no_key")) or (management_no_key(mno) or "")
        db_keys.append(key)
        items.append(
            SurveyPublicItem(
                management_no=mno,
                management_no_key=key,
                label=_to_str(row.get("label")) or "—",
                map_url=_to_str(row.get("map_url")),
                start_label="",
                start_lat=_to_str(row.get("start_lat")),
                start_lng=_to_str(row.get("start_lng")),
                end_label="",
                end_lat=_to_str(row.get("end_lat")),
                end_lng=_to_str(row.get("end_lng")),
                note=_to_str(row.get("note")) or "—",
            )
        )

    db_keys_sorted = sorted(k for k in db_keys if k)
    shown_keys_sorted = sorted(
        {str(it.management_no_key or "").strip() for it in items if str(it.management_no_key or "").strip()}
    )
    dup_count = max(len(db_keys_sorted) - len(shown_keys_sorted), 0)
    overlay_cnt = _fetch_overlay_return_candidate_count(
        portal_status_endpoint, portal_api_key
    )
    warnings = 0
    if dup_count > 0:
        warnings += 1
    smoke = ReturnWaitSmoke(
        db_return_wait_count=len(db_keys_sorted),
        displayed_return_wait_count=len(shown_keys_sorted),
        overlay_return_candidate_count=overlay_cnt,
        duplicate_management_no_count=dup_count,
        warnings_count=warnings,
        db_return_wait_management_no_keys=db_keys_sorted,
        displayed_management_no_keys=shown_keys_sorted,
    )
    return items, smoke


def build_survey_html(
    items: list[SurveyPublicItem],
    empty_note: str,
    report_date_iso: str,
    form_base_url: str = SURVEY_REPORT_FORM_URL,
    status_request_endpoint: str = SURVEY_STATUS_REQUEST_ENDPOINT,
    status_request_api_key: str = "",
    portal_status_endpoint: str = PORTAL_CASE_STATUS_ENDPOINT,
    immediate_status: bool | None = None,
    initial_hidden_overlay_keys: set[str] | None = None,
    repo_root: Path | None = None,
) -> str:
    root = repo_root or Path(__file__).resolve().parent.parent
    gps_poles = load_gps_poles(root)
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
            "「現調済みにする」で交渉待ちへ即時反映します（portal status overlay）。"
            "「返却候補にする」はサーバーに登録し、この一覧から非表示になります。"
            "誤操作は交渉待ちページの「現調待ちに戻す」で取り消せます。"
            "従来の PC 承認待ち方式は PORTAL_IMMEDIATE_STATUS=0 で再生成できます。"
        )
    else:
        survey_mark_hint = "押すとPC側の承認待ちになります（更新依頼を送信）"
        survey_requested_action = "mark_survey_completed"
        survey_disclaimer = (
            "「現調済みを報告」「返却候補を報告」は Google フォームに送信します。"
            "「現調済みにする」は Supabase へ更新依頼（PC反映待ち）を送信します。"
            "いずれも押しただけではこの一覧から消えません。"
        )
    cards: list[str] = []
    points: list[dict] = []
    for idx, it in enumerate(items):
        # 単点地図ボタン: 妥当な単点座標があるときだけ。map_url は信用せず座標から生成。
        map_btn = ""
        single = _validated_single_latlng(it)
        if single is not None:
            s_lat, s_lng = single
            map_btn = (
                f'<a class="btn btn-map" '
                f'href="https://www.google.com/maps?q={s_lat},{s_lng}" '
                'target="_blank" rel="noopener noreferrer">地図を表示</a>'
            )
        # 2点地図ボタン: 開始/終了の2点がどちらも妥当なときだけ。
        two_btn = ""
        two_json = ""
        two_wrap = ""
        two = _validated_two_latlng(it)
        if two is not None:
            start_lat, start_lng, end_lat, end_lng = two
            two_json_id = f"two-geo-{idx}"
            two_wrap_id = f"two-wrap-{idx}"
            two_map_id = f"share-two-map-{idx}"
            two_btn = (
                f'<button type="button" class="btn btn-map" data-two-open '
                f'data-two-wrap="{two_wrap_id}" data-two-map="{two_map_id}" '
                f'data-two-json="{two_json_id}" aria-expanded="false" '
                f'aria-controls="{two_wrap_id}">2点地図を表示</button>'
            )
            two_geo = build_two_geo_payload(
                a_name=it.start_label or it.label,
                a_lat=start_lat,
                a_lng=start_lng,
                b_name=it.end_label or it.label,
                b_lat=end_lat,
                b_lng=end_lng,
                gps_poles=gps_poles,
            )
            two_json = format_two_geo_script(two_json_id, two_geo)
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
        report_btns = ""
        if not use_immediate:
            url_done = build_survey_report_url(
                form_base_url,
                it.management_no,
                it.label,
                SURVEY_REPORT_TYPE_JP_COMPLETED,
                report_date_iso,
            )
            url_return = build_survey_report_url(
                form_base_url,
                it.management_no,
                it.label,
                SURVEY_REPORT_TYPE_JP_RETURN_CANDIDATE,
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
        portal_request_btns = ""
        if it.management_no_key:
            if use_immediate:
                portal_request_btns = (
                    '<div class="card-actions card-actions-portal-request" role="group" '
                    'aria-label="案件操作">'
                    '<div class="survey-case-action-row" role="group" aria-label="案件操作">'
                    '<button type="button" class="btn btn-survey-mark-done" '
                    'data-survey-mark-done>現調済みにする</button>'
                    '<button type="button" class="btn btn-survey-mark-return-candidate" '
                    'data-return-candidate-mark>返却候補にする</button>'
                    "</div>"
                    '<p class="survey-mark-hint muted-tiny">'
                    f"{survey_mark_hint}"
                    "</p>"
                    '<p class="survey-mark-status muted-tiny" data-survey-mark-status '
                    'hidden role="status"></p>'
                    '<p class="return-candidate-status muted-tiny" data-return-candidate-status '
                    'hidden role="status"></p>'
                    "</div>"
                )
            else:
                portal_request_btns = (
                    '<div class="card-actions card-actions-portal-request" role="group" '
                    'aria-label="現調済み（PC承認待ち）">'
                    '<button type="button" class="btn btn-survey-mark-done" '
                    'data-survey-mark-done>現調済みにする</button>'
                    '<p class="survey-mark-hint muted-tiny">'
                    f"{survey_mark_hint}"
                    "</p>"
                    '<p class="survey-mark-status muted-tiny" data-survey-mark-status '
                    'hidden role="status"></p>'
                    "</div>"
                )
        hidden_attr = ""
        if it.management_no_key and it.management_no_key in hidden_overlay_keys:
            hidden_attr = ' hidden data-portal-moved="negotiation"'
        # マルチピンも妥当 JP 座標のときだけ載せる（国外/0/取り違えは除外）。
        multipin_attr = ""
        mp = _validated_single_latlng(it, record=False)
        f_lat_mp = f_lng_mp = None
        if mp is not None:
            f_lat_mp, f_lng_mp = mp
            multipin_attr = _multipin_data_attrs(f_lat_mp, f_lng_mp)
            if not multipin_attr:
                f_lat_mp = f_lng_mp = None
                _record_map_coord_warning(
                    it.management_no,
                    "multipin_attr_rejected_at_html_emit",
                )
        cards.append(
            f"""<article class="card survey-update-card" data-card-index="{idx}"
  data-management-no-key="{escape_html(it.management_no_key)}"
  data-management-no="{escape_html(it.management_no)}"
  data-label="{escape_html(it.label)}"
  data-requested-action="{survey_requested_action}"{multipin_attr}{hidden_attr}>
  <div class="card-head">
    <h2 class="card-title">{escape_html(it.label)}</h2>
    <p class="item-mgmt">{escape_html(it.management_no)}</p>
    <div class="card-actions">{actions}</div>
    {report_btns}
    {portal_request_btns}
  </div>
  {two_json}
  {two_wrap}
  <div class="note-panel" id="{note_id}" hidden>{note_body}</div>
</article>"""
        )
        if f_lat_mp is not None and f_lng_mp is not None:
            points.append(
                {
                    "name": it.label,
                    "lat": f_lat_mp,
                    "lng": f_lng_mp,
                    "management_no": it.management_no,
                }
            )
    items_html = "\n".join(cards)
    if not items_html:
        items_html = f'<p class="muted-tiny">{escape_html(empty_note)}</p>'
    if points:
        map_block = """  <section class="map-section" aria-labelledby="map-heading">
    <h2 id="map-heading">全体地図</h2>
    <p class="muted-tiny survey-multipin-empty" hidden role="status">表示対象の位置情報がありません。</p>
    <div id="share-map" role="application" aria-label="全径間の位置"></div>
  </section>
"""
    else:
        map_block = """  <section class="map-section map-empty" aria-labelledby="map-heading">
    <h2 id="map-heading">全体地図</h2>
    <p class="muted-tiny">まとめて表示できる位置情報がありません。</p>
  </section>
"""
    if use_immediate:
        survey_portal_js = render_survey_immediate_status_js(
            portal_status_endpoint, status_request_api_key
        )
    else:
        survey_portal_js = render_survey_legacy_request_js(
            status_request_endpoint, status_request_api_key
        )
    subpage_header = render_portal_subpage_header("現調待ち一覧", page="survey")
    subpage_menu_css = render_portal_subpage_menu_css()
    subpage_menu_js = render_portal_subpage_menu_js()
    survey_action_css = survey_case_action_row_css() if use_immediate else ""
    html_body = f"""<!DOCTYPE html>
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
{subpage_menu_css}
{survey_action_css}
.lead {{
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
  color: var(--muted);
}}
.survey-visible-count-line {{
  font-weight: 600;
  color: var(--text);
}}
.survey-visible-count-line strong {{
  font-weight: 700;
}}
.survey-count-hint {{
  display: inline;
  margin-left: 0.35rem;
  font-size: 0.82rem;
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
{two_map_tooltip_css()}
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
.card-actions-portal-request {{
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
  flex-basis: 100%;
  width: 100%;
  margin-top: 0.35rem;
  padding-top: 0.55rem;
  border-top: 1px solid var(--border);
}}
.btn-survey-mark-done {{
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
.survey-overlay-warning {{
  margin: 0 0 0.75rem;
  padding: 0.5rem 0.65rem;
  font-size: 0.82rem;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #f59e0b;
  border-radius: 8px;
}}
.survey-overlay-warning[hidden] {{ display: none !important; }}
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
.return-candidate-status {{
  margin: 0;
  color: #92400e;
  font-weight: 600;
  flex-basis: 100%;
  width: 100%;
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
{subpage_header}
  <p class="lead" id="survey-count-lead" data-survey-candidate-total="{len(items)}">径間ごとに地図・現場指示・操作ボタンがあります。<span class="survey-visible-count-line">表示中 <strong id="survey-visible-count">{len(items)}</strong> 件</span><span class="survey-count-hint muted-tiny" id="survey-count-hint" hidden>（候補 {len(items)} 件・交渉待ち・返却候補は除く）</span></p>
  <p class="report-disclaimer">{survey_disclaimer}</p>
  <p id="survey-overlay-warning" class="survey-overlay-warning" hidden role="status"></p>
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
{two_map_click_handler_js()}
{render_survey_multipin_js()}
  // Portal status overlay (B-plan) or legacy pending request (A-plan). Never embed service_role.
{survey_portal_js}
}})();
  </script>
  <script>
{subpage_menu_js}
  </script>
</body>
</html>
"""
    return finalize_survey_map_html(html_body)


def build_negotiation_html(
    items: list[SurveyPublicItem],
    empty_note: str,
    promoted_candidates: list[SurveyPublicItem] | None = None,
    return_wait_items: list[SurveyPublicItem] | None = None,
    return_wait_smoke: ReturnWaitSmoke | None = None,
    portal_status_endpoint: str = PORTAL_CASE_STATUS_ENDPOINT,
    status_request_api_key: str = "",
    immediate_status: bool | None = None,
    repo_root: Path | None = None,
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
        # 交渉待ちページは地図UI不要。地図/2点地図ボタンは出さない。
        two_json = ""
        two_wrap = ""
        actions = ""
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
</article>"""
        )
    items_html = "\n".join(cards)
    if not items_html:
        items_html = f'<p class="muted-tiny">{escape_html(empty_note)}</p>'
    map_block = ""
    candidates_json = serialize_promoted_candidates(promoted_candidates or [])
    negotiation_portal_js = ""
    if use_immediate:
        negotiation_portal_js = render_negotiation_immediate_status_js(
            portal_status_endpoint,
            status_request_api_key,
            candidates_json,
        )
    subpage_header = render_portal_subpage_header("交渉待ち一覧", page="negotiation")
    subpage_menu_css = render_portal_subpage_menu_css()
    subpage_menu_js = render_portal_subpage_menu_js()
    if return_wait_smoke is None:
        return_wait_smoke = ReturnWaitSmoke(
            db_return_wait_count=0,
            displayed_return_wait_count=0,
            overlay_return_candidate_count=0,
            duplicate_management_no_count=0,
            warnings_count=0,
            db_return_wait_management_no_keys=[],
            displayed_management_no_keys=[],
        )
    return_wait_section = render_negotiation_return_wait_section(
        return_wait_items or [],
        return_wait_smoke,
        use_immediate=use_immediate,
    )
    return_candidate_section = ""
    return_candidate_css = render_negotiation_return_candidate_css()
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
{subpage_menu_css}
{return_candidate_css}
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
{two_map_tooltip_css()}
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
</style>
</head>
<body>
{subpage_header}
  <p class="lead">現調済み・対応中の案件です。地主交渉に進む案件を確認します。（表示 {len(items)} 件）</p>
  <p class="report-disclaimer">{negotiation_disclaimer}</p>
  <main>
{items_html}
{return_wait_section}
{map_block}
  </main>
  <p class="footer-note">このページは <code>scripts/generate_portal.py</code> で再生成できます。</p>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
    crossorigin=""></script>
  <script>
(function () {{
  // Portal status overlay (B-plan immediate). Never embed service_role.
{negotiation_portal_js}
}})();
  </script>
  <script>
{subpage_menu_js}
  </script>
</body>
</html>
"""


def build_archive_detail_html(
    entry: ManifestEntry,
    public_items: list[ArchivePublicItem] | None,
    detail_note: str,
    planned_incomplete: list[PlannedIncompleteItem] | None = None,
) -> str:
    """アーカイブ詳細（公開可能項目のみ）。通常共有ページの構成へ合わせる。"""
    folder = entry.date
    date_jp = fallback_heading(folder)
    title_disp = entry.title.strip() if entry.title else date_jp
    items_html = ""
    points: list[dict] = []
    planned_items = planned_incomplete or []
    completed_heading = ""
    if planned_items:
        completed_heading = (
            '<h2 class="archive-section-heading">完了報告（Supabase 正本）</h2>\n'
        )
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
                two_geo = build_two_geo_payload(
                    a_name=it.label,
                    a_lat=start_lat,
                    a_lng=start_lng,
                    b_name=it.label,
                    b_lat=end_lat,
                    b_lng=end_lng,
                    gps_poles=None,
                )
                two_json = format_two_geo_script(two_json_id, two_geo)
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
    planned_html = build_planned_incomplete_section_html(planned_items)
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
.archive-section-heading {{
  font-size: 1.05rem;
  margin: 1rem 0 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border);
}}
.planned-incomplete-section .archive-section-heading {{
  border-top: none;
  padding-top: 0;
  margin-top: 1.25rem;
}}
.card-planned-incomplete {{
  border-color: #e8c4a0;
}}
.archive-planned-count {{
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 600;
  margin-top: 0.15rem;
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
{two_map_tooltip_css()}
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
{completed_heading}{items_html}
{planned_html}
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
{two_map_click_handler_js()}

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
        planned_items = load_archive_planned_incomplete(repo_root, ent.date)
        if pub_items is None and _STRICT_COMPLETION_REPORTS_MISSING:
            print(
                f"Error: completion_reports JSON missing for {ent.date} under "
                f"{_completion_reports_root(repo_root)}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        n_items = len(pub_items) if pub_items else 0
        cr_root = _completion_reports_root(repo_root)
        n_planned = len(planned_items)
        print(
            f"archive detail {ent.date}: items={n_items}, "
            f"planned_but_incomplete={n_planned}, "
            f"completion_reports_root={cr_root} "
            f"(source={_completion_reports_root_source_label()})"
            + (f"; note={note}" if note else "")
        )
        _check_archive_items_vs_export_summary(
            repo_root,
            ent.date,
            n_items,
            strict_mismatch=_STRICT_COMPLETION_REPORTS_SUMMARY_MISMATCH,
        )
        out_path.write_text(
            build_archive_detail_html(ent, pub_items, note, planned_items),
            encoding="utf-8",
            newline="\n",
        )
        written.append(out_path)
    return written


def build_html(
    entries: list[tuple[str, str]],
    *,
    calendar_api_key: str = "",
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
    today_schedule_js = build_portal_today_schedule_js(calendar_api_key)
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
{PORTAL_TOP_TODAY_SCHEDULE_CSS}
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
          <a class="portal-menu-item" role="menuitem" href="./calendar/">社内カレンダー</a>
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

  <section class="today-schedule" aria-labelledby="today-schedule-heading">
    <h2 class="today-schedule-heading" id="today-schedule-heading">本日の予定</h2>
    <p class="today-schedule-note">社内カレンダーの本日分を簡易表示</p>
    <div id="today-schedule-root"></div>
    <p class="today-schedule-more"><a href="./calendar/">社内カレンダーで詳細を見る</a></p>
  </section>

  <div class="card-list" role="list">
{cards_str}
  </div>

  <p class="footer-note">このページは <code>scripts/generate_portal.py</code> で再生成できます。</p>
  <script>
{today_schedule_js}

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
PORTAL_MODE_SURVEY_ONLY = "survey-only"
PORTAL_MODE_ARCHIVE_ONLY = "archive-only"
PORTAL_MODE_PORTAL_TOP_ONLY = "portal-top-only"
PORTAL_MODE_NEGOTIATION_ONLY = "negotiation-only"

# Legacy share pages that should remain accessible by direct URL,
# but no longer appear on portal top cards.
RETIRED_SHARE_DATE_KEYS = frozenset({"261231"})

FOCUSED_PORTAL_MODES = frozenset(
    {
        PORTAL_MODE_SURVEY_ONLY,
        PORTAL_MODE_ARCHIVE_ONLY,
        PORTAL_MODE_PORTAL_TOP_ONLY,
        PORTAL_MODE_NEGOTIATION_ONLY,
    }
)

PORTAL_GUARD_REL_PATHS: tuple[str, ...] = (
    "portal/index.html",
    "portal/survey/index.html",
    "portal/archive/index.html",
    "portal/negotiation/index.html",
)

MODE_ALLOWED_PORTAL_OUTPUTS: dict[str, frozenset[str]] = {
    PORTAL_MODE_SURVEY_ONLY: frozenset({"portal/survey/index.html"}),
    PORTAL_MODE_ARCHIVE_ONLY: frozenset({"portal/archive/index.html"}),
    PORTAL_MODE_PORTAL_TOP_ONLY: frozenset({"portal/index.html"}),
    PORTAL_MODE_NEGOTIATION_ONLY: frozenset({"portal/negotiation/index.html"}),
}


@dataclass
class FocusedGenerateResult:
    mode: str
    output_rel: str
    stats: dict[str, Any]
    apikey_nonempty: bool


def _portal_data_root_display(repo_root: Path) -> str:
    return str(_portal_data_root_default(repo_root))


def _portal_data_root_default(repo_root: Path) -> Path:
    if _DATA_ROOT_OVERRIDE is not None:
        return _DATA_ROOT_OVERRIDE
    return (repo_root.parent / "ippatsu-pc" / "data").resolve()


def _load_env_file_minimal(path: Path) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[7:].strip()
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key not in os.environ:
            os.environ[key] = val
    return True


def load_portal_dotenv(repo_root: Path) -> list[str]:
    """share-pages / ippatsu-pc の .env を読む（既存の環境変数は上書きしない）。"""
    loaded: list[str] = []
    candidates = [
        repo_root / ".env",
        repo_root.parent / "ippatsu-pc" / ".env",
    ]
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]

        for path in candidates:
            if path.is_file():
                load_dotenv(path, override=False)
                loaded.append(str(path.resolve()))
    except ImportError:
        for path in candidates:
            if _load_env_file_minimal(path):
                loaded.append(str(path.resolve()))
    return loaded


def _snapshot_portal_guard_files(repo_root: Path) -> dict[str, bytes | None]:
    snap: dict[str, bytes | None] = {}
    for rel in PORTAL_GUARD_REL_PATHS:
        p = repo_root / rel
        snap[rel] = p.read_bytes() if p.is_file() else None
    return snap


def _portal_guard_violations(
    repo_root: Path,
    before: dict[str, bytes | None],
    allowed: frozenset[str],
) -> list[str]:
    violations: list[str] = []
    for rel in PORTAL_GUARD_REL_PATHS:
        p = repo_root / rel
        after = p.read_bytes() if p.is_file() else None
        if before.get(rel) != after and rel not in allowed:
            violations.append(rel)
    return violations


def _iter_share_index_rows(repo_root: Path) -> list[tuple[str, Path]]:
    share_dir = repo_root / "share"
    if not share_dir.is_dir():
        return []
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
    return rows


def _build_portal_top_entries(
    repo_root: Path,
    *,
    exclude_folder: str | None = None,
) -> list[tuple[str, str]]:
    manifest_entries = load_archive_manifest_entries(repo_root)
    archived = {e.date for e in manifest_entries}
    entries: list[tuple[str, str]] = []
    for folder, path in _iter_share_index_rows(repo_root):
        if folder in RETIRED_SHARE_DATE_KEYS:
            continue
        if folder in archived:
            continue
        if exclude_folder is not None and folder == exclude_folder:
            continue
        html_text = path.read_text(encoding="utf-8", errors="replace")
        date_line = card_heading(folder, path)
        summary = summarize_share_html(html_text, folder)
        heading = build_portal_heading(date_line, summary)
        entries.append((folder, heading))
    return entries


def _build_archive_index_parts(
    repo_root: Path,
) -> tuple[
    list[tuple[ManifestEntry, ShareSummary | None, list[ArchivePublicItem] | None]],
    list,
    list[ManifestEntry],
    dict[str, int],
]:
    manifest_entries = load_archive_manifest_entries(repo_root)
    share_by_folder = {f: p for f, p in _iter_share_index_rows(repo_root)}
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
    stats = {
        "manifest": len(manifest_entries),
        "archive_rows": len(archive_parts),
        "recent": len(recent_parts),
        "months": len(sections),
    }
    return recent_parts, sections, manifest_entries, stats


def _write_portal_html(repo_root: Path, rel: str, html: str) -> Path:
    out_path = repo_root / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8", newline="\n")
    return out_path


def run_survey_only(repo_root: Path) -> FocusedGenerateResult:
    survey_items, survey_empty_note, survey_stats = load_survey_public_items(repo_root)
    portal_api_key = survey_status_request_api_key(repo_root)
    if not portal_api_key:
        print(
            "warning: survey portal apikey not set; "
            "set PORTAL_SURVEY_REQUEST_API_KEY or SUPABASE_ANON_KEY "
            "when generating (送信ボタンは無効化されます).",
            file=sys.stderr,
        )
    overlay_neg_keys = fetch_portal_negotiation_wait_keys(
        PORTAL_CASE_STATUS_ENDPOINT, portal_api_key
    )
    survey_html = build_survey_html(
        survey_items,
        survey_empty_note,
        date.today().isoformat(),
        status_request_api_key=portal_api_key,
        portal_status_endpoint=PORTAL_CASE_STATUS_ENDPOINT,
        initial_hidden_overlay_keys=overlay_neg_keys,
        repo_root=repo_root,
    )
    rel = "portal/survey/index.html"
    out_path = _write_portal_html(repo_root, rel, survey_html)
    stats = dict(survey_stats)
    stats["survey_items"] = len(survey_items)
    print(
        f"Wrote {out_path} (survey_items={len(survey_items)}, "
        f"survey_items_total={survey_stats['total']}, "
        f"visible={survey_stats['visible']}, "
        f"filtered={survey_stats['filtered']})"
    )
    if survey_stats.get("exclude_reasons"):
        print(f"  survey_exclude_reasons: {survey_stats['exclude_reasons']}")
    coord_warnings = _drain_map_coord_warnings()
    if coord_warnings:
        print(f"  map_coord_warnings: {coord_warnings}")
    stats["map_coord_warnings"] = coord_warnings
    return FocusedGenerateResult(
        mode=PORTAL_MODE_SURVEY_ONLY,
        output_rel=rel,
        stats=stats,
        apikey_nonempty=bool(portal_api_key),
    )


def run_archive_only(repo_root: Path) -> FocusedGenerateResult:
    recent_parts, sections, manifest_entries, arch_stats = _build_archive_index_parts(
        repo_root
    )
    arch_html = build_archive_html(recent_parts, sections)
    rel = "portal/archive/index.html"
    out_path = _write_portal_html(repo_root, rel, arch_html)
    print(
        f"Wrote {out_path} (manifest={arch_stats['manifest']}, "
        f"archive_rows={arch_stats['archive_rows']}, recent={arch_stats['recent']}, "
        f"months={arch_stats['months']})"
    )
    stats = dict(arch_stats)
    stats["manifest_entries"] = len(manifest_entries)
    return FocusedGenerateResult(
        mode=PORTAL_MODE_ARCHIVE_ONLY,
        output_rel=rel,
        stats=stats,
        apikey_nonempty=False,
    )


def run_portal_top_only(repo_root: Path) -> FocusedGenerateResult:
    entries = _build_portal_top_entries(repo_root)
    manifest_entries = load_archive_manifest_entries(repo_root)
    archived = len({e.date for e in manifest_entries})
    out_html = build_html(entries, calendar_api_key=portal_calendar_api_key(repo_root))
    rel = "portal/index.html"
    out_path = _write_portal_html(repo_root, rel, out_html)
    print(
        f"Wrote {out_path} ({len(entries)} cards, "
        f"{archived} date(s) hidden on top per manifest)"
    )
    stats = {"portal_cards": len(entries), "archived_dates_hidden": archived}
    cal_key = portal_calendar_api_key(repo_root)
    return FocusedGenerateResult(
        mode=PORTAL_MODE_PORTAL_TOP_ONLY,
        output_rel=rel,
        stats=stats,
        apikey_nonempty=bool(cal_key),
    )


def run_negotiation_only(repo_root: Path) -> FocusedGenerateResult:
    negotiation_items, negotiation_empty_note, negotiation_stats = (
        load_negotiation_public_items(repo_root)
    )
    portal_api_key = survey_status_request_api_key(repo_root)
    if not portal_api_key:
        print(
            "warning: negotiation portal apikey not set; "
            "set PORTAL_SURVEY_REQUEST_API_KEY or SUPABASE_ANON_KEY "
            "when generating.",
            file=sys.stderr,
        )
    survey_items, _, _ = load_survey_public_items(repo_root)
    return_wait_items, return_wait_smoke = load_return_wait_public_items(
        portal_status_endpoint=PORTAL_CASE_STATUS_ENDPOINT,
        portal_api_key=portal_api_key,
    )
    negotiation_html = build_negotiation_html(
        negotiation_items,
        negotiation_empty_note,
        promoted_candidates=survey_items,
        return_wait_items=return_wait_items,
        return_wait_smoke=return_wait_smoke,
        status_request_api_key=portal_api_key,
        portal_status_endpoint=PORTAL_CASE_STATUS_ENDPOINT,
        repo_root=repo_root,
    )
    rel = "portal/negotiation/index.html"
    out_path = _write_portal_html(repo_root, rel, negotiation_html)
    print(
        f"Wrote {out_path} (negotiation_items={len(negotiation_items)}, "
        f"negotiation_items_total={negotiation_stats['total']}, "
        f"visible={negotiation_stats['visible']}, "
        f"filtered={negotiation_stats['filtered']}, "
        f"db_return_wait={return_wait_smoke.db_return_wait_count}, "
        f"displayed_return_wait={return_wait_smoke.displayed_return_wait_count}, "
        f"overlay_return_candidate={return_wait_smoke.overlay_return_candidate_count}, "
        f"dup={return_wait_smoke.duplicate_management_no_count}, "
        f"warn={return_wait_smoke.warnings_count})"
    )
    stats = dict(negotiation_stats)
    stats["negotiation_items"] = len(negotiation_items)
    stats["db_return_wait_count"] = return_wait_smoke.db_return_wait_count
    stats["displayed_return_wait_count"] = return_wait_smoke.displayed_return_wait_count
    stats["overlay_return_candidate_count"] = (
        return_wait_smoke.overlay_return_candidate_count
    )
    stats["duplicate_management_no_count"] = (
        return_wait_smoke.duplicate_management_no_count
    )
    stats["warnings_count"] = return_wait_smoke.warnings_count
    stats["db_return_wait_management_no_keys"] = (
        return_wait_smoke.db_return_wait_management_no_keys
    )
    stats["displayed_management_no_keys"] = (
        return_wait_smoke.displayed_management_no_keys
    )
    coord_warnings = _drain_map_coord_warnings()
    if coord_warnings:
        print(f"  map_coord_warnings: {coord_warnings}")
    stats["map_coord_warnings"] = coord_warnings
    return FocusedGenerateResult(
        mode=PORTAL_MODE_NEGOTIATION_ONLY,
        output_rel=rel,
        stats=stats,
        apikey_nonempty=bool(portal_api_key),
    )


def _require_html_substrings(html: str, checks: list[tuple[str, str]]) -> list[str]:
    failures: list[str] = []
    for label, needle in checks:
        if needle not in html:
            failures.append(label)
    return failures


def _validate_two_geo_script(html: str, script_id: str = "two-geo-0") -> list[str]:
    failures: list[str] = []
    m = re.search(rf'id="{re.escape(script_id)}">([^<]+)<', html)
    if not m:
        failures.append(f"{script_id} script block missing")
        return failures
    raw = m.group(1)
    if "&quot;" in raw:
        failures.append(f"{script_id} contains HTML-escaped quotes")
    try:
        geo = json.loads(raw)
    except json.JSONDecodeError:
        failures.append(f"{script_id} json.loads failed")
        return failures
    if not isinstance(geo.get("nearby"), list):
        failures.append(f"{script_id} missing nearby array")
    return failures


_SURVEY_CARD_RE = re.compile(
    r'<article class="card survey-update-card"[^>]*data-management-no-key="([^"]+)"',
)
_EXPECTED_SURVEY_WAIT_COUNT = 19
_EXPECTED_SURVEY_MULTIPIN_COUNT = 19
_EXPECTED_NEGOTIATION_WAIT_COUNT = 30
_EXPECTED_RETURN_WAIT_COUNT = 3
_SURVEY_NEGOTIATION_KEY = "51403794"
_SURVEY_GPS_SUPPLEMENT_KEY = "51410418"


def _count_survey_multipin_markers(html: str) -> int:
    return len(_SURVEY_ARTICLE_MULTIPIN_RE.findall(html))


def _survey_card_has_multipin(html: str, management_no_key: str) -> bool:
    pat = (
        rf'<article[^>]*data-management-no-key="{re.escape(management_no_key)}"'
        rf'[^>]*data-multipin-lat="'
    )
    return bool(re.search(pat, html))


def _parse_survey_candidate_total(html: str) -> int | None:
    m = re.search(r'data-survey-candidate-total="(\d+)"', html)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _count_survey_cards(html: str) -> int:
    return len(_SURVEY_CARD_RE.findall(html))


def _count_negotiation_wait_cards(html: str) -> int:
    return len(
        re.findall(
            r'<article class="card negotiation-card" data-card-index=',
            html,
        )
    )


def _count_return_wait_cards(html: str) -> int:
    return len(
        re.findall(
            r'<article class="card negotiation-card return-wait-card"',
            html,
        )
    )


def validate_survey_only_output(
    repo_root: Path, *, apikey_nonempty: bool
) -> list[str]:
    path = repo_root / "portal" / "survey" / "index.html"
    if not path.is_file():
        return ["portal/survey/index.html missing"]
    html = path.read_text(encoding="utf-8", errors="replace")
    failures = _require_html_substrings(
        html,
        [
            ("現調済みにする", "現調済みにする"),
            ("返却候補にする", "返却候補にする"),
            ("survey-overlay-warning", "survey-overlay-warning"),
            ("fetchReturnCandidates", "fetchReturnCandidates"),
            ("portal-menu-btn", "portal-menu-btn"),
            ("two-geo-0", 'id="two-geo-0"'),
            ("applySurveyMultipinState", "function applySurveyMultipinState"),
            ("collectVisibleSurveyMultipinPoints", "collectVisibleSurveyMultipinPoints"),
            ("updateSurveyVisibleCount", "function updateSurveyVisibleCount"),
            ("survey-visible-count", 'id="survey-visible-count"'),
            ("survey-count-lead", 'id="survey-count-lead"'),
            ("share-map", 'id="share-map"'),
            (_SURVEY_GPS_SUPPLEMENT_KEY, _SURVEY_GPS_SUPPLEMENT_KEY),
        ],
    )
    failures.extend(_validate_two_geo_script(html, "two-geo-0"))

    total = _parse_survey_candidate_total(html)
    if total != _EXPECTED_SURVEY_WAIT_COUNT:
        failures.append(
            f"survey_wait_count expected {_EXPECTED_SURVEY_WAIT_COUNT} got {total}"
        )
    card_count = _count_survey_cards(html)
    if card_count != _EXPECTED_SURVEY_WAIT_COUNT:
        failures.append(
            f"survey_card_count expected {_EXPECTED_SURVEY_WAIT_COUNT} got {card_count}"
        )
    multipin_count = _count_survey_multipin_markers(html)
    if multipin_count != _EXPECTED_SURVEY_MULTIPIN_COUNT:
        failures.append(
            f"survey_multipin_count expected {_EXPECTED_SURVEY_MULTIPIN_COUNT} "
            f"got {multipin_count}"
        )
    if not _survey_card_has_multipin(html, _SURVEY_GPS_SUPPLEMENT_KEY):
        failures.append(f"survey_multipin missing for {_SURVEY_GPS_SUPPLEMENT_KEY}")
    if re.search(rf'data-management-no-key="{_SURVEY_NEGOTIATION_KEY}"', html):
        failures.append(
            f"survey must not list negotiation_wait key {_SURVEY_NEGOTIATION_KEY}"
        )

    multipin_violations = find_survey_html_multipin_violations(html)
    if multipin_violations:
        failures.append(
            "survey multipin out_of_jp_bounds: "
            + ", ".join(
                f"{v.get('management_no_key')}@{v.get('html_line')}"
                for v in multipin_violations[:5]
            )
        )
    if not apikey_nonempty:
        failures.append("survey apikey empty")
    return failures


def validate_archive_only_output(repo_root: Path) -> list[str]:
    path = repo_root / "portal" / "archive" / "index.html"
    if not path.is_file():
        return ["portal/archive/index.html missing"]
    html = path.read_text(encoding="utf-8", errors="replace")
    return _require_html_substrings(
        html,
        [
            ("portal-menu-btn", "portal-menu-btn"),
            ("ポータルTOP", 'href="../"'),
            ("現調待ち", 'href="../survey/"'),
            ("交渉待ち", 'href="../negotiation/"'),
            ("社内カレンダー", 'href="../calendar/"'),
            ("アーカイブ current", 'aria-current="page"'),
        ],
    )


def validate_portal_top_only_output(repo_root: Path) -> list[str]:
    path = repo_root / "portal" / "index.html"
    if not path.is_file():
        return ["portal/index.html missing"]
    html = path.read_text(encoding="utf-8", errors="replace")
    return _require_html_substrings(
        html,
        [
            ("today-schedule", "today-schedule"),
            ("loadTodaySchedule", "function loadTodaySchedule"),
            ("company-calendar-events", "company-calendar-events"),
            ("calendar link", 'href="./calendar/"'),
            ("portal-menu-btn", "portal-menu-btn"),
        ],
    )


def validate_negotiation_only_output(repo_root: Path) -> list[str]:
    path = repo_root / "portal" / "negotiation" / "index.html"
    if not path.is_file():
        return ["portal/negotiation/index.html missing"]
    html = path.read_text(encoding="utf-8", errors="replace")
    failures = _require_html_substrings(
        html,
        [
            ("portal-menu-btn", "portal-menu-btn"),
            ("return-candidate-section", "return-candidate-section"),
            ("返却待ち（正本）", "返却待ち（正本）"),
            ("fetchReturnCandidates", "fetchReturnCandidates"),
            ("negotiation-card", "negotiation-card"),
            ("data-negotiation-revert", "data-negotiation-revert"),
            ("現調待ちに戻す", "現調待ちに戻す"),
            (_SURVEY_NEGOTIATION_KEY, _SURVEY_NEGOTIATION_KEY),
        ],
    )
    neg_count = _count_negotiation_wait_cards(html)
    if neg_count != _EXPECTED_NEGOTIATION_WAIT_COUNT:
        failures.append(
            f"negotiation_wait_count expected {_EXPECTED_NEGOTIATION_WAIT_COUNT} "
            f"got {neg_count}"
        )
    ret_count = _count_return_wait_cards(html)
    if ret_count != _EXPECTED_RETURN_WAIT_COUNT:
        failures.append(
            f"return_wait_count expected {_EXPECTED_RETURN_WAIT_COUNT} got {ret_count}"
        )
    if "地図を表示" in html:
        failures.append("negotiation must not contain 地図を表示")
    if "2点地図を表示" in html:
        failures.append("negotiation must not contain 2点地図を表示")
    if 'id="share-map"' in html:
        failures.append('negotiation must not contain id="share-map"')
    return failures


def validate_focused_mode(
    mode: str, repo_root: Path, result: FocusedGenerateResult
) -> list[str]:
    if mode == PORTAL_MODE_SURVEY_ONLY:
        return validate_survey_only_output(
            repo_root, apikey_nonempty=result.apikey_nonempty
        )
    if mode == PORTAL_MODE_ARCHIVE_ONLY:
        return validate_archive_only_output(repo_root)
    if mode == PORTAL_MODE_PORTAL_TOP_ONLY:
        return validate_portal_top_only_output(repo_root)
    if mode == PORTAL_MODE_NEGOTIATION_ONLY:
        return validate_negotiation_only_output(repo_root)
    return [f"unknown focused mode: {mode}"]


def _print_focused_cli_summary(
    result: FocusedGenerateResult,
    *,
    data_root: str,
    env_loaded: list[str],
    validation_ok: bool,
    validation_failures: list[str],
) -> None:
    print(f"mode: {result.mode}")
    print(f"data_root: {data_root}")
    if env_loaded:
        print(f"env_loaded: {len(env_loaded)} file(s)")
    print(f"changed_target: {result.output_rel}")
    print(f"output file: {result.output_rel}")
    if "visible" in result.stats:
        print(f"visible: {result.stats['visible']}")
    if "portal_cards" in result.stats:
        print(f"portal_cards: {result.stats['portal_cards']}")
    if "negotiation_items" in result.stats:
        print(f"negotiation_items: {result.stats['negotiation_items']}")
    if "manifest" in result.stats:
        print(f"manifest_entries: {result.stats['manifest']}")
    print(f"apikey_nonempty: {str(result.apikey_nonempty).lower()}")
    if validation_ok:
        print("validation: OK")
    else:
        print("validation: NG")
        for item in validation_failures:
            print(f"  - {item}")


def run_focused_portal_mode(mode: str, repo_root: Path) -> int:
    env_loaded = load_portal_dotenv(repo_root)
    allowed = MODE_ALLOWED_PORTAL_OUTPUTS[mode]
    before = _snapshot_portal_guard_files(repo_root)
    runners = {
        PORTAL_MODE_SURVEY_ONLY: run_survey_only,
        PORTAL_MODE_ARCHIVE_ONLY: run_archive_only,
        PORTAL_MODE_PORTAL_TOP_ONLY: run_portal_top_only,
        PORTAL_MODE_NEGOTIATION_ONLY: run_negotiation_only,
    }
    result = runners[mode](repo_root)
    guard_hits = _portal_guard_violations(repo_root, before, allowed)
    if guard_hits:
        print(
            "Error: portal file guard detected unexpected changes: "
            + ", ".join(guard_hits),
            file=sys.stderr,
        )
        return 1
    failures = validate_focused_mode(mode, repo_root, result)
    validation_ok = not failures
    _print_focused_cli_summary(
        result,
        data_root=_portal_data_root_display(repo_root),
        env_loaded=env_loaded,
        validation_ok=validation_ok,
        validation_failures=failures,
    )
    return 0 if validation_ok else 1


def _parse_six_digit_date(value: str) -> str | None:
    """6桁日付キーを正規化。不正なら None。"""
    d = (value or "").strip()
    if len(d) == 6 and d.isdigit():
        return d
    return None


def _configure_stdio_encoding() -> None:
    """Windows cp932 コンソールで診断 print が落ちないよう stdout/stderr を緩和する。

    HTML 書き込みは常に UTF-8。本関数は末尾ログ用のみ。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, OSError, ValueError):
                pass


def main() -> int:
    global _DATA_ROOT_OVERRIDE
    global _COMPLETION_REPORTS_ROOT_OVERRIDE
    global _STRICT_COMPLETION_REPORTS_ROOT
    global _STRICT_COMPLETION_REPORTS_MISSING
    global _STRICT_COMPLETION_REPORTS_SUMMARY_MISMATCH

    _configure_stdio_encoding()

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
            "Path to the ippatsu-pc 'data' directory (survey/ etc.). "
            "Default: <parent of this repo>/ippatsu-pc/data. "
            "Archive completion_reports use --completion-reports-root when set."
        ),
    )
    parser.add_argument(
        "--completion-reports-root",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Directory containing completion report secondary JSON files "
            "(YYMMDD.json), e.g. ippatsu-pc output/completion_reports_export. "
            "Preferred for portal archive generation before publish. "
            "Do not copy into data/completion_reports before portal publish."
        ),
    )
    parser.add_argument(
        "--strict-completion-reports-root",
        action="store_true",
        help=(
            "Require --completion-reports-root (exit if unset). "
            "Use for Supabase SOT / pre-publish runs."
        ),
    )
    parser.add_argument(
        "--strict-completion-reports-missing",
        action="store_true",
        help=(
            "Exit if a manifest archive date has no JSON under completion_reports_root."
        ),
    )
    parser.add_argument(
        "--strict-completion-reports-summary",
        action="store_true",
        help=(
            "Exit if loaded item count disagrees with export_summary.json for that date."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=(
            PORTAL_MODE_FULL,
            PORTAL_MODE_COMPLETION_ARCHIVE,
            PORTAL_MODE_SHARE_UPDATE,
            PORTAL_MODE_SURVEY_ONLY,
            PORTAL_MODE_ARCHIVE_ONLY,
            PORTAL_MODE_PORTAL_TOP_ONLY,
            PORTAL_MODE_NEGOTIATION_ONLY,
        ),
        default=PORTAL_MODE_FULL,
        help=(
            "full: full portal regen (default). "
            "completion-archive: minimal regen for completion report archive sync "
            "(requires --date). "
            "share-update: minimal regen for share-mode publish (requires --date). "
            "survey-only / archive-only / portal-top-only / negotiation-only: "
            "single HTML output with post-generate validation."
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
    _COMPLETION_REPORTS_ROOT_OVERRIDE = None
    _STRICT_COMPLETION_REPORTS_ROOT = bool(ns.strict_completion_reports_root)
    _STRICT_COMPLETION_REPORTS_MISSING = bool(ns.strict_completion_reports_missing)
    _STRICT_COMPLETION_REPORTS_SUMMARY_MISMATCH = bool(
        ns.strict_completion_reports_summary
    )
    if ns.data_root is not None:
        dr = ns.data_root.expanduser().resolve()
        if not dr.is_dir():
            print(f"Error: --data-root is not a directory: {dr}", file=sys.stderr)
            return 1
        _DATA_ROOT_OVERRIDE = dr
    if ns.completion_reports_root is not None:
        cr = ns.completion_reports_root.expanduser().resolve()
        if not cr.is_dir():
            print(
                f"Error: --completion-reports-root is not a directory: {cr}",
                file=sys.stderr,
            )
            return 1
        _COMPLETION_REPORTS_ROOT_OVERRIDE = cr

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
    load_portal_dotenv(repo_root)

    if _print_completion_reports_root_info(
        repo_root, strict_root=_STRICT_COMPLETION_REPORTS_ROOT
    ):
        return 1

    if mode in FOCUSED_PORTAL_MODES:
        if mode in (PORTAL_MODE_PORTAL_TOP_ONLY,):
            share_dir = repo_root / "share"
            if not share_dir.is_dir():
                print(f"Missing directory: {share_dir}", file=sys.stderr)
                return 1
        return run_focused_portal_mode(mode, repo_root)

    share_dir = repo_root / "share"
    if not share_dir.is_dir():
        print(f"Missing directory: {share_dir}", file=sys.stderr)
        return 1

    if mode == PORTAL_MODE_FULL:
        # ippatsu-pc からの HTML コピー直後でも、ポータル生成前に必ず注入する。
        inject_share_detail_edit_into_share_pages(repo_root)

    manifest_entries = load_archive_manifest_entries(repo_root)
    synced_dates = sync_archive_manifest_counts_from_completion_export(repo_root)
    if synced_dates:
        print(
            "synced archive_manifest.json counts from completion export: "
            + ", ".join(synced_dates)
        )
        manifest_entries = load_archive_manifest_entries(repo_root)
    archived = {e.date for e in manifest_entries}

    exclude_folder = (
        target_date if mode == PORTAL_MODE_COMPLETION_ARCHIVE else None
    )
    entries = _build_portal_top_entries(
        repo_root, exclude_folder=exclude_folder
    )

    out = build_html(entries, calendar_api_key=portal_calendar_api_key(repo_root))
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

    recent_parts, sections, _, arch_index_stats = _build_archive_index_parts(repo_root)
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
        f"Wrote {arch_path} (manifest={arch_index_stats['manifest']}, "
        f"archive_rows={arch_index_stats['archive_rows']}, "
        f"recent={arch_index_stats['recent']}, months={arch_index_stats['months']}, "
        f"archive_details={len(detail_paths)})"
    )
    if mode == PORTAL_MODE_FULL:
        survey_items, survey_empty_note, survey_stats = load_survey_public_items(
            repo_root
        )
        portal_api_key = survey_status_request_api_key(repo_root)
        if not portal_api_key:
            print(
                "warning: survey portal apikey not set; "
                "set PORTAL_SURVEY_REQUEST_API_KEY or SUPABASE_ANON_KEY "
                "when generating (送信ボタンは無効化されます).",
                file=sys.stderr,
            )
        overlay_neg_keys = fetch_portal_negotiation_wait_keys(
            PORTAL_CASE_STATUS_ENDPOINT, portal_api_key
        )
        survey_html = build_survey_html(
            survey_items,
            survey_empty_note,
            date.today().isoformat(),
            status_request_api_key=portal_api_key,
            portal_status_endpoint=PORTAL_CASE_STATUS_ENDPOINT,
            initial_hidden_overlay_keys=overlay_neg_keys,
            repo_root=repo_root,
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
        survey_coord_warnings = _drain_map_coord_warnings()
        if survey_coord_warnings:
            print(f"  survey_map_coord_warnings: {survey_coord_warnings}")
        # M11 + B-plan: 交渉待ちページ。即時 status overlay（apikey は publishable/anon のみ）。
        negotiation_items, negotiation_empty_note, negotiation_stats = (
            load_negotiation_public_items(repo_root)
        )
        return_wait_items, return_wait_smoke = load_return_wait_public_items(
            portal_status_endpoint=PORTAL_CASE_STATUS_ENDPOINT,
            portal_api_key=portal_api_key,
        )
        negotiation_html = build_negotiation_html(
            negotiation_items,
            negotiation_empty_note,
            promoted_candidates=survey_items,
            return_wait_items=return_wait_items,
            return_wait_smoke=return_wait_smoke,
            status_request_api_key=portal_api_key,
            portal_status_endpoint=PORTAL_CASE_STATUS_ENDPOINT,
            repo_root=repo_root,
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
            f"filtered={negotiation_stats['filtered']}, "
            f"db_return_wait={return_wait_smoke.db_return_wait_count}, "
            f"displayed_return_wait={return_wait_smoke.displayed_return_wait_count}, "
            f"overlay_return_candidate={return_wait_smoke.overlay_return_candidate_count}, "
            f"dup={return_wait_smoke.duplicate_management_no_count}, "
            f"warn={return_wait_smoke.warnings_count})"
        )
        negotiation_coord_warnings = _drain_map_coord_warnings()
        if negotiation_coord_warnings:
            print(f"  negotiation_map_coord_warnings: {negotiation_coord_warnings}")
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
