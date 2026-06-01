"""Client-side JS snippets for immediate portal status (B-plan draft).

Used by scripts/generate_portal.py. Keeps large JS blocks out of the main generator.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

# Same deployed function as A-plan until update-portal-case-status is deployed separately.
PORTAL_CASE_STATUS_ENDPOINT_DEFAULT = (
    "https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/submit-survey-status-request"
)


def portal_immediate_status_enabled() -> bool:
    """Default on for B-plan draft. Set PORTAL_IMMEDIATE_STATUS=0 to embed legacy A-plan JS."""
    raw = (os.environ.get("PORTAL_IMMEDIATE_STATUS") or "1").strip().lower()
    return raw not in {"0", "false", "no", "legacy"}


def fetch_portal_negotiation_wait_keys(endpoint: str, api_key: str) -> set[str]:
    """GET portal status overrides; return management_no_key set for negotiation_wait.

    Used at generate time to omit overlay-promoted cases from the static survey list.
    Never logs or prints api_key. On failure returns an empty set (non-fatal).
    """
    ep = (endpoint or "").strip()
    key = (api_key or "").strip()
    if not ep or not key:
        return set()
    req = urllib.request.Request(
        ep,
        method="GET",
        headers={"apikey": key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, TimeoutError):
        return set()
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return set()
    if not isinstance(data, dict) or not data.get("ok"):
        return set()
    overrides = data.get("overrides")
    if not isinstance(overrides, list):
        return set()
    out: set[str] = set()
    for row in overrides:
        if not isinstance(row, dict):
            continue
        if str(row.get("portal_status") or "").strip() != "negotiation_wait":
            continue
        k = str(row.get("management_no_key") or "").strip()
        if k:
            out.add(k)
    return out


def serialize_promoted_candidates(items: list[Any]) -> str:
    """Minimal survey items for negotiation-page dynamic promotion."""
    out: list[dict[str, str]] = []
    for it in items:
        out.append(
            {
                "management_no_key": str(getattr(it, "management_no_key", "") or ""),
                "management_no": str(getattr(it, "management_no", "") or ""),
                "label": str(getattr(it, "label", "") or ""),
                "note": str(getattr(it, "note", "") or ""),
            }
        )
    return json.dumps(out, ensure_ascii=False)


def render_survey_immediate_status_js(endpoint: str, api_key: str) -> str:
    ep = json.dumps(endpoint, ensure_ascii=False)
    key = json.dumps(api_key, ensure_ascii=False)
    return f"""
  var PORTAL_STATUS_ENDPOINT = {ep};
  var PORTAL_STATUS_API_KEY = {key};
  var PORTAL_STATUS_LS_PREFIX = "portal_case_status:";
  var SURVEY_MARK_CONFIRM =
    "この案件を「現調済み」として交渉待ちへ移動しますか？\\n\\n即時に交渉待ちページへ表示されます。誤操作は交渉待ちページの「現調待ちに戻す」で取り消せます。";
  var RETURN_CANDIDATE_MARK_CONFIRM = "この案件を返却候補にしますか？";
  function portalStatusLsKey(mgmtKey) {{
    return PORTAL_STATUS_LS_PREFIX + mgmtKey;
  }}
  function portalStatusMapFromResponse(data) {{
    var map = Object.create(null);
    if (!data || !Array.isArray(data.overrides)) return map;
    data.overrides.forEach(function(row) {{
      var k = String(row.management_no_key || "").trim();
      var st = String(row.portal_status || "").trim();
      if (k && st) map[k] = st;
    }});
    return map;
  }}
﻿function applySurveyOverlay(statusMap, serverOk, returnCandidateKeys) {{
    var returnMap = returnCandidateKeys || Object.create(null);
    document.querySelectorAll(".survey-update-card[data-management-no-key]").forEach(function(card) {{
      var key = (card.getAttribute("data-management-no-key") || "").trim();
      if (!key) return;
      var st = statusMap[key];
      if (serverOk) {{
        // サーバーが正常応答: サーバー結果を正とし、古いlocalStorageを清掃する
        if (st !== "negotiation_wait") {{
          try {{ localStorage.removeItem(portalStatusLsKey(key)); }} catch (e) {{}}
        }}
      }} else {{
        // サーバー到達不可: localStorageをフォールバックとして使用
        try {{
          if (localStorage.getItem(portalStatusLsKey(key)) === "negotiation_wait") {{
            st = "negotiation_wait";
          }}
        }} catch (e) {{}}
      }}
      if (st === "negotiation_wait" || returnMap[key]) {{
        card.hidden = true;
        card.setAttribute(
          "data-portal-moved",
          st === "negotiation_wait" ? "negotiation" : "return_candidate",
        );
      }} else {{
        card.hidden = false;
        card.removeAttribute("data-portal-moved");
      }}
    }});
  }}
  function mapPortalStatusError(httpStatus, body) {{
    var err = "";
    if (body && typeof body === "object") {{
      err = String(body.error || body.message || "");
    }}
    if (httpStatus === 401 || err === "invalid_api_key") {{
      return "送信に失敗しました（APIキーが無効です）";
    }}
    if (httpStatus === 503 || err === "server_not_configured") {{
      return "送信機能がサーバ側で未設定です";
    }}
    return "送信に失敗しました。通信状態を確認して再試行してください";
  }}
  function setSurveyMarkUi(card, btn, statusEl, state, message) {{
    statusEl.classList.remove("is-error");
    if (state === "sent") {{
      statusEl.hidden = false;
      statusEl.textContent = message || "交渉待ちへ移動済み";
      btn.disabled = true;
      btn.textContent = "移動済み";
      card.classList.add("survey-mark-sent");
      return;
    }}
    if (state === "sending") {{
      statusEl.hidden = false;
      statusEl.textContent = "送信中...";
      btn.disabled = true;
      btn.textContent = "送信中...";
      card.classList.remove("survey-mark-sent");
      return;
    }}
    if (state === "error") {{
      statusEl.hidden = false;
      statusEl.classList.add("is-error");
      statusEl.textContent = message || "送信に失敗しました";
      btn.disabled = false;
      btn.textContent = "現調済みにする";
      card.classList.remove("survey-mark-sent");
      return;
    }}
    statusEl.hidden = true;
    statusEl.textContent = "";
    btn.disabled = false;
    btn.textContent = "現調済みにする";
    card.classList.remove("survey-mark-sent");
  }}
  function mapReturnCandidateError(httpStatus, body) {{
    var err = "";
    if (body && typeof body === "object") {{
      err = String(body.error || body.message || "");
    }}
    if (httpStatus === 401 || err === "invalid_api_key") {{
      return "送信に失敗しました（APIキーが無効です）";
    }}
    if (httpStatus === 503 || err === "server_not_configured") {{
      return "送信機能がサーバ側で未設定です";
    }}
    if (httpStatus === 409 && err === "overlay_status_conflict") {{
      return "交渉待ちに移動済みのため返却候補にできません";
    }}
    return "送信に失敗しました。通信状態を確認して再試行してください";
  }}
  function setReturnCandidateUi(card, btn, statusEl, state, message) {{
    statusEl.classList.remove("is-error");
    if (state === "marked") {{
      statusEl.hidden = false;
      statusEl.textContent = message || "返却候補に設定済み";
      if (btn) {{
        btn.disabled = true;
        btn.textContent = "返却候補済み";
      }}
      card.classList.add("return-candidate-marked");
      return;
    }}
    if (state === "sending") {{
      statusEl.hidden = false;
      statusEl.textContent = "送信中...";
      if (btn) {{
        btn.disabled = true;
        btn.textContent = "送信中...";
      }}
      return;
    }}
    if (state === "error") {{
      statusEl.hidden = false;
      statusEl.classList.add("is-error");
      statusEl.textContent = message || "返却候補の設定に失敗しました";
      if (btn) {{
        btn.disabled = false;
        btn.textContent = "返却候補にする";
      }}
      card.classList.remove("return-candidate-marked");
      return;
    }}
    statusEl.hidden = true;
    statusEl.textContent = "";
    if (btn) {{
      btn.disabled = !PORTAL_STATUS_API_KEY;
      btn.textContent = "返却候補にする";
    }}
    card.classList.remove("return-candidate-marked");
  }}
  function fetchReturnCandidates() {{
    if (!PORTAL_STATUS_API_KEY) {{
      return Promise.resolve({{ ok: false, keys: Object.create(null), reason: "apikey_missing" }});
    }}
    return fetch(PORTAL_STATUS_ENDPOINT + "?list=return_candidates", {{
      method: "GET",
      headers: {{ apikey: PORTAL_STATUS_API_KEY }},
    }})
      .then(function(res) {{
        return res
          .json()
          .catch(function() {{ return {{}}; }})
          .then(function(data) {{ return {{ res: res, data: data }}; }});
      }})
      .then(function(r) {{
        var keys = Object.create(null);
        if (!r.res.ok || !r.data || !r.data.ok) {{
          return {{ ok: false, keys: keys, reason: "fetch_failed" }};
        }}
        var list = r.data.return_candidates;
        if (!Array.isArray(list)) return {{ ok: true, keys: keys }};
        list.forEach(function(it) {{
          var k = String(it.management_no_key || "").trim();
          if (k) keys[k] = true;
        }});
        return {{ ok: true, keys: keys }};
      }})
      .catch(function() {{ return {{ ok: false, keys: Object.create(null), reason: "network_error" }}; }});
  }}
  function refreshReturnCandidateCardState(keys) {{
    document.querySelectorAll(".survey-update-card[data-management-no-key]").forEach(function(card) {{
      var key = (card.getAttribute("data-management-no-key") || "").trim();
      var btn = card.querySelector("[data-return-candidate-mark]");
      var statusEl = card.querySelector("[data-return-candidate-status]");
      if (!key || !statusEl) return;
      if (keys[key]) {{
        setReturnCandidateUi(card, btn, statusEl, "marked");
      }} else {{
        setReturnCandidateUi(card, btn, statusEl, "idle");
      }}
    }});
  }}
  function fetchPortalOverrides() {{
    if (!PORTAL_STATUS_API_KEY) return Promise.resolve({{ ok: false, statusMap: Object.create(null) }});
    return fetch(PORTAL_STATUS_ENDPOINT, {{
      method: "GET",
      headers: {{ apikey: PORTAL_STATUS_API_KEY }},
    }})
      .then(function(res) {{
        return res.json().catch(function() {{ return {{}}; }});
      }})
      .then(function(data) {{
        if (!data || !data.ok) return {{ ok: false, statusMap: Object.create(null) }};
        return {{ ok: true, statusMap: portalStatusMapFromResponse(data) }};
      }})
      .catch(function() {{ return {{ ok: false, statusMap: Object.create(null) }}; }});
  }}
  document.querySelectorAll("[data-survey-mark-done]").forEach(function(btn) {{
    if (!PORTAL_STATUS_API_KEY) btn.disabled = true;
  }});
  var surveyOverlayWarningEl = document.getElementById("survey-overlay-warning");
  var cachedReturnCandidateKeys = Object.create(null);
  var cachedReturnCandidateFetchOk = true;
  var cachedStatusMap = Object.create(null);
  var cachedStatusFetchOk = false;
  function updateSurveyOverlayWarning() {{
    if (!surveyOverlayWarningEl) return;
    if (cachedReturnCandidateFetchOk) {{
      surveyOverlayWarningEl.hidden = true;
      surveyOverlayWarningEl.textContent = "";
      return;
    }}
    surveyOverlayWarningEl.hidden = false;
    surveyOverlayWarningEl.textContent =
      "返却候補情報の取得に失敗したため、一部案件が現調待ちに表示される可能性があります。";
  }}
  function syncSurveyCardVisibility() {{
    applySurveyOverlay(cachedStatusMap, cachedStatusFetchOk, cachedReturnCandidateKeys);
    if (typeof applySurveyMultipinState === "function") applySurveyMultipinState();
  }}
  syncSurveyCardVisibility();
  fetchPortalOverrides().then(function(result) {{
    cachedStatusMap = result.statusMap || Object.create(null);
    cachedStatusFetchOk = !!result.ok;
    syncSurveyCardVisibility();
  }});
  fetchReturnCandidates().then(function(result) {{
    cachedReturnCandidateKeys = result.keys || Object.create(null);
    cachedReturnCandidateFetchOk = !!result.ok;
    updateSurveyOverlayWarning();
    refreshReturnCandidateCardState(cachedReturnCandidateKeys);
    syncSurveyCardVisibility();
    if (!result.ok) {{
      console.warn("[portal/survey] failed to fetch return candidates");
    }}
  }});
  document.querySelectorAll(".survey-update-card[data-management-no-key]").forEach(function(card) {{
    var key = (card.getAttribute("data-management-no-key") || "").trim();
    var btn = card.querySelector("[data-survey-mark-done]");
    var statusEl = card.querySelector("[data-survey-mark-status]");
    var returnBtn = card.querySelector("[data-return-candidate-mark]");
    var returnStatusEl = card.querySelector("[data-return-candidate-status]");
    if (!key || !btn || !statusEl) return;
    if (!PORTAL_STATUS_API_KEY) {{
      setSurveyMarkUi(
        card,
        btn,
        statusEl,
        "error",
        "送信設定が未設定です（ポータル再生成時にキーが必要です）",
      );
    }}
    if (PORTAL_STATUS_API_KEY) {{
      btn.addEventListener("click", function() {{
        if (btn.disabled) return;
        if (!window.confirm(SURVEY_MARK_CONFIRM)) return;
        var payload = {{
          management_no_key: key,
          action: "mark_survey_done",
          source: "portal_survey",
          note: "",
        }};
        setSurveyMarkUi(card, btn, statusEl, "sending");
        fetch(PORTAL_STATUS_ENDPOINT, {{
          method: "POST",
          headers: {{
            "Content-Type": "application/json",
            apikey: PORTAL_STATUS_API_KEY,
          }},
          body: JSON.stringify(payload),
        }})
          .then(function(res) {{
            return res
              .json()
              .catch(function() {{ return {{}}; }})
              .then(function(data) {{ return {{ res: res, data: data }}; }});
          }})
          .then(function(r) {{
            if (r.res.ok && r.data && r.data.ok) {{
              try {{
                localStorage.setItem(portalStatusLsKey(key), "negotiation_wait");
              }} catch (e2) {{}}
              card.hidden = true;
              card.setAttribute("data-portal-moved", "negotiation");
              setSurveyMarkUi(card, btn, statusEl, "sent", "交渉待ちへ移動済み（この一覧から非表示）");
              return;
            }}
            setSurveyMarkUi(
              card,
              btn,
              statusEl,
              "error",
              mapPortalStatusError(r.res.status, r.data),
            );
          }})
          .catch(function() {{
            setSurveyMarkUi(
              card,
              btn,
              statusEl,
              "error",
              "送信に失敗しました。通信状態を確認して再試行してください",
            );
          }});
      }});
    }}
    if (returnBtn && returnStatusEl) {{
      if (!PORTAL_STATUS_API_KEY) returnBtn.disabled = true;
      returnBtn.addEventListener("click", function() {{
        if (returnBtn.disabled) return;
        if (!window.confirm(RETURN_CANDIDATE_MARK_CONFIRM)) return;
        setReturnCandidateUi(card, returnBtn, returnStatusEl, "sending");
        fetch(PORTAL_STATUS_ENDPOINT, {{
          method: "POST",
          headers: {{
            "Content-Type": "application/json",
            apikey: PORTAL_STATUS_API_KEY,
          }},
          body: JSON.stringify({{
            management_no_key: key,
            management_no: (card.getAttribute("data-management-no") || "").trim(),
            label: (card.getAttribute("data-label") || "").trim(),
            action: "mark_return_candidate",
            source: "portal_survey",
          }}),
        }})
          .then(function(res) {{
            return res
              .json()
              .catch(function() {{ return {{}}; }})
              .then(function(data) {{ return {{ res: res, data: data }}; }});
          }})
          .then(function(r) {{
            if (r.res.ok && r.data && r.data.ok) {{
              cachedReturnCandidateKeys[key] = true;
              setReturnCandidateUi(
                card,
                returnBtn,
                returnStatusEl,
                "marked",
                "返却候補に設定済み（交渉待ちページの返却リストに表示）",
              );
              card.hidden = true;
              card.setAttribute("data-portal-moved", "return_candidate");
              syncSurveyCardVisibility();
              return;
            }}
            setReturnCandidateUi(
              card,
              returnBtn,
              returnStatusEl,
              "error",
              mapReturnCandidateError(r.res.status, r.data),
            );
          }})
          .catch(function() {{
            setReturnCandidateUi(
              card,
              returnBtn,
              returnStatusEl,
              "error",
              "送信に失敗しました。通信状態を確認して再試行してください",
            );
          }});
      }});
    }}
  }});

"""

def render_survey_legacy_request_js(endpoint: str, api_key: str) -> str:
    ep = json.dumps(endpoint, ensure_ascii=False)
    key = json.dumps(api_key, ensure_ascii=False)
    return f"""
  var SURVEY_STATUS_REQUEST_ENDPOINT = {ep};
  var SURVEY_STATUS_REQUEST_API_KEY = {key};
  var SURVEY_SENT_LS_PREFIX = "survey_update_request_sent:";
  var SURVEY_MARK_CONFIRM =
    "この案件を「現調済み」として送信しますか？送信後、PC側で確認・反映されます。";
  function surveySentLsKey(mgmtKey, action) {{
    return SURVEY_SENT_LS_PREFIX + mgmtKey + ":" + action;
  }}
  function newRequestId() {{
    if (typeof crypto !== "undefined" && crypto.randomUUID) {{
      return crypto.randomUUID();
    }}
    return String(Date.now()) + "-" + Math.random().toString(16).slice(2);
  }}
  function setSurveyMarkUi(card, btn, statusEl, state, message) {{
    statusEl.classList.remove("is-error");
    if (state === "sent" || state === "duplicate") {{
      statusEl.hidden = false;
      statusEl.textContent = message || "送信済み（PC反映待ち）";
      btn.disabled = true;
      btn.textContent = "送信済み";
      card.classList.add("survey-mark-sent");
      return;
    }}
    if (state === "sending") {{
      statusEl.hidden = false;
      statusEl.textContent = "送信中...";
      btn.disabled = true;
      btn.textContent = "送信中...";
      card.classList.remove("survey-mark-sent");
      return;
    }}
    if (state === "error") {{
      statusEl.hidden = false;
      statusEl.classList.add("is-error");
      statusEl.textContent = message || "送信に失敗しました";
      btn.disabled = false;
      btn.textContent = "現調済みにする";
      card.classList.remove("survey-mark-sent");
      return;
    }}
    statusEl.hidden = true;
    statusEl.textContent = "";
    btn.disabled = false;
    btn.textContent = "現調済みにする";
    card.classList.remove("survey-mark-sent");
  }}
  function mapSurveySubmitError(httpStatus, body) {{
    var err = "";
    if (body && typeof body === "object") {{
      err = String(body.error || body.message || "");
    }}
    if (
      httpStatus === 409 &&
      (err === "duplicate_open_request" || err === "duplicate_request_id")
    ) {{
      return {{
        state: "duplicate",
        message: "すでに送信済みです（PC反映待ち）",
        persist: true,
      }};
    }}
    if (err === "not_survey_wait") {{
      return {{
        state: "error",
        message: "この案件は現在、現調待ちではありません",
        persist: false,
      }};
    }}
    if (err === "case_not_found") {{
      return {{
        state: "error",
        message: "対象案件が見つかりません",
        persist: false,
      }};
    }}
    if (httpStatus === 403 || err === "origin_not_allowed") {{
      return {{
        state: "error",
        message: "送信に失敗しました（接続元が許可されていません）",
        persist: false,
      }};
    }}
    if (httpStatus === 401 || err === "invalid_api_key") {{
      return {{
        state: "error",
        message: "送信に失敗しました（APIキーが無効です）",
        persist: false,
      }};
    }}
    if (httpStatus === 503 || err === "server_not_configured") {{
      return {{
        state: "error",
        message: "送信機能がサーバ側で未設定です",
        persist: false,
      }};
    }}
    return {{
      state: "error",
      message: "送信に失敗しました。通信状態を確認して再試行してください",
      persist: false,
    }};
  }}
  document.querySelectorAll("[data-survey-mark-done]").forEach(function(btn) {{
    if (!SURVEY_STATUS_REQUEST_API_KEY) btn.disabled = true;
  }});
  document.querySelectorAll(".survey-update-card[data-management-no-key]").forEach(function(card) {{
    var key = (card.getAttribute("data-management-no-key") || "").trim();
    var action = (card.getAttribute("data-requested-action") || "mark_survey_completed").trim();
    var btn = card.querySelector("[data-survey-mark-done]");
    var statusEl = card.querySelector("[data-survey-mark-status]");
    if (!key || !btn || !statusEl) return;
    if (!SURVEY_STATUS_REQUEST_API_KEY) {{
      setSurveyMarkUi(
        card,
        btn,
        statusEl,
        "error",
        "送信設定が未設定です（ポータル再生成時にキーが必要です）",
      );
      return;
    }}
    var lsKey = surveySentLsKey(key, action);
    try {{
      if (localStorage.getItem(lsKey) === "1") {{
        setSurveyMarkUi(card, btn, statusEl, "sent", "送信済み（PC反映待ち）");
      }}
    }} catch (e) {{}}
    btn.addEventListener("click", function() {{
      if (btn.disabled) return;
      if (!window.confirm(SURVEY_MARK_CONFIRM)) return;
      var payload = {{
        request_id: newRequestId(),
        management_no_key: key,
        management_no: (card.getAttribute("data-management-no") || "").trim(),
        label: (card.getAttribute("data-label") || "").trim(),
        requested_action: action,
        source: "portal_survey",
        portal_page_url: location.href,
        client_note: "",
      }};
      setSurveyMarkUi(card, btn, statusEl, "sending");
      fetch(SURVEY_STATUS_REQUEST_ENDPOINT, {{
        method: "POST",
        headers: {{
          "Content-Type": "application/json",
          apikey: SURVEY_STATUS_REQUEST_API_KEY,
        }},
        body: JSON.stringify(payload),
      }})
        .then(function(res) {{
          return res
            .json()
            .catch(function() {{ return {{}}; }})
            .then(function(data) {{ return {{ res: res, data: data }}; }});
        }})
        .then(function(r) {{
          if (r.res.ok && r.data && r.data.ok) {{
            try {{
              localStorage.setItem(lsKey, "1");
            }} catch (e2) {{}}
            setSurveyMarkUi(card, btn, statusEl, "sent", "送信済み（PC反映待ち）");
            return;
          }}
          var mapped = mapSurveySubmitError(r.res.status, r.data);
          if (mapped.persist) {{
            try {{
              localStorage.setItem(lsKey, "1");
            }} catch (e3) {{}}
            setSurveyMarkUi(card, btn, statusEl, "duplicate", mapped.message);
            return;
          }}
          setSurveyMarkUi(card, btn, statusEl, "error", mapped.message);
        }})
        .catch(function() {{
          setSurveyMarkUi(
            card,
            btn,
            statusEl,
            "error",
            "送信に失敗しました。通信状態を確認して再試行してください",
          );
        }});
    }});
  }});
"""


def render_negotiation_immediate_status_js(
    endpoint: str,
    api_key: str,
    promoted_candidates_json: str,
) -> str:
    ep = json.dumps(endpoint, ensure_ascii=False)
    key = json.dumps(api_key, ensure_ascii=False)
    return f"""
  var PORTAL_STATUS_ENDPOINT = {ep};
  var PORTAL_STATUS_API_KEY = {key};
  var RETURN_CANDIDATE_LS_KEY = "portalReturnCandidates";
  var PROMOTED_SURVEY_CANDIDATES = {promoted_candidates_json};
  var REVERT_CONFIRM =
    "この案件を現調待ち一覧へ戻しますか？\\n\\n交渉待ちから非表示になり、現調待ちページに再表示されます。";
  var RETURN_CANDIDATE_CLEAR_CONFIRM = "この案件の返却候補を解除しますか？";
  function escHtml(s) {{
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }}
  function portalStatusMapFromResponse(data) {{
    var map = Object.create(null);
    if (!data || !Array.isArray(data.overrides)) return map;
    data.overrides.forEach(function(row) {{
      var k = String(row.management_no_key || "").trim();
      var st = String(row.portal_status || "").trim();
      if (k && st) map[k] = st;
    }});
    return map;
  }}
  function existingNegotiationKeys() {{
    var set = Object.create(null);
    document.querySelectorAll(".negotiation-card[data-management-no-key]").forEach(function(card) {{
      var k = (card.getAttribute("data-management-no-key") || "").trim();
      if (k) set[k] = true;
    }});
    return set;
  }}
  function appendPromotedCards(statusMap) {{
    var host = document.querySelector("main");
    if (!host || !Array.isArray(PROMOTED_SURVEY_CANDIDATES)) return;
    var existing = existingNegotiationKeys();
    // 返却待ちセクションより前（交渉待ちカード群の直後）に挿入する基準点
    var mapSection = host.querySelector(".return-candidate-section");
    var idx = 0;
    PROMOTED_SURVEY_CANDIDATES.forEach(function(c) {{
      var key = String(c.management_no_key || "").trim();
      if (!key || existing[key]) return;
      if (statusMap[key] !== "negotiation_wait") return;
      var label = String(c.label || "");
      var mno = String(c.management_no || "");
      var note = String(c.note || "—");
      var html =
        '<article class="card negotiation-card negotiation-card-promoted" data-card-index="p' + idx + '"'
        + ' data-management-no-key="' + escHtml(key) + '"'
        + ' data-management-no="' + escHtml(mno) + '"'
        + ' data-label="' + escHtml(label) + '" data-portal-promoted="1">'
        + '<motion class="card-head">'.replace("motion", "div")
        + '<h2 class="card-title">' + escHtml(label) + '</h2>'
        + '<p class="item-mgmt">' + escHtml(mno) + '</p>'
        + '<div class="card-actions card-actions-revert" role="group" aria-label="現調待ちに戻す">'
        + '<button type="button" class="btn btn-revert" data-negotiation-revert>現調待ちに戻す</button>'
        + '<p class="revert-hint muted-tiny">現調待ちから即時昇格した案件です。</p>'
        + '<p class="negotiation-revert-status muted-tiny" data-negotiation-revert-status hidden role="status"></p>'
        + '</div></div>'
        + '<div class="note-panel">' + escHtml(note) + '</div>'
        + '</article>';
      // 返却待ちセクションより前に挿入して既存カードと同じ一覧エリアに表示する
      if (mapSection) {{
        mapSection.insertAdjacentHTML("beforebegin", html);
      }} else {{
        host.insertAdjacentHTML("beforeend", html);
      }}
      existing[key] = true;
      idx += 1;
    }});
  }}
  function bindRevertButtons() {{
    document.querySelectorAll(".negotiation-card[data-management-no-key]").forEach(function(card) {{
      var key = (card.getAttribute("data-management-no-key") || "").trim();
      var btn = card.querySelector("[data-negotiation-revert]");
      var statusEl = card.querySelector("[data-negotiation-revert-status]");
      if (!key || !btn || !statusEl) return;
      if (btn.getAttribute("data-revert-bound") === "1") return;
      btn.setAttribute("data-revert-bound", "1");
      if (!PORTAL_STATUS_API_KEY) {{
        btn.disabled = true;
        return;
      }}
      btn.addEventListener("click", function() {{
        if (btn.disabled) return;
        if (!window.confirm(REVERT_CONFIRM)) return;
        btn.disabled = true;
        statusEl.hidden = false;
        statusEl.textContent = "送信中...";
        fetch(PORTAL_STATUS_ENDPOINT, {{
          method: "POST",
          headers: {{
            "Content-Type": "application/json",
            apikey: PORTAL_STATUS_API_KEY,
          }},
          body: JSON.stringify({{
            management_no_key: key,
            action: "revert_to_survey_wait",
            source: "portal_negotiation",
            note: "",
          }}),
        }})
          .then(function(res) {{
            return res
              .json()
              .catch(function() {{ return {{}}; }})
              .then(function(data) {{ return {{ res: res, data: data }}; }});
          }})
          .then(function(r) {{
            if (r.res.ok && r.data && r.data.ok) {{
              card.hidden = true;
              statusEl.textContent = "現調待ちへ戻しました";
              try {{
                localStorage.removeItem("portal_case_status:" + key);
              }} catch (e2) {{}}
              return;
            }}
            btn.disabled = false;
            statusEl.textContent = "送信に失敗しました";
          }})
          .catch(function() {{
            btn.disabled = false;
            statusEl.textContent = "送信に失敗しました";
          }});
      }});
    }});
  }}
  function fetchPortalOverrides() {{
    if (!PORTAL_STATUS_API_KEY) return Promise.resolve(Object.create(null));
    return fetch(PORTAL_STATUS_ENDPOINT, {{
      method: "GET",
      headers: {{ apikey: PORTAL_STATUS_API_KEY }},
    }})
      .then(function(res) {{
        return res.json().catch(function() {{ return {{}}; }});
      }})
      .then(function(data) {{
        if (!data || !data.ok) return Object.create(null);
        return portalStatusMapFromResponse(data);
      }})
      .catch(function() {{ return Object.create(null); }});
  }}
  function loadReturnCandidates() {{
    try {{
      var raw = localStorage.getItem(RETURN_CANDIDATE_LS_KEY);
      if (!raw) return [];
      var arr = JSON.parse(raw);
      return Array.isArray(arr) ? arr : [];
    }} catch (e) {{
      return [];
    }}
  }}
  function saveReturnCandidates(items) {{
    try {{
      localStorage.setItem(RETURN_CANDIDATE_LS_KEY, JSON.stringify(items));
    }} catch (e) {{}}
  }}
  function fmtMarkedAt(iso) {{
    var s = String(iso || "").trim();
    if (!s) return "時刻不明";
    var d = new Date(s);
    if (isNaN(d.getTime())) return "時刻不明";
    return (
      d.getFullYear() + "-" +
      String(d.getMonth() + 1).padStart(2, "0") + "-" +
      String(d.getDate()).padStart(2, "0") + " " +
      String(d.getHours()).padStart(2, "0") + ":" +
      String(d.getMinutes()).padStart(2, "0")
    );
  }}
  function renderReturnCandidateList() {{
    var listEl = document.getElementById("return-candidate-list");
    var emptyEl = document.getElementById("return-candidate-empty");
    if (!listEl || !emptyEl) return;
    var items = loadReturnCandidates();
    listEl.innerHTML = "";
    if (!items.length) {{
      emptyEl.hidden = false;
      return;
    }}
    emptyEl.hidden = true;
    items.forEach(function(it, i) {{
      var key = String(it.management_no_key || "").trim();
      if (!key) return;
      var html =
        '<article class="return-candidate-item" role="listitem" data-return-candidate-key="' + escHtml(key) + '">' +
        '<div class="return-candidate-item-head">' +
        '<div>' +
        '<p class="return-candidate-item-title">' + escHtml(String(it.label || "（名称未設定）")) + "</p>" +
        '<p class="return-candidate-item-mgmt">' + escHtml(String(it.management_no || "管理番号不明")) + "</p>" +
        "</div>" +
        '<button type="button" class="btn btn-return-candidate-clear" data-return-candidate-clear="' + escHtml(key) + '">返却候補を解除</button>' +
        "</div>" +
        '<p class="return-candidate-item-meta">返却候補（モック） / marked_at: ' + escHtml(fmtMarkedAt(it.marked_at)) + "</p>" +
        "</article>";
      listEl.insertAdjacentHTML("beforeend", html);
    }});
    listEl.querySelectorAll("[data-return-candidate-clear]").forEach(function(btn) {{
      if (btn.getAttribute("data-clear-bound") === "1") return;
      btn.setAttribute("data-clear-bound", "1");
      btn.addEventListener("click", function() {{
        var key = (btn.getAttribute("data-return-candidate-clear") || "").trim();
        if (!key) return;
        if (!window.confirm(RETURN_CANDIDATE_CLEAR_CONFIRM)) return;
        var next = loadReturnCandidates().filter(function(it) {{
          return String(it.management_no_key || "").trim() !== key;
        }});
        saveReturnCandidates(next);
        renderReturnCandidateList();
      }});
    }});
  }}
  fetchPortalOverrides().then(function(statusMap) {{
    appendPromotedCards(statusMap);
    bindRevertButtons();
    renderReturnCandidateList();
  }});
"""
