export function bindPermanentNote(document, location, fetchNote) {
  const id = new URLSearchParams(location.search).get("management_no");
  const source = document.getElementById("permanent-note-data");
  const data = JSON.parse(source.textContent);
  const displayed = document.getElementById("permanent-note-text");
  const pencil = document.getElementById("permanent-note-edit");
  const draft = document.getElementById("permanent-note-draft");
  const field = document.getElementById("permanent-note-value");
  const status = document.getElementById("permanent-note-status");
  const save = document.getElementById("permanent-note-save");
  const cancel = document.getElementById("permanent-note-cancel");
  if (!/^[0-9]{8}$/.test(id ?? "") || !Object.hasOwn(data, id)) {
    displayed.textContent = "対象案件を開いてください。";
    return;
  }
  displayed.textContent = (data[id].body ?? data[id]) || "記載なし";
  if (!fetchNote) return;
  let current;
  let blocked = false;
  const show = (record) => {
    if (record.management_no !== id || typeof record.body !== "string" || typeof record.revision !== "string")
      throw Error("対象案件の保存内容を確認できません。");
    current = record;
    displayed.textContent = current.body || "記載なし";
  };
  pencil.addEventListener("click", () => {
    field.value = current.body;
    draft.hidden = false;
    pencil.disabled = true;
    field.focus();
  });
  function close() {
    draft.hidden = true;
    pencil.disabled = blocked;
    if (!blocked) pencil.focus();
  }
  cancel.addEventListener("click", close);
  save.addEventListener("click", async () => {
    if (blocked || save.disabled) return;
    field.disabled = save.disabled = cancel.disabled = true;
    try {
      const body = field.value.trim();
      const receipt = await fetchNote(id, {body, revision: current.revision});
      const latest = await fetchNote(id);
      show(latest);
      if (latest.body !== body || latest.revision !== receipt.revision)
        throw Error("保存内容を確認できません。");
      status.textContent = "保存しました。";
      close();
    } catch {
      blocked = true;
      status.textContent = "保存結果を確認できません。入力を控え、ページを開き直して確認してください。";
    } finally {
      field.disabled = cancel.disabled = false;
      save.disabled = blocked;
    }
  });
  return fetchNote(id).then((record) => {
    show(record);
    pencil.hidden = false;
  }).catch(() => {
    status.textContent = "保存済みの恒久メモを取得できませんでした。";
  });
}
if (typeof document !== "undefined") {
  const config = JSON.parse(document.getElementById("shared-ledger-config").textContent);
  bindPermanentNote(document, location, async (id, edit) => {
    const endpoint = new URL("https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/portal-permanent-memos");
    endpoint.search = new URLSearchParams({date:config.date, management_no:id});
    const response = await fetch(endpoint, {
      method: edit ? "POST" : "GET",
      headers: edit ? {"Content-Type":"application/json"} : undefined,
      body: edit ? JSON.stringify(edit) : undefined,
      cache:"no-store",
      signal:AbortSignal.timeout(15000),
    });
    if (!response.ok) throw Error("恒久メモの通信に失敗しました。");
    return response.json();
  });
}
