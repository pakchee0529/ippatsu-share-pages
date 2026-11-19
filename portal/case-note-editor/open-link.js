const form = document.getElementById("instruction-note-link");
const field = document.getElementById("instruction-note-link-value");
const status = document.getElementById("instruction-note-link-status");
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const expected = new URL(form.dataset.editor, location.href);
  let link;
  try {
    link = new URL(field.value.trim());
  } catch {
    status.textContent = "社内で受け取った編集リンクを入力してください。";
    return;
  }
  const hash = new URLSearchParams(link.hash.slice(1));
  if (link.origin !== expected.origin || link.pathname !== expected.pathname ||
      link.search || !/^[A-Za-z0-9_-]{43}$/.test(hash.get("edit") || "")) {
    status.textContent = "この指示書用の編集リンクを確認してください。";
    return;
  }
  expected.hash = new URLSearchParams({ edit: hash.get("edit") }).toString();
  location.assign(expected);
});
