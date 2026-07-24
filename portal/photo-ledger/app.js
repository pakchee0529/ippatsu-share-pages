(() => {
  "use strict";

  const pack = window.PHOTO_LEDGER_PACK;
  if (!pack || !Array.isArray(pack.markers)) {
    document.body.textContent = "札パックを読み込めませんでした。";
    return;
  }

  const byId = new Map(pack.markers.map((marker) => [marker.id, marker]));
  const list = document.getElementById("markerList");
  const dialog = document.getElementById("markerDialog");
  const toast = document.getElementById("toast");
  let wakeLock = null;

  document.getElementById("managementNo").textContent = pack.managementNo;
  document.getElementById("spanLabel").textContent = pack.spanLabel;
  document.getElementById("markerCount").textContent = `${pack.markers.length}種類`;

  const eventKey = `photo-ledger-events:${pack.sessionId}`;
  const lastKey = `photo-ledger-last:${pack.sessionId}`;

  function loadEvents() {
    try {
      return JSON.parse(localStorage.getItem(eventKey) || "[]");
    } catch {
      return [];
    }
  }

  function persistIssued(marker) {
    const event = {
      event: "issued",
      sessionId: pack.sessionId,
      markerId: marker.id,
      sequence: marker.payloadValues.q,
      issuedAt: new Date().toISOString(),
      packHash: pack.packHash
    };
    const events = loadEvents();
    events.push(event);
    localStorage.setItem(eventKey, JSON.stringify(events));
    localStorage.setItem(lastKey, marker.id);
    return event;
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    window.setTimeout(() => toast.classList.remove("show"), 1800);
  }

  async function requestWakeLock() {
    if (!("wakeLock" in navigator)) return;
    try {
      wakeLock = await navigator.wakeLock.request("screen");
    } catch {
      wakeLock = null;
    }
  }

  async function showMarker(marker, { record = true } = {}) {
    const startedAt = performance.now();
    if (record) persistIssued(marker);
    document.getElementById("dialogManagement").textContent =
      `管理番号 ${pack.managementNo}`;
    document.getElementById("dialogSpan").textContent = pack.spanLabel;
    document.getElementById("dialogLabel").textContent = marker.label;
    document.getElementById("dialogSequence").textContent =
      `当日札 ${marker.payloadValues.q}`;
    document.getElementById("qrTarget").innerHTML = marker.qrSvg;
    dialog.showModal();
    await requestWakeLock();
    const elapsed = Math.round(performance.now() - startedAt);
    showToast(`札を表示しました（${elapsed} ms）`);
  }

  for (const marker of pack.markers) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "marker-button";
    button.innerHTML = `${escapeHtml(marker.shortLabel)}<small>${escapeHtml(
      marker.label
    )}</small>`;
    button.addEventListener("click", () => showMarker(marker));
    list.appendChild(button);
  }

  function escapeHtml(value) {
    const span = document.createElement("span");
    span.textContent = String(value);
    return span.innerHTML;
  }

  async function closeDialog() {
    if (wakeLock) {
      try { await wakeLock.release(); } catch { /* already released */ }
      wakeLock = null;
    }
    dialog.close();
  }

  document.getElementById("closeButton").addEventListener("click", closeDialog);
  document.getElementById("brightnessButton").addEventListener("click", () => {
    requestWakeLock();
    showToast("端末の画面輝度を最大にしてください");
  });
  document.getElementById("restoreButton").addEventListener("click", () => {
    const marker = byId.get(localStorage.getItem(lastKey));
    if (!marker) {
      showToast("再表示できる札がありません");
      return;
    }
    showMarker(marker, { record: false });
  });
  document.getElementById("exportButton").addEventListener("click", () => {
    const exportValue = {
      version: 1,
      sessionId: pack.sessionId,
      packHash: pack.packHash,
      exportedAt: new Date().toISOString(),
      events: loadEvents()
    };
    const blob = new Blob(
      [JSON.stringify(exportValue, null, 2)],
      { type: "application/json" }
    );
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

  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {
      showToast("オフライン準備に失敗しました");
    });
  }
})();
