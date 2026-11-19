const api = "https://evmgsqdrojxppxknrzfk.supabase.co/functions/v1/case-note-editor";
const token = new URLSearchParams(location.hash.slice(1)).get("edit");
history.replaceState(null, "", location.pathname);
const status = document.querySelector("#status");
const notes = document.querySelector("#notes");

async function request(options = {}) {
  const response = await fetch(api, { ...options, cache: "no-store",
    headers: { authorization: "Bearer " + token } });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data === "string" ? data : "処理に失敗しました。");
  return data;
}

async function show() {
  if (!token) throw new Error("社内の編集リンクから開いてください。");
  const data = await request();
  document.querySelector("h1").textContent = data.case.management_no + " " + data.case.label;
  notes.replaceChildren();
  for (const [kind, title] of [["permanent", "恒久メモ"], ["next_action", "次回メモ"]]) {
    const section = document.createElement("section");
    const heading = document.createElement("h2");
    heading.textContent = title;
    section.append(heading);
    const current = data.notes.filter(note => note.note_type === kind);
    for (const note of current.length ? current : [{ id: "", body: "", updated_at: "" }]) {
      const form = document.createElement("form");
      const label = document.createElement("label");
      label.textContent = title;
      const input = document.createElement("textarea");
      input.value = note.body;
      input.rows = 5;
      input.cols = 36;
      input.maxLength = 10000;
      label.append(document.createElement("br"), input);
      const button = document.createElement("button");
      button.type = "submit";
      button.textContent = "保存";
      form.append(label, document.createElement("br"), button);
      form.addEventListener("submit", async event => {
        event.preventDefault();
        button.disabled = true;
        try {
          await request({ method: "POST", body: new URLSearchParams({
            kind, body: input.value, id: note.id, version: note.updated_at,
          }) });
          await show();
          status.textContent = "保存して読み戻しました。";
        } catch (error) {
          status.textContent = error.message;
          button.disabled = false;
        }
      });
      section.append(form);
    }
    notes.append(section);
  }
  status.textContent = "";
}

show().catch(error => { status.textContent = error.message; });
