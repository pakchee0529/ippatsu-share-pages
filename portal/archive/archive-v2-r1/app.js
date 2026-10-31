/* Read-only index of public immutable snapshots. No DB, storage, or worker APIs. */
(() => {
  'use strict';
  const result = document.getElementById('results');
  const message = document.getElementById('message');
  const older = document.getElementById('older');
  const designInput = document.getElementById('design');
  const dayInput = document.getElementById('day');
  let catalog, shown = 10;
  const el = (tag, value, cls) => {
    const node = document.createElement(tag);
    if (value !== undefined) node.textContent = value;
    if (cls) node.className = cls;
    return node;
  };
  const normalizeDesign = raw => {
    const normalized = String(raw || '').normalize('NFKC').replace(/\s+/gu, '').toUpperCase();
    const match = /^(?:B)?([0-9]{4})$/.exec(normalized);
    return match ? match[1] : null;
  };
  const dateLabel = day => `20${day.slice(0, 2)}年${Number(day.slice(2, 4))}月${Number(day.slice(4, 6))}日`;
  const route = (kind, value) => {
    if (kind === 'design' && location.protocol !== 'file:' && document.body.dataset.initialDate) { location.assign('/ippatsu-share-pages/portal/archive/?design=' + encodeURIComponent(value)); return; }
    if (kind === 'date' && location.protocol !== 'file:' && catalog.days.some(day => day.date === value && day.available)) {
      location.assign(`/ippatsu-share-pages/portal/archive/${value}/view.html`); return;
    }
    const url = location.protocol === 'file:' ? new URL(location.href) : new URL('/ippatsu-share-pages/portal/archive/', location.origin);
    url.search = ''; url.hash = '';
    if (kind) url.searchParams.set(kind, value);
    history.pushState(null, '', url);
    render();
  };
  function renderCards() {
    const days = catalog.days.filter(day => day.completed > 0);
    message.textContent = '完了した現場の日付を選んでください。';
    const cards = el('div', undefined, 'cards');
    for (const day of days.slice(0, shown)) {
      const card = el('article', undefined, 'date-card');
      card.dataset.date = day.date;
      card.append(el('h2', dateLabel(day.date)), el('p', `完了 ${day.completed}径間`, 'case-count'));
      if (!day.available) card.append(el('p', '保存帳票の索引は未登録', 'muted'));
      const a = el('a', day.available ? '離隔表を開く' : '既存資料を確認', 'button');
      a.href = day.available ? `/ippatsu-share-pages/portal/archive/${day.date}/view.html` : `/ippatsu-share-pages/portal/archive/?date=${day.date}`;
      a.addEventListener('click', event => {
        if (day.available && location.protocol !== 'file:') return;
        event.preventDefault(); route('date', day.date);
      });
      card.append(a); cards.append(card);
    }
    result.append(cards);
    older.hidden = shown >= days.length;
    if (!days.length) message.textContent = '完了した現場の記録はありません。';
  }
  function renderSnapshots(cases, heading) {
    const instructionMode = new URL(location.href).searchParams.get('document') === 'instructions';
    result.append(el('h2', heading, 'view-title'));
    result.append(el('p', `${cases.length}径間。現場ごとの保存版を表示しています。数量の合算はしていません。`, 'muted'));
    const list = el('div', undefined, 'snapshots');
    for (const item of cases) {
      const section = el('section', undefined, 'snapshot');
      section.dataset.snapshot = item.anchor;
      const meta = el('div', undefined, 'snapshot-meta');
      meta.append(el('span', dateLabel(item.date)), el('span', `受付回 ${item.episode} / 保存rev ${item.revision}`));
      const raw = item.design_original.trim();
      meta.append(el('span', raw ? `設計番号 ${item.design_original}` : '設計番号未登録'));
      const instruction = el('a', '同じ保存版の指示書', 'button secondary');
      instruction.href = item.instructions_html ? `/ippatsu-share-pages/portal/archive/${item.date}/view.html?document=instructions#${item.anchor}` : item.instructions_href;
      if (location.protocol === 'file:') instruction.href = item.instructions_html ? `?document=instructions#${item.anchor}` : 'https://pakchee0529.github.io' + item.instructions_href;
      meta.append(instruction);
      if (item.reference_href) {
        const reference = el('a', '地図・現場条件（従来表示）', 'button secondary');
        reference.href = location.protocol === 'file:' ? 'https://pakchee0529.github.io' + item.reference_href : item.reference_href;
        meta.append(reference);
      }
      section.append(meta);
      const fragment = document.createElement('template');
      // This markup is generated solely from allowlisted, script-free public
      // immutable HTML. No search text or external response is interpolated.
      fragment.innerHTML = instructionMode && item.instructions_html ? item.instructions_html : item.clearance_html;
      // Display-only projection: preserve all original source cells in catalog.
      // Never calculate a quantity or turn a missing/unknown value into zero.
      for (const table of fragment.content.querySelectorAll('table.other-counts')) {
        const headers = [...table.rows[0].cells].map(cell => cell.textContent.trim());
        if (JSON.stringify(headers) === JSON.stringify(['区分','元','反映後','計'])) {
          for (const row of table.rows) {
            if (row.cells.length !== 4) throw new Error('other-counts column mismatch');
            row.dataset.sourceReflected = row.cells[2].textContent;
            row.deleteCell(2);
          }
          table.rows[0].cells[2].textContent = '結果';
        } else if (JSON.stringify(headers) !== JSON.stringify(['区分','元','結果'])) {
          throw new Error('unknown other-counts contract');
        }
      }
      if (location.protocol === 'file:') {
        for (const a of fragment.content.querySelectorAll('a[href^="/portal/"]')) a.href = 'https://pakchee0529.github.io' + a.getAttribute('href');
      }
      for (const table of fragment.content.querySelectorAll('table')) {
        const wrap = el('div', undefined, 'table-wrap');
        wrap.tabIndex = 0;
        wrap.setAttribute('role', 'region');
        wrap.setAttribute('aria-label', '保存帳票の表');
        table.replaceWith(wrap); wrap.append(table);
      }
      section.append(fragment.content); list.append(section);
    }
    result.append(list);
  }
  function render() {
    if (!catalog) return;
    result.replaceChildren(); older.hidden = true;
    const query = new URL(location.href).searchParams;
    const design = query.get('design');
    const date = query.get('date') || ((!location.search || query.get('document') === 'instructions') ? document.body.dataset.initialDate : '');
    if (design !== null) {
      if (design === 'unregistered') {
        designInput.value = '';
        const cases = catalog.cases.filter(item => item.design_key === null);
        message.textContent = cases.length ? '未登録・形式未確認の番号は推測で補完していません。' : '検索対象内に、設計番号未登録の保存帳票はありません。';
        renderSnapshots(cases, '設計番号未登録・要確認');
      } else {
        designInput.value = design;
        const key = normalizeDesign(design);
        if (!key) { message.textContent = '設計番号は4桁で指定してください。先頭のB・全半角・空白は検索時に揃えます。'; return; }
        const cases = catalog.cases.filter(item => item.design_key === key);
        message.textContent = cases.length ? '' : '一致する保存帳票はありません。未登録の番号は推測していません。';
        renderSnapshots(cases, `設計番号 ${key}`);
      }
    } else if (date) {
      if (!/^\d{6}$/.test(date)) { message.textContent = '日付の形式を確認してください。'; return; }
      dayInput.value = `20${date.slice(0, 2)}-${date.slice(2, 4)}-${date.slice(4, 6)}`;
      const day = catalog.days.find(item => item.date === date);
      const cases = catalog.cases.filter(item => item.date === date);
      if (cases.length) { message.textContent = ''; renderSnapshots(cases, dateLabel(date)); }
      else if (day && day.completed === 0) { message.textContent = 'この日に完了した現場はありません。'; }
      else if (day) {
        message.textContent = 'この日の保存帳票の索引は未登録です。数量や設計番号は推測していません。';
        const a = el('a', '既存の保存資料を参照する', 'button secondary'); a.href = day.legacy_href; result.append(a);
      } else { message.textContent = catalog.unverified_dates?.includes(date) ? 'この日付の完了状況は確認できません。完了0件とは扱っていません。' : 'この日付の保存記録はありません。'; }
    } else { renderCards(); }
    if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
  }
  document.getElementById('filters').addEventListener('submit', event => {
    event.preventDefault(); route('design', designInput.value);
  });
  document.getElementById('date-open').addEventListener('click', () => {
    if (!dayInput.value) { message.textContent = '日付を選んでください。'; return; }
    route('date', dayInput.value.replaceAll('-', '').slice(2));
  });
  document.getElementById('reset').addEventListener('click', () => {
    if (location.protocol !== 'file:') { location.assign('/ippatsu-share-pages/portal/archive/'); return; }
    document.body.dataset.initialDate = ''; shown = 10; designInput.value = ''; route('', '');
  });
  document.getElementById('unregistered').addEventListener('click', () => route('design', 'unregistered'));
  older.addEventListener('click', () => { shown += 10; render(); });
  window.addEventListener('popstate', render);
  const embedded = document.getElementById('archive-snapshot-data');
  if (location.protocol === 'file:') document.querySelector('header a').href = 'https://pakchee0529.github.io/ippatsu-share-pages/portal/';
  const localSnapshot = () => {
    if (!embedded) throw new Error('snapshot unavailable');
    document.getElementById('scope-notice').textContent = 'この日付の単独保存版です。検索範囲は保存した日付内です。指示書リンクは同じ公開保存版を開きます。';
    return JSON.parse(embedded.textContent);
  };
  const load = location.protocol === 'file:' ? Promise.resolve().then(localSnapshot) :
    fetch('/ippatsu-share-pages/portal/archive/archive-v2-r1/catalog.json?v=' + encodeURIComponent(document.body.dataset.catalogVersion || ''), {cache: 'no-cache'})
      .then(response => { if (!response.ok) throw new Error('catalog'); return response.json(); });
  load
    .then(data => {
      if (data.schema !== 'public-archive-snapshots/v1' || !Array.isArray(data.days) || !Array.isArray(data.cases)) throw new Error('schema');
      if (data.cases.some(item => item.completion_status !== 'completed' || item.design_key !== normalizeDesign(item.design_original) || item.anchor !== `span-${item.date}-${item.management_no}-e${item.episode}-r${item.revision}`) || new Set(data.cases.map(item => item.anchor)).size !== data.cases.length) throw new Error('snapshot identity');
      if (location.protocol !== 'file:') {
        const missing = data.days.filter(day => day.completed > 0 && !day.available).length;
        const indexed = new Set(data.cases.map(item => item.date)).size;
        document.getElementById('scope-notice').textContent = `設計番号検索の対象：保存帳票を確認できた${indexed}日・${data.cases.length}径間。` + (missing ? ` その他${missing}日分は、日付から既存資料を確認できます。` : '');
      }
      catalog = data; render(); document.documentElement.dataset.archiveReady = 'true';
    })
    .catch(() => { message.textContent = '保存帳票の索引を読み込めません。時間をおいて再読込みしてください。'; });
})();
