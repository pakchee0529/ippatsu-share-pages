(() => {
  "use strict";

  const packRegistry = window.PHOTO_LEDGER_PACK;
  const workDateStorageKey = "photo-ledger-selected-work-date";
  const packDays = Array.isArray(packRegistry?.days) && packRegistry.days.length
    ? packRegistry.days
    : packRegistry
    ? [packRegistry]
    : [];
  const pack = chooseWorkDatePack(packDays);
  const packCases = Array.isArray(pack?.cases) && pack.cases.length
    ? pack.cases
    : pack
    ? [{
        caseId: pack.caseId,
        managementNo: pack.managementNo,
        spanLabel: pack.spanLabel,
        planned: {},
        markers: pack.markers
      }]
    : [];
  if (
    !packRegistry
    || !pack
    || !packCases.length
    || packCases.some((item) => !Array.isArray(item.markers))
    || typeof qrcode !== "function"
  ) {
    document.body.textContent = "札パックまたはQR生成機能を読み込めませんでした。";
    return;
  }

  const list = document.getElementById("markerList");
  const activePanel = document.getElementById("activePanel");
  const dialog = document.getElementById("markerDialog");
  const toast = document.getElementById("toast");
  const workDateSwitcher = document.getElementById("workDateSwitcher");
  const workDateSelect = document.getElementById("workDateSelect");
  const caseSelect = document.getElementById("caseSelect");
  const eventKey = `photo-ledger-events:${pack.sessionId}`;
  const lastKey = `photo-ledger-last:${pack.sessionId}`;
  const activeKey = `photo-ledger-active:${pack.sessionId}`;
  const sequenceKey = `photo-ledger-sequence:${pack.sessionId}`;
  const selectedCaseKey = `photo-ledger-selected-case:${pack.sessionId}`;
  const pendingPairKey = `photo-ledger-pending-before:${pack.sessionId}`;
  const genericCasesKey = `photo-ledger-generic-cases:${pack.sessionId}`;
  const legacyOverviewPairKey =
    `photo-ledger-pending-overview-before:${pack.sessionId}`;
  let wakeLock = null;
  let shownCard = null;
  const savedGenericCases = loadJson(genericCasesKey, {});
  if (pack.mode === "generic") {
    for (const caseItem of packCases) {
      const saved = savedGenericCases[caseItem.caseId];
      if (!saved) continue;
      if (saved.managementNo) caseItem.managementNo = saved.managementNo;
      if (saved.spanLabel) caseItem.spanLabel = saved.spanLabel;
      for (const marker of caseItem.markers) {
        marker.payloadValues.m = caseItem.managementNo;
        marker.payloadValues.l = caseItem.spanLabel;
      }
    }
  }
  let active = loadJson(activeKey, null);
  const activeCase = active
    ? packCases.find((item) => caseWireId(item) === active.values.c)
    : null;
  let currentCase = activeCase || packCases.find(
    (item) => item.caseId === localStorage.getItem(selectedCaseKey)
  ) || packCases[0];
  let pendingBeforeByCategory = loadJson(pendingPairKey, {});
  const legacyOverviewBefore = loadJson(legacyOverviewPairKey, null);
  if (legacyOverviewBefore && !pendingBeforeByCategory.O) {
    pendingBeforeByCategory.O = legacyOverviewBefore;
    saveJson(pendingPairKey, pendingBeforeByCategory);
    localStorage.removeItem(legacyOverviewPairKey);
  }

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

  function caseWireId(caseItem) {
    return caseItem.markers[0]?.payloadValues?.c || "";
  }

  const plannedLabels = {
    branch_cut_under_10: "枝10未満",
    branch_cut_10_20: "枝20未満",
    branch_cut_20_30: "枝30未満",
    branch_cut_30_40: "枝40未満",
    branch_cut_40_50: "枝50未満",
    branch_cut_over_50: "枝50超過",
    root_cut_under_10: "根10未満",
    root_cut_10_20: "根20未満",
    root_cut_20_30: "根30未満",
    root_cut_30_40: "根40未満",
    root_cut_40_50: "根50未満",
    root_cut_over_50: "根50超過",
    brush_area_m2: "柴",
    bamboo_count: "竹",
    vine_locations: "つる",
    carry_out: "持出あり",
    collect: "集積あり"
  };

  function plannedSummary(caseItem) {
    const entries = [];
    for (const [field, value] of Object.entries(caseItem.planned || {})) {
      if (!plannedLabels[field] || !value) continue;
      if (field === "carry_out" || field === "collect") {
        entries.push(plannedLabels[field]);
      } else {
        const unit = field === "brush_area_m2"
          ? "㎡"
          : field === "vine_locations"
          ? "箇所"
          : "本";
        entries.push(`${plannedLabels[field]} ${value}${unit}`);
      }
    }
    return entries.length ? `BA前後、${entries.join("、")}` : "BA前後";
  }

  function renderCaseHeader() {
    caseSelect.replaceChildren();
    for (const [index, caseItem] of packCases.entries()) {
      const option = document.createElement("option");
      option.value = caseItem.caseId;
      option.textContent =
        `${index + 1}. ${caseItem.managementNo} ${caseItem.spanLabel}`;
      caseSelect.appendChild(option);
    }
    caseSelect.value = currentCase.caseId;
    const currentIndex = packCases.indexOf(currentCase);
    document.getElementById("casePosition").textContent =
      `${currentIndex + 1} / ${packCases.length}`;
    document.getElementById("managementNo").textContent =
      currentCase.managementNo;
    document.getElementById("spanLabel").textContent =
      currentCase.spanLabel;
    document.getElementById("plannedSummary").textContent =
      plannedSummary(currentCase);
    document.getElementById("markerCount").textContent =
      `${currentCase.markers.length}種類`;
  }

  function syncGenericEditor() {
    const editor = document.getElementById("genericEditor");
    if (!editor) return;
    editor.hidden = pack.mode !== "generic";
    if (pack.mode !== "generic") return;
    document.getElementById("genericManagementNo").value =
      currentCase.managementNo.startsWith("汎用") ? "" : currentCase.managementNo;
    document.getElementById("genericSpanLabel").value =
      currentCase.spanLabel === "現場入力待ち" ? "" : currentCase.spanLabel;
  }

  function localTodayKey() {
    const today = new Date();
    return [
      String(today.getFullYear()).slice(-2),
      String(today.getMonth() + 1).padStart(2, "0"),
      String(today.getDate()).padStart(2, "0")
    ].join("");
  }

  function chooseWorkDatePack(days) {
    if (!days.length) return null;
    const saved = localStorage.getItem(workDateStorageKey);
    const savedPack = days.find((item) => item.workDate === saved);
    if (savedPack) return savedPack;
    const today = localTodayKey();
    const todayPack = days.find((item) => item.workDate === today);
    if (todayPack) return todayPack;
    const sorted = [...days].sort((a, b) =>
      String(a.workDate).localeCompare(String(b.workDate))
    );
    return sorted.find((item) => String(item.workDate) > today)
      || sorted.at(-1);
  }

  function workDateLabel(value) {
    const text = String(value || "");
    return /^\d{6}$/.test(text)
      ? `20${text.slice(0, 2)}/${text.slice(2, 4)}/${text.slice(4, 6)}`
      : text;
  }

  function renderWorkDates() {
    workDateSelect.replaceChildren();
    for (const day of [...packDays].sort((a, b) =>
      String(a.workDate).localeCompare(String(b.workDate))
    )) {
      const option = document.createElement("option");
      option.value = day.workDate;
      option.textContent = `${workDateLabel(day.workDate)}・${day.caseCount || day.cases?.length || 0}案件`;
      workDateSelect.appendChild(option);
    }
    workDateSelect.value = pack.workDate;
    workDateSwitcher.hidden = packDays.length < 2;
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

  function recoveryCode(payload) {
    try {
      const values = JSON.parse(payload.slice(4));
      if (!values.s || !values.q || !values.x) return "";
      return `IPR1:${values.s}:${values.q}:${String(values.x).toUpperCase()}`;
    } catch {
      return "";
    }
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
      c: source.c,
      m: pack.mode === "generic" ? currentCase.managementNo : source.m,
      l: pack.mode === "generic" ? currentCase.spanLabel : source.l,
      k: source.k, b: source.b, p: source.p, d: source.d
    };
    if (source.w) values.w = source.w;
    if (source.n) values.n = source.n;
    return values;
  }

  function isPairedCategory(categoryWire) {
    return ["O", "S", "B", "X"].includes(categoryWire);
  }

  function isPairedBefore(values) {
    return isPairedCategory(values.k) && values.p === "B";
  }

  function isPairedAfter(values) {
    return isPairedCategory(values.k) && values.p === "A";
  }

  function pairedWorkLabel(categoryWire) {
    return ({ O: "伐採", S: "柴伐採", B: "竹伐採" })[categoryWire] || "前後";
  }

  function pairedPhaseLabel(categoryWire, phase) {
    return `${pairedWorkLabel(categoryWire)}${phase === "BEFORE" ? "前" : "後"}`;
  }

  function pendingPairId(values) {
    return `${values.c}:${values.k}:${values.w || ""}:${values.n || ""}`;
  }

  function rememberPendingBefore(group) {
    if (!group || !isPairedBefore(group.values)) return;
    pendingBeforeByCategory[pendingPairId(group.values)] = {
      startSequence: group.startSequence,
      values: group.values,
      label: group.label
    };
    saveJson(pendingPairKey, pendingBeforeByCategory);
  }

  function startGroup(marker, vehicle = "") {
    if (
      pack.mode === "generic"
      && (currentCase.managementNo.startsWith("汎用")
        || currentCase.spanLabel === "現場入力待ち")
    ) {
      showToast("先にこの案件スロットの管理番号と径間名を保存してください");
      document.getElementById("genericManagementNo")?.focus();
      return;
    }
    if (active && active.endMode !== "NONE") {
      showToast("先に現在グループの終了札を作ってください");
      activePanel.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    if (active && isPairedBefore(active.values)) {
      rememberPendingBefore(active);
    }
    const isAfter = isPairedAfter(marker.payloadValues);
    const exactPending = pendingBeforeByCategory[pendingPairId(marker.payloadValues)];
    const legacyPending = marker.payloadValues.k === "X"
      ? null
      : pendingBeforeByCategory[marker.payloadValues.k];
    const pendingBefore = exactPending || legacyPending;
    if (isAfter && !pendingBefore) {
      showToast(
        `先に${pairedPhaseLabel(marker.payloadValues.k, "BEFORE")}候補を撮影してください`
      );
      return;
    }
    const sequence = nextSequence();
    const values = startValues(marker, sequence);
    const transportLabel = vehicle
      ? `${marker.vehicleLabel || marker.label} ${vehicle}`
      : marker.label;
    if (vehicle) values.n = transportLabel;
    const card = {
      kind: "START",
      sequence,
      label: transportLabel,
      managementNo: currentCase.managementNo,
      spanLabel: currentCase.spanLabel,
      instruction: "この札の次から、同じ区分の候補写真を撮影",
      payload: encodeValues("IP1:", values)
    };
    card.recoveryCode = recoveryCode(card.payload);
    active = {
      markerId: marker.id,
      label: transportLabel,
      shortLabel: marker.shortLabel,
      endMode: marker.endMode || "NONE",
      startSequence: sequence,
      values,
      counts: [],
      currentClaim: sourceClaim(values.d),
      selected: [],
      reusePhoto: null,
      pairedStartSequence: isAfter
        ? pendingBefore.startSequence
        : null,
      pairedSelected: [],
      pairedReusePhoto: null
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
      recoveryCode: card.recoveryCode || recoveryCode(card.payload),
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

  function appendCount(value) {
    const count = Number(value);
    if (!Number.isFinite(count) || count < 1) return;
    active.counts.push({ count, claim: active.currentClaim });
    saveJson(activeKey, active);
    renderActive();
  }

  function countSummary() {
    const labels = { PLANNED: "予定", ADDED: "追加", CHANGED: "変更" };
    const segments = countSegments();
    const total = active.counts.reduce((sum, item) => sum + item.count, 0);
    const detail = segments
      .map((segment) => `${labels[segment.claim] || segment.claim}:${segment.counts.join("+")}本`)
      .join(" / ");
    return `合計${total}本（${detail}）`;
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
      values.o = [...active.selected];
      if (active.reusePhoto) {
        values.r = [[
          active.reusePhoto,
          start.k === "O" ? "B" : "O"
        ]];
      }
      if (active.endMode === "PAIRED_PICK") {
        values.h = active.pairedStartSequence;
        values.j = [...active.pairedSelected];
        if (active.pairedReusePhoto) {
          values.y = [[
            active.pairedReusePhoto,
            start.k === "O" ? "B" : "O"
          ]];
        }
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
    if (
      active.endMode === "PAIRED_PICK"
      && (active.pairedSelected.length === 0 || active.selected.length === 0)
    ) {
      const work = pairedWorkLabel(active.values.k);
      showToast(`${work}前・${work}後をそれぞれ1枚以上選んでください`);
      return;
    }
    const sequence = nextSequence();
    const values = endValues(sequence);
    const summary = active.endMode === "COUNT"
      ? `${active.counts.length}枚・計${active.counts.reduce((sum, item) => sum + item.count, 0)}本`
      : active.endMode === "PAIRED_PICK"
      ? `前 ${active.pairedSelected.join("・")}／後 ${active.selected.join("・")}枚目`
      : `採用 ${active.selected.join("・")}枚目`;
    const card = {
      kind: active.endMode,
      sequence,
      label: `${active.shortLabel} ${active.endMode === "COUNT" ? "集計" : "採用"}`,
      managementNo: currentCase.managementNo,
      spanLabel: currentCase.spanLabel,
      instruction: `${summary}／この札までが同じグループ`,
      payload: encodeValues("IP2:", values),
      closesGroup: true
    };
    card.recoveryCode = recoveryCode(card.payload);
    if (active.endMode === "COUNT") {
      card.instruction = `${countSummary()}・集計QRを撮影してください`;
    }
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
        ${selectionOrderEditor(active.selected, "after", "台帳の表示順")}
        ${reuseEditor()}
        <div class="editor-actions">
          <button id="clearPick" class="secondary" type="button">選択解除</button>
          <button id="finishGroup" class="primary" type="button">採用QRを表示</button>
        </div>`;
    } else if (active.endMode === "PAIRED_PICK") {
      const beforeLabel = pairedPhaseLabel(active.values.k, "BEFORE");
      const afterLabel = pairedPhaseLabel(active.values.k, "AFTER");
      activePanel.innerHTML = `${head}
        <p class="mode-title">${beforeLabel}・${afterLabel}の採用写真をまとめて選ぶ</p>
        <p class="pick-subtitle">${beforeLabel}候補（開始札 G${active.pairedStartSequence}）</p>
        <div class="pick-grid">
          ${Array.from({ length: 12 }, (_, index) => index + 1).map((value) =>
            `<button class="pick-button ${active.pairedSelected.includes(value) ? "selected" : ""}" data-paired-pick="${value}" type="button">${value}</button>`
          ).join("")}
        </div>
        ${selectionOrderEditor(active.pairedSelected, "before", `${beforeLabel}の台帳表示順`)}
        ${pairedReuseEditor()}
        <p class="pick-subtitle">${afterLabel}候補（開始札 G${active.startSequence}）</p>
        <div class="pick-grid">
          ${Array.from({ length: 12 }, (_, index) => index + 1).map((value) =>
            `<button class="pick-button ${active.selected.includes(value) ? "selected" : ""}" data-pick="${value}" type="button">${value}</button>`
          ).join("")}
        </div>
        ${selectionOrderEditor(active.selected, "after", `${afterLabel}の台帳表示順`)}
        ${reuseEditor()}
        <div class="editor-actions">
          <button id="clearPick" class="secondary" type="button">選択解除</button>
          <button id="finishGroup" class="primary" type="button">前後採用QRを表示</button>
        </div>`;
    } else {
      const help = isPairedBefore(active.values)
        ? `採用QRは撮りません。${pairedPhaseLabel(active.values.k, "AFTER")}の撮影後に、前後候補をまとめて選びます。`
        : "この区分は終了札なし。次の開始札までを同じグループとして扱います。";
      activePanel.innerHTML = `${head}
        <p class="empty-help">${help}</p>`;
    }
    bindActiveEvents();
  }

  function claimButton(value, label) {
    return `<button class="${active.currentClaim === value ? "selected" : ""}" data-claim="${value}" type="button">${label}</button>`;
  }

  function selectionOrderEditor(selection, kind, label) {
    if (selection.length < 2) return "";
    return `<div class="selection-order">
      <p>${label}（↑↓で入れ替え）</p>
      ${selection.map((value, index) => `<div class="selection-order-row">
        <strong>${index + 1}番目：写真 ${value}</strong>
        <span>
          <button type="button" data-order-move="${kind}" data-order-index="${index}" data-order-direction="up" ${index === 0 ? "disabled" : ""}>↑</button>
          <button type="button" data-order-move="${kind}" data-order-index="${index}" data-order-direction="down" ${index === selection.length - 1 ? "disabled" : ""}>↓</button>
        </span>
      </div>`).join("")}
    </div>`;
  }

  function reuseEditor() {
    if (!["O", "B"].includes(active.values.k) || active.selected.length === 0) return "";
    const target = active.values.k === "O" ? "竹伐採前後" : "伐採前後";
    return `<div class="reuse-block">
      <p>同じ写真を${target}にも流用</p>
      <div class="reuse-buttons">
        <button type="button" data-reuse="0" class="${active.reusePhoto ? "" : "selected"}">流用なし</button>
        ${active.selected.map((value) =>
          `<button type="button" data-reuse="${value}" class="${active.reusePhoto === value ? "selected" : ""}">${value}枚目を流用</button>`
        ).join("")}
      </div>
    </div>`;
  }

  function pairedReuseEditor() {
    if (
      !["O", "B"].includes(active.values.k)
      || active.pairedSelected.length === 0
    ) return "";
    const source = pairedPhaseLabel(active.values.k, "BEFORE");
    const target = active.values.k === "O" ? "竹伐採前" : "伐採前";
    return `<div class="reuse-block">
      <p>${source}の同じ写真を${target}にも流用</p>
      <div class="reuse-buttons">
        <button type="button" data-paired-reuse="0" class="${active.pairedReusePhoto ? "" : "selected"}">流用なし</button>
        ${active.pairedSelected.map((value) =>
          `<button type="button" data-paired-reuse="${value}" class="${active.pairedReusePhoto === value ? "selected" : ""}">${value}枚目を流用</button>`
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
        appendCount(button.dataset.count);
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
    activePanel.querySelectorAll("[data-paired-pick]").forEach((button) => {
      button.addEventListener("click", () => {
        const value = Number(button.dataset.pairedPick);
        active.pairedSelected = active.pairedSelected.includes(value)
          ? active.pairedSelected.filter((item) => item !== value)
          : [...active.pairedSelected, value];
        if (!active.pairedSelected.includes(active.pairedReusePhoto)) {
          active.pairedReusePhoto = null;
        }
        saveJson(activeKey, active);
        renderActive();
      });
    });
    activePanel.querySelectorAll("[data-order-move]").forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.dataset.orderMove === "before"
          ? "pairedSelected"
          : "selected";
        const index = Number(button.dataset.orderIndex);
        const offset = button.dataset.orderDirection === "up" ? -1 : 1;
        const nextIndex = index + offset;
        if (!Number.isInteger(index) || nextIndex < 0 || nextIndex >= active[key].length) return;
        [active[key][index], active[key][nextIndex]] = [
          active[key][nextIndex], active[key][index]
        ];
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
      active.pairedSelected = [];
      active.pairedReusePhoto = null;
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
    activePanel.querySelectorAll("[data-paired-reuse]").forEach((button) => {
      button.addEventListener("click", () => {
        active.pairedReusePhoto = Number(button.dataset.pairedReuse) || null;
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
    document.getElementById("dialogManagement").textContent =
      `管理番号 ${card.managementNo || currentCase.managementNo}`;
    document.getElementById("dialogSpan").textContent =
      card.spanLabel || currentCase.spanLabel;
    document.getElementById("dialogLabel").textContent = card.label;
    document.getElementById("dialogSequence").textContent = `当日札 ${card.sequence}`;
    document.getElementById("dialogRecovery").textContent = card.recoveryCode
      ? `復元コード ${card.recoveryCode}`
      : "";
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
      if (shownCard.kind === "PAIRED_PICK") {
        delete pendingBeforeByCategory[pendingPairId(active.values)];
        delete pendingBeforeByCategory[active.values.k];
        saveJson(pendingPairKey, pendingBeforeByCategory);
      }
      active = null;
      localStorage.removeItem(activeKey);
      renderActive();
    }
  }

  function markerButton(marker) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `marker-button${marker.priority ? " priority" : ""}`;
    const endLabel = marker.endMode === "COUNT"
      ? "＋集計札"
      : marker.endMode === "PICK"
      ? "＋採用札"
      : marker.endMode === "PAIRED_PICK"
      ? "＋前後採用札"
      : "開始札";
    const priority = marker.priority
      ? `<b>${escapeHtml(marker.priorityLabel || "必要")}</b>`
      : "";
    button.innerHTML = `${escapeHtml(marker.shortLabel)}${priority}<small>${escapeHtml(marker.label)}</small><em>${endLabel}</em>`;
    const vehicles = Array.isArray(marker.vehicleOptions)
      ? marker.vehicleOptions.filter((item) => typeof item === "string" && item)
      : [];
    if (!vehicles.length) {
      button.addEventListener("click", () => startGroup(marker));
      return button;
    }
    const container = document.createElement("div");
    container.className = "marker-vehicle-card";
    button.addEventListener("click", () => showToast("車種を選択してください"));
    const vehicleChoices = document.createElement("div");
    vehicleChoices.className = "vehicle-choices";
    for (const vehicle of vehicles) {
      const choice = document.createElement("button");
      choice.type = "button";
      choice.className = "vehicle-choice";
      choice.textContent = vehicle;
      choice.addEventListener("click", () => startGroup(marker, vehicle));
      vehicleChoices.appendChild(choice);
    }
    container.append(button, vehicleChoices);
    return container;
  }

  const folders = [
    { category: "E", label: "枝切り" },
    { category: "N", label: "根切り" }
  ];
  const nestedCategories = new Set(folders.map((item) => item.category));
  function appendFolder(folder) {
    const markers = currentCase.markers.filter(
      (item) => item.payloadValues.k === folder.category
    );
    if (!markers.length) return;
    const details = document.createElement("details");
    details.className = "marker-folder";
    const summary = document.createElement("summary");
    const plannedCount = markers.filter((item) => item.priority).length;
    summary.innerHTML = `<strong>${folder.label}</strong><span>${plannedCount ? `予定 ${plannedCount}区分` : `${markers.length}区分から選ぶ`}</span>`;
    const grid = document.createElement("div");
    grid.className = "folder-grid";
    for (const marker of markers) grid.appendChild(markerButton(marker));
    details.append(summary, grid);
    list.appendChild(details);
  }

  function renderMarkerList() {
    list.replaceChildren();
    for (const marker of currentCase.markers.filter(
      (item) => item.payloadValues.k === "O"
    )) {
      list.appendChild(markerButton(marker));
    }
    for (const folder of folders) appendFolder(folder);
    for (const marker of currentCase.markers.filter(
      (item) =>
        item.payloadValues.k !== "O"
        && !nestedCategories.has(item.payloadValues.k)
    )) {
      list.appendChild(markerButton(marker));
    }
  }

  function switchCase(caseId) {
    const nextCase = packCases.find((item) => item.caseId === caseId);
    if (!nextCase || nextCase === currentCase) {
      caseSelect.value = currentCase.caseId;
      return;
    }
    if (active && active.endMode !== "NONE") {
      caseSelect.value = currentCase.caseId;
      showToast("先に現在グループの終了札を作ってください");
      return;
    }
    rememberPendingBefore(active);
    active = null;
    localStorage.removeItem(activeKey);
    currentCase = nextCase;
    localStorage.setItem(selectedCaseKey, currentCase.caseId);
    renderCaseHeader();
    syncGenericEditor();
    renderMarkerList();
    renderActive();
    showToast(
      `${currentCase.managementNo} ${currentCase.spanLabel}へ切り替えました`
    );
  }

  function moveCase(offset) {
    const currentIndex = packCases.indexOf(currentCase);
    const nextIndex =
      (currentIndex + offset + packCases.length) % packCases.length;
    switchCase(packCases[nextIndex].caseId);
  }

  function switchWorkDate(workDate) {
    if (workDate === pack.workDate) return;
    const nextPack = packDays.find((item) => item.workDate === workDate);
    if (!nextPack) {
      workDateSelect.value = pack.workDate;
      return;
    }
    if (active && active.endMode !== "NONE") {
      workDateSelect.value = pack.workDate;
      showToast("先に現在グループの終了札を作ってください");
      return;
    }
    rememberPendingBefore(active);
    active = null;
    localStorage.removeItem(activeKey);
    localStorage.setItem(workDateStorageKey, nextPack.workDate);
    window.location.reload();
  }

  workDateSelect.addEventListener(
    "change", () => switchWorkDate(workDateSelect.value)
  );
  caseSelect.addEventListener("change", () => switchCase(caseSelect.value));
  document.getElementById("saveGenericCase")?.addEventListener("click", () => {
    if (pack.mode !== "generic") return;
    const managementNo = document.getElementById("genericManagementNo").value.trim();
    const spanLabel = document.getElementById("genericSpanLabel").value.trim();
    if (!managementNo || !spanLabel) {
      showToast("管理番号と径間名を入力してください");
      return;
    }
    currentCase.managementNo = managementNo;
    currentCase.spanLabel = spanLabel;
    for (const marker of currentCase.markers) {
      marker.payloadValues.m = managementNo;
      marker.payloadValues.l = spanLabel;
    }
    const next = loadJson(genericCasesKey, {});
    next[currentCase.caseId] = { managementNo, spanLabel };
    saveJson(genericCasesKey, next);
    renderCaseHeader();
    syncGenericEditor();
    showToast("案件スロットを保存しました");
  });
  document.getElementById("previousCase").addEventListener(
    "click", () => moveCase(-1)
  );
  document.getElementById("nextCase").addEventListener(
    "click", () => moveCase(1)
  );
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
      currentCaseId: currentCase.caseId,
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
  renderWorkDates();
  renderCaseHeader();
  syncGenericEditor();
  renderMarkerList();
  renderActive();

  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {
      showToast("オフライン準備に失敗しました");
    });
  }
})();
