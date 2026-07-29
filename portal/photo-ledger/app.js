(() => {
  "use strict";

  const pack = window.PHOTO_LEDGER_PACK;
  if (!pack || !Array.isArray(pack.markers) || typeof qrcode !== "function") {
    document.body.textContent = "札パックまたはQR生成機能を読み込めませんでした。";
    return;
  }

  const list = document.getElementById("markerList");
  const activePanel = document.getElementById("activePanel");
  const dialog = document.getElementById("markerDialog");
  const toast = document.getElementById("toast");
  const eventKey = `photo-ledger-events:${pack.sessionId}`;
  const lastKey = `photo-ledger-last:${pack.sessionId}`;
  const activeKey = `photo-ledger-active:${pack.sessionId}`;
  const sequenceKey = `photo-ledger-sequence:${pack.sessionId}`;
  let wakeLock = null;
  let shownCard = null;
  let active = loadJson(activeKey, null);

  document.getElementById("managementNo").textContent = pack.managementNo;
  document.getElementById("spanLabel").textContent = pack.spanLabel;
  document.getElementById("markerCount").textContent = `${pack.markers.length}種類`;

  function loadJson(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key) || "null") ?? fallback;
    } catch {
      return fallback;
    }
  }

  function saveJson(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function nextSequence() {
    const next = Number(localStorage.getItem(sequenceKey) || "0") + 1;
    localStorage.setItem(sequenceKey, String(next));
    return next;
  }

  function crc32(text) {
    let crc = -1;
    const bytes = new TextEncoder().encode(text);
    for (const byte of bytes) {
      crc ^= byte;
      for (let bit = 0; bit < 8; bit += 1) {
        crc = (crc >>> 1) ^ (0xEDB88320 & -(crc & 1));
      }
    }
    return ((crc ^ -1) >>> 0).toString(16).toUpperCase().padStart(8, "0");
  }

  function encodeValues(prefix, values) {
    const canonical = JSON.stringify(values);
    return `${prefix}${JSON.stringify({ ...values, x: crc32(canonical) })}`;
  }

  function createQrSvg(payload) {
    const code = qrcode(0, "Q");
    code.addData(payload, "Byte");
    code.make();
    return code.createSvgTag(8, 4);
  }

  function startValues(marker, sequence) {
    const source = marker.payloadValues;
    const values = {
      v: 1, t: "G", s: pack.sessionId, q: sequence,
      c: source.c, m: source.m, l: source.l,
      k: source.k, b: source.b, p: source.p, d: source.d
    };
    if (source.w) values.w = source.w;
    if (source.n) values.n = source.n;
    return values;
  }

  function startGroup(marker) {
    if (active && active.endMode !== "NONE") {
      showToast("先に現在グループの終了札を作ってください");
      activePanel.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    const sequence = nextSequence();
    const values = startValues(marker, sequence);
    const card = {
      kind: "START",
      sequence,
      label: marker.label,
      instruction: "この札の次から、同じ区分の候補写真を撮影",
      payload: encodeValues("IP1:", values)
    };
    active = {
      markerId: marker.id,
      label: marker.label,
      shortLabel: marker.shortLabel,
      endMode: marker.endMode || "NONE",
      startSequence: sequence,
      values,
      counts: [],
      currentClaim: sourceClaim(values.d),
      selected: [],
      reusePhoto: null
    };
    saveJson(activeKey, active);
    persistIssued(card);
    showCard(card);
    renderActive();
  }

  function sourceClaim(wire) {
    return ({ P: "PLANNED", A: "ADDED", C: "CHANGED", S: "SPECIAL" })[wire] || "PLANNED";
  }

  function claimWire(claim) {
    return ({ PLANNED: "P", ADDED: "A", CHANGED: "C", SPECIAL: "S" })[claim];
  }

  function persistIssued(card) {
    const events = loadJson(eventKey, []);
    events.push({
      event: "issued",
      kind: card.kind,
      sessionId: pack.sessionId,
      sequence: card.sequence,
      startSequence: active ? active.startSequence : null,
      issuedAt: new Date().toISOString(),
      packHash: pack.packHash,
      payload: card.payload
    });
    saveJson(eventKey, events);
    saveJson(lastKey, card);
  }

  function countSegments() {
    const segments = [];
    for (const entry of active.counts) {
      const last = segments.at(-1);
      if (!last || last.claim !== entry.claim) {
        segments.push({ claim: entry.claim, counts: [entry.count] });
      } else {
        last.counts.push(entry.count);
      }
    }
    return segments;
  }

  function endValues(sequence) {
    const start = active.values;
    const values = {
      v: 2, t: "E", s: pack.sessionId, q: sequence,
      g: active.startSequence, c: start.c, m: start.m,
      l: start.l, k: start.k, b: start.b, p: start.p,
      u: active.endMode === "COUNT" ? "C" : "P"
    };
    if (active.endMode === "COUNT") {
      values.a = countSegments().map((segment) => [
        claimWire(segment.claim), segment.counts
      ]);
    } else {
      values.o = [...active.selected].sort((a, b) => a - b);
      if (active.reusePhoto) {
        values.r = [[
          active.reusePhoto,
          start.k === "O" ? "B" : "O"
        ]];
      }
    }
    return values;
  }

  function finishGroup() {
    if (active.endMode === "COUNT" && active.counts.length === 0) {
      showToast("写真ごとの本数を1つ以上入力してください");
      return;
    }
    if (active.endMode === "PICK" && active.selected.length === 0) {
      showToast("採用する写真を1つ以上選んでください");
      return;
    }
    const sequence = nextSequence();
    const values = endValues(sequence);
    const summary = active.endMode === "COUNT"
      ? `${active.counts.length}枚・計${active.counts.reduce((sum, item) => sum + item.count, 0)}本`
      : `採用 ${active.selected.join("・")}枚目`;
    const card = {
      kind: active.endMode,
      sequence,
      label: `${active.shortLabel} ${active.endMode === "COUNT" ? "集計" : "採用"}`,
      instruction: `${summary}／この札までが同じグループ`,
      payload: encodeValues("IP2:", values),
      closesGroup: true
    };
    persistIssued(card);
    showCard(card);
  }

  function renderActive() {
    if (!active) {
      activePanel.hidden = true;
      activePanel.innerHTML = "";
      return;
    }
    activePanel.hidden = false;
    const head = `
      <div class="active-head">
        <div><span>撮影中 G${active.startSequence}</span><strong>${escapeHtml(active.label)}</strong></div>
        <button id="cancelActive" class="text-button" type="button">取消</button>
      </div>`;
    if (active.endMode === "COUNT") {
      const chips = active.counts.map((item, index) =>
        `<span class="count-chip ${item.claim.toLowerCase()}">${index + 1}枚目=${item.count}本</span>`
      ).join("") || "<p class=\"empty-help\">写真を撮るたび、その写真に写った本数を押す</p>";
      activePanel.innerHTML = `${head}
        <p class="mode-title">写真ごとの本数</p>
        <div class="claim-tabs">
          ${claimButton("PLANNED", "予定")}
          ${claimButton("ADDED", "追加")}
          ${claimButton("CHANGED", "変更")}
        </div>
        <div class="number-pad">
          ${[1,2,3,4,5,6,7,8,9].map((value) =>
            `<button class="count-button" data-count="${value}" type="button">${value}本</button>`
          ).join("")}
        </div>
        <div class="count-list">${chips}</div>
        <div class="editor-actions">
          <button id="undoCount" class="secondary" type="button">1つ戻す</button>
          <button id="finishGroup" class="primary" type="button">集計QRを表示</button>
        </div>`;
    } else if (active.endMode === "PICK") {
      activePanel.innerHTML = `${head}
        <p class="mode-title">撮影後、採用する相対位置を選ぶ</p>
        <div class="pick-grid">
          ${Array.from({ length: 12 }, (_, index) => index + 1).map((value) =>
            `<button class="pick-button ${active.selected.includes(value) ? "selected" : ""}" data-pick="${value}" type="button">${value}</button>`
          ).join("")}
        </div>
        ${reuseEditor()}
        <div class="editor-actions">
          <button id="clearPick" class="secondary" type="button">選択解除</button>
          <button id="finishGroup" class="primary" type="button">採用QRを表示</button>
        </div>`;
    } else {
      activePanel.innerHTML = `${head}
        <p class="empty-help">この区分は終了札なし。次の開始札までを同じグループとして扱います。</p>`;
    }
    bindActiveEvents();
  }

  function claimButton(value, label) {
    return `<button class="${active.currentClaim === value ? "selected" : ""}" data-claim="${value}" type="button">${label}</button>`;
  }

  function reuseEditor() {
    if (!["O", "B"].includes(active.values.k) || active.selected.length === 0) return "";
    const target = active.values.k === "O" ? "竹伐採前後" : "伐採前後";
    return `<div class="reuse-block">
      <p>同じ写真を${target}にも流用</p>
      <div class="reuse-buttons">
        <button type="button" data-reuse="0" class="${active.reusePhoto ? "" : "selected"}">流用なし</button>
        ${[...active.selected].sort((a, b) => a - b).map((value) =>
          `<button type="button" data-reuse="${value}" class="${active.reusePhoto === value ? "selected" : ""}">${value}枚目を流用</button>`
        ).join("")}
      </div>
    </div>`;
  }

  function bindActiveEvents() {
    document.getElementById("cancelActive").addEventListener("click", () => {
      if (!window.confirm("現在のグループ入力を取り消しますか？ 写真は変更されません。")) return;
      active = null;
      localStorage.removeItem(activeKey);
      renderActive();
    });
    activePanel.querySelectorAll("[data-claim]").forEach((button) => {
      button.addEventListener("click", () => {
        active.currentClaim = button.dataset.claim;
        saveJson(activeKey, active);
        renderActive();
      });
    });
    activePanel.querySelectorAll("[data-count]").forEach((button) => {
      button.addEventListener("click", () => {
        active.counts.push({
          count: Number(button.dataset.count),
          claim: active.currentClaim
        });
        saveJson(activeKey, active);
        renderActive();
      });
    });
    activePanel.querySelectorAll("[data-pick]").forEach((button) => {
      button.addEventListener("click", () => {
        const value = Number(button.dataset.pick);
        active.selected = active.selected.includes(value)
          ? active.selected.filter((item) => item !== value)
          : [...active.selected, value];
        if (!active.selected.includes(active.reusePhoto)) active.reusePhoto = null;
        saveJson(activeKey, active);
        renderActive();
      });
    });
    document.getElementById("undoCount")?.addEventListener("click", () => {
      active.counts.pop();
      saveJson(activeKey, active);
      renderActive();
    });
    document.getElementById("clearPick")?.addEventListener("click", () => {
      active.selected = [];
      active.reusePhoto = null;
      saveJson(activeKey, active);
      renderActive();
    });
    activePanel.querySelectorAll("[data-reuse]").forEach((button) => {
      button.addEventListener("click", () => {
        active.reusePhoto = Number(button.dataset.reuse) || null;
        saveJson(activeKey, active);
        renderActive();
      });
    });
    document.getElementById("finishGroup")?.addEventListener("click", finishGroup);
  }

  function escapeHtml(value) {
    const span = document.createElement("span");
    span.textContent = String(value);
    return span.innerHTML;
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    window.setTimeout(() => toast.classList.remove("show"), 1800);
  }

  async function requestWakeLock() {
    if (!("wakeLock" in navigator)) return;
    try { wakeLock = await navigator.wakeLock.request("screen"); } catch { wakeLock = null; }
  }

  async function showCard(card) {
    const startedAt = performance.now();
    shownCard = card;
    document.getElementById("dialogManagement").textContent = `管理番号 ${pack.managementNo}`;
    document.getElementById("dialogSpan").textContent = pack.spanLabel;
    document.getElementById("dialogLabel").textContent = card.label;
    document.getElementById("dialogSequence").textContent = `当日札 ${card.sequence}`;
    document.getElementById("instruction").textContent = card.instruction;
    document.getElementById("qrTarget").innerHTML = createQrSvg(card.payload);
    dialog.showModal();
    await requestWakeLock();
    showToast(`札を表示しました（${Math.round(performance.now() - startedAt)} ms）`);
  }

  async function closeDialog() {
    if (wakeLock) {
      try { await wakeLock.release(); } catch { /* already released */ }
      wakeLock = null;
    }
    dialog.close();
    if (shownCard?.closesGroup) {
      active = null;
      localStorage.removeItem(activeKey);
      renderActive();
    }
  }

  function markerButton(marker) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `marker-button${marker.priority ? " priority" : ""}`;
    button.innerHTML = `${escapeHtml(marker.shortLabel)}${marker.priority ? "<b>必要</b>" : ""}<small>${escapeHtml(marker.label)}</small><em>${marker.endMode === "COUNT" ? "＋集計札" : marker.endMode === "PICK" ? "＋採用札" : "開始札"}</em>`;
    button.addEventListener("click", () => startGroup(marker));
    return button;
  }

  const folders = [
    { category: "E", label: "枝切り" },
    { category: "N", label: "根切り" }
  ];
  const nestedCategories = new Set(folders.map((item) => item.category));
  for (const marker of pack.markers.filter(
    (item) => !nestedCategories.has(item.payloadValues.k)
  )) {
    list.appendChild(markerButton(marker));
  }
  for (const folder of folders) {
    const markers = pack.markers.filter(
      (item) => item.payloadValues.k === folder.category
    );
    if (!markers.length) continue;
    const details = document.createElement("details");
    details.className = "marker-folder";
    const summary = document.createElement("summary");
    summary.innerHTML = `<strong>${folder.label}</strong><span>${markers.length}区分から選ぶ</span>`;
    const grid = document.createElement("div");
    grid.className = "folder-grid";
    for (const marker of markers) grid.appendChild(markerButton(marker));
    details.append(summary, grid);
    list.appendChild(details);
  }

  document.getElementById("closeButton").addEventListener("click", closeDialog);
  document.getElementById("brightnessButton").addEventListener("click", () => {
    requestWakeLock();
    showToast("端末の画面輝度を最大にしてください");
  });
  document.getElementById("restoreButton").addEventListener("click", () => {
    const card = loadJson(lastKey, null);
    if (!card) return showToast("再表示できる札がありません");
    showCard(card);
  });
  document.getElementById("exportButton").addEventListener("click", () => {
    const exportValue = {
      version: 2,
      sessionId: pack.sessionId,
      packHash: pack.packHash,
      exportedAt: new Date().toISOString(),
      activeGroup: active,
      events: loadJson(eventKey, [])
    };
    const blob = new Blob([JSON.stringify(exportValue, null, 2)], { type: "application/json" });
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(blob);
    anchor.download = `photo-ledger-${pack.sessionId}.json`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
  });

  function updateNetworkStatus() {
    const status = document.getElementById("networkStatus");
    status.textContent = navigator.onLine ? "準備済み" : "オフライン";
    status.classList.toggle("offline", !navigator.onLine);
  }
  window.addEventListener("online", updateNetworkStatus);
  window.addEventListener("offline", updateNetworkStatus);
  updateNetworkStatus();
  renderActive();

  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {
      showToast("オフライン準備に失敗しました");
    });
  }
})();
