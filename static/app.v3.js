/* AI 接口测试 Agent —— 前端逻辑（原生 JS，无框架） */
const state = {
  token: localStorage.getItem('token') || '',
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  projects: [],
  projectId: null,
  tab: 'cases',
  runFilter: null,
  runId: null,
};

const currentRole = () => {
  const p = state.projects.find((x) => x.id === state.projectId);
  return p ? p.role : null;
};
const canWrite = () => ['admin', 'tester'].includes(currentRole());
const isAdmin = () => currentRole() === 'admin';

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};
function openModal(html) {
  const mask = el('div', 'modal-mask');
  mask.innerHTML = `<div class="modal">${html}</div>`;
  document.body.appendChild(mask);
  mask.close = () => mask.remove();
  return mask;
}

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

if (!state.token) location.href = '/login';

async function api(path, opts = {}) {
  const resp = await fetch(path, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + state.token,
      ...(opts.headers || {}),
    },
  });
  if (resp.status === 401) { localStorage.removeItem('token'); location.href = '/login'; }
  const text = await resp.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
  if (!resp.ok) throw new Error((data && data.detail) || resp.statusText);
  return data;
}

/* ---------------- 顶栏：项目选择 + 导航 ---------------- */
function renderProjects() {
  const sel = $('#projectSelect');
  if (!sel) return;
  sel.innerHTML = '';
  if (!state.projects.length) {
    sel.innerHTML = '<option>没有项目</option>';
    return;
  }
  state.projects.forEach((p) => {
    const o = document.createElement('option');
    o.value = String(p.id);
    o.textContent = `${p.name}（${p.endpoint_count} 接口 · ${p.role}）`;
    if (p.id === state.projectId) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = () => {
    state.projectId = Number(sel.value);
    if (!state.tab || state.tab === 'profile') state.tab = 'cases';
    state.runId = null;
    renderAll();
  };
}

function renderTabs() {
  const box = $('#tabs');
  if (!box) return;
  box.innerHTML = '';
  if (!state.projectId) return;
  const tabs = [['cases', '接口与用例'], ['run', '执行与报告'], ['issues', '缺陷'], ['stats', '统计']];
  if (isAdmin()) tabs.push(['members', '成员'], ['audit', '审计']);
  tabs.forEach(([k, label]) => {
    const b = el('button', 'navitem' + (state.tab === k ? ' active' : ''), label);
    b.onclick = () => { state.tab = k; renderAll(); };
    box.appendChild(b);
  });
}

/* ---------------- 用例视图 ---------------- */
async function viewCases() {
  const main = $('#main');
  main.innerHTML = '';
  const pid = state.projectId;

  const head = el('div', 'card');
  head.innerHTML = `<div class="row">
      <h2 style="margin:0">接口与用例</h2>
      <span class="muted" id="epMeta"></span>
      <span class="spacer" style="flex:1"></span>
      <button id="btnImport">从服务地址导入</button>
      <button id="btnUpload">上传 spec 文件</button>
      <button id="btnGen" class="primary">生成用例</button>
      <input type="file" id="specFile" accept=".json,.yaml,.yml" style="display:none">
    </div>
    <div class="row" style="margin-top:10px">
      <span class="muted">被测服务：<code id="baseUrlText">-</code></span>
      <button id="btnEditBase" class="ghost">修改地址</button>
      <button id="btnLogin" class="btn-ghost" title="仅当被测服务打开就需要输口令时才用（如本站示例项目一）">🔑 服务有口令？</button>
      <button id="btnHeaders" class="ghost">设置请求头</button>
      <span class="muted" id="headerHint"></span>
    </div>
    <p class="muted" style="margin:8px 0 0;line-height:1.8">
      <b>默认流程</b>：直接点「从服务地址导入」→「生成用例」→「执行」，大多数服务不需要任何鉴权配置。<br>
      <b>上传 spec</b>：服务没暴露文档、或文档被登录拦住时，直接把 JSON/YAML 文件传进来。<br>
      <b>🔑 服务有口令？</b>：只有当打开服务就要输密码时（比如本站的示例项目一）才用，Agent 会帮你登录拿 Cookie。<br>
      <b>设置请求头</b>：需要固定 API-Key 或已有 Cookie 时手工填。
    </p>`;
  main.appendChild(head);

  const quick = el('details', 'card');
  quick.innerHTML = `<summary style="cursor:pointer;font-weight:600">
      没有 OpenAPI？粘贴一条 cURL，或上传 Postman 集合 →</summary>
    <p class="muted" style="margin:8px 0">贴一条你平时用的 curl，系统会立刻建好接口，并生成 2 条可直接执行的用例（不依赖模型）。</p>
    <details style="margin-bottom:8px">
      <summary class="muted" style="cursor:pointer">cURL 从哪来？点开看三种方式</summary>
      <ul class="muted" style="line-height:1.9;margin:6px 0 0 18px">
        <li><b>浏览器 F12</b>：Network → 找到请求 → 右键 → Copy → Copy as cURL</li>
        <li><b>Postman</b>：选中请求 → 右侧 Code 按钮 → 选 cURL → 复制</li>
        <li><b>接口文档</b>：Swagger 页面「Try it out」执行后，浏览器 F12 里也能复制</li>
      </ul>
    </details>
    <textarea id="curlText" rows="4" spellcheck="false"
      placeholder='curl -X POST http://127.0.0.1:9000/users -H "Authorization: Bearer mock-token" -H "Content-Type: application/json" -d {"email":"a@b.c","name":"x"}'
      style="width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font-family:ui-monospace,Consolas,monospace;font-size:12px"></textarea>
    <div class="row" style="margin-top:8px">
      <button id="btnCurl" class="primary">导入这条 cURL</button>
      <button id="btnPm">上传 Postman 集合</button>
      <input type="file" id="pmFile" accept=".json" style="display:none">
    </div>`;
  main.appendChild(quick);

  const table = el('div', 'card');
  table.innerHTML = '<p class="muted">加载中…</p>';
  main.appendChild(table);

  quick.querySelector('#btnCurl').onclick = async (ev) => {
    const btn = ev.target;
    const curl = quick.querySelector('#curlText').value.trim();
    if (!curl) return alert('先粘贴一条 curl');
    btn.disabled = true; btn.textContent = '导入中…';
    try {
      const r = await api(`/api/projects/${pid}/import/curl`, {
        method: 'POST', body: JSON.stringify({ curl }),
      });
      alert(`已导入 ${r.endpoint.method} ${r.endpoint.path}\n生成用例 ${r.cases} 条\n服务地址已设为 ${r.base_url}\n下一步：点「执行与报告」跑一下`);
      renderAll();
    } catch (e) { alert('导入失败：\n' + e.message); }
    finally { btn.disabled = false; btn.textContent = '导入这条 cURL'; }
  };

  quick.querySelector('#btnPm').onclick = () => quick.querySelector('#pmFile').click();
  quick.querySelector('#pmFile').onchange = async (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    const text = await file.text();
    try {
      const r = await api(`/api/projects/${pid}/import/postman`, {
        method: 'POST', body: JSON.stringify({ spec_text: text }),
      });
      alert(`导入 ${r.endpoints} 个请求（新建 ${r.created} 个接口）`);
      renderAll();
    } catch (e) { alert('导入失败：\n' + e.message); }
  };

  if (!canWrite()) {
    head.querySelector('#btnImport').disabled = true;
    head.querySelector('#btnGen').disabled = true;
    head.querySelector('#btnGen').textContent = '只读不可生成';
  }

  head.querySelector('#btnImport').onclick = async (ev) => {
    const btn = ev.target;
    btn.disabled = true; btn.textContent = '导入中…';
    try {
      const r = await api(`/api/projects/${pid}/import`, { method: 'POST', body: JSON.stringify({}) });
      alert(`导入成功：${r.endpoints} 个接口\n下一步：点「生成用例」`);
      renderAll();
    } catch (e) {
      alert('导入失败：\n' + e.message);
    } finally { btn.disabled = false; btn.textContent = '导入 OpenAPI'; }
  };
  head.querySelector('#btnEditBase').onclick = async () => {
    const next = prompt('被测服务的根地址（OpenAPI 所在服务）', state.projectBase || '');
    if (!next) return;
    try {
      await api(`/api/projects/${pid}`, { method: 'PATCH', body: JSON.stringify({ base_url: next }) });
      alert('地址已更新');
      renderAll();
    } catch (e) { alert('修改失败：' + e.message); }
  };

  head.querySelector('#btnLogin').onclick = async (ev) => {
    const btn = ev.target;
    const pwd = prompt('输入被测服务的访问口令（会 POST 到 ' + (state.projectBase || '') + '/login）');
    if (!pwd) return;
    btn.disabled = true; btn.textContent = '登录中…';
    try {
      const r = await api(`/api/projects/${pid}/login`, {
        method: 'POST', body: JSON.stringify({ password: pwd }),
      });
      alert(`登录成功，已保存 Cookie：${r.cookie_names}\n下一步点「从服务地址导入」，之后的测试请求都会自动带上登录态。`);
    } catch (e) { alert('登录失败：\n' + e.message); }
    finally { btn.disabled = false; btn.textContent = '用口令登录'; }
  };

  head.querySelector('#btnHeaders').onclick = async () => {
    const cur = state.projectHeaders || {};
    const text = prompt(
      '输入 JSON 形式的请求头（会加到每个请求上）\n例如：{"Cookie": "access_token=xxx"} 或 {"X-API-Key": "k"}',
      JSON.stringify(cur, null, 0)
    );
    if (text === null) return;
    let parsed;
    try { parsed = text.trim() ? JSON.parse(text) : {}; }
    catch (e) { return alert('不是合法 JSON'); }
    try {
      await api(`/api/projects/${pid}`, { method: 'PATCH', body: JSON.stringify({ custom_headers: parsed }) });
      state.projectHeaders = parsed;
      head.querySelector('#headerHint').textContent = Object.keys(parsed).length ? `已设置 ${Object.keys(parsed).length} 个请求头` : '';
      alert('请求头已保存');
    } catch (e) { alert('保存失败：' + e.message); }
  };

  head.querySelector('#btnUpload').onclick = () => head.querySelector('#specFile').click();
  head.querySelector('#specFile').onchange = async (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    const text = await file.text();
    const btn = head.querySelector('#btnUpload');
    btn.disabled = true; btn.textContent = '解析中…';
    try {
      const r = await api(`/api/projects/${pid}/import`, {
        method: 'POST', body: JSON.stringify({ spec_text: text }),
      });
      alert(`导入成功：${r.endpoints} 个接口`);
      renderAll();
    } catch (e) { alert('导入失败：\n' + e.message); }
    finally { btn.disabled = false; btn.textContent = '上传 spec 文件'; }
  };

  head.querySelector('#btnGen').onclick = async (ev) => {
    const btn = ev.target;
    const old = btn.textContent;
    btn.disabled = true; btn.textContent = '生成中…（约 30~60 秒）';
    try {
      const r = await api(`/api/projects/${pid}/generate`, { method: 'POST', body: JSON.stringify({ only_missing: true }) });
      alert(`生成完成：新增 ${r.added} 条\n接口 ${r.endpoints} 个，已有用例跳过 ${r.skipped} 个，失败 ${r.failed} 个`);
      renderAll();
    } catch (e) {
      alert('生成失败：\n' + e.message);
    } finally { btn.disabled = false; btn.textContent = old; }
  };

  const [eps, cases] = await Promise.all([
    api(`/api/projects/${pid}/endpoints`),
    api(`/api/projects/${pid}/cases`),
  ]);
  head.querySelector('#epMeta').textContent = `${eps.length} 个接口 · ${cases.length} 条用例`;
  head.querySelector('#baseUrlText').textContent = state.projectBase || '-';

  if (!eps.length) {
    table.innerHTML = `<h3 style="margin-top:0">这个项目还没有接口，按三步开始</h3>
      <ol style="line-height:2;margin:8px 0 0 18px">
        <li>点右上角「<b>导入 OpenAPI</b>」把接口文档拉进来（会去 ${esc(state.projectBase || '你的 base_url')} 取）</li>
        <li>点「<b>生成用例</b>」让模型给每个接口出题</li>
        <li>去「<b>执行与报告</b>」点「运行全部用例」，看结果和归因</li>
      </ol>
      <p class="muted" style="margin-top:12px">提示：导入前请确认被测服务已经启动。</p>`;
    return;
  }

  const byEp = new Map(eps.map((e) => [e.id, []]));
  cases.forEach((c) => { if (byEp.has(c.endpoint_id)) byEp.get(c.endpoint_id).push(c); });

  const tbl = document.createElement('table');
  tbl.innerHTML = '<thead><tr><th style="width:90px">方法</th><th>路径</th><th style="width:70px">用例</th><th>用例明细</th></tr></thead>';
  const tbody = document.createElement('tbody');
  eps.forEach((ep) => {
    const tr = document.createElement('tr');
    const list = byEp.get(ep.id) || [];
    const detail = list.map((c) => {
      const tag = c.enabled ? 'ok' : 'dim';
      return `<label style="display:block;margin:2px 0">
        <input type="checkbox" ${c.enabled ? 'checked' : ''} data-case="${c.id}">
        <span class="tag ${tag}" style="margin-left:4px">${esc(c.dimension)}</span>
        <span style="margin-left:6px">${esc(c.name)}</span></label>`;
    }).join('') || '<span class="muted">暂无</span>';

    tr.innerHTML = `<td><span class="tag dim">${esc(ep.method)}</span></td>
      <td><code>${esc(ep.path)}</code><div class="muted">${esc(ep.summary || '')}</div></td>
      <td>${list.length}</td>
      <td>${detail}</td>`;
    tr.querySelectorAll('[data-case]').forEach((cb) => {
      if (!canWrite()) { cb.disabled = true; }
      cb.onchange = async () => {
        try {
          await api(`/api/cases/${cb.dataset.case}`, { method: 'PATCH', body: JSON.stringify({ enabled: cb.checked }) });
        } catch (e) { cb.checked = !cb.checked; alert(e.message); }
      };
    });
    tbody.appendChild(tr);
  });
  tbl.appendChild(tbody);
  table.innerHTML = '';
  table.appendChild(tbl);
}

/* ---------------- 执行视图 ---------------- */
function renderRunSummary(run) {
  const pct = run.total ? Math.round((run.passed / run.total) * 100) : 0;
  const f = state.runFilter;
  const card = (key, label, value, color) => `
    <div class="metric clickable ${f === key ? 'metric-active' : ''}" data-filter="${key}">
      <div class="muted">${label}</div>
      <div class="v" ${color ? `style="color:${color}"` : ''}>${value}</div>
    </div>`;
  return `<div class="cards">
      ${card('all', '用例总数', run.total)}
      ${card('passed', '通过', run.passed, 'var(--ok)')}
      ${card('failed', '失败', run.failed, 'var(--bad)')}
      <div class="metric"><div class="muted">通过率</div><div class="v">${pct}%</div></div>
      <div class="metric"><div class="muted">耗时</div><div class="v">${run.duration_ms || 0}ms</div></div>
    </div>`;
}

async function viewRun() {
  const main = $('#main');
  main.innerHTML = '';
  const pid = state.projectId;

  const head = el('div', 'card');
  head.innerHTML = `<div class="row"><h2 style="margin:0">执行与报告</h2>
    <span class="muted" id="runStatus"></span><span style="flex:1"></span>
    <button id="btnRun" class="primary">运行全部用例</button></div>
    <div class="progress" style="margin-top:12px"><i id="bar"></i></div>`;
  main.appendChild(head);
  const body = el('div');
  main.appendChild(body);

  if (!canWrite()) {
    head.querySelector('#btnRun').disabled = true;
    head.querySelector('#btnRun').textContent = '只读不可执行';
  }
  head.querySelector('#btnRun').onclick = async (ev) => {
    const btn = ev.target;
    btn.disabled = true;
    try {
      const r = await api('/api/runs', { method: 'POST', body: JSON.stringify({ project_id: pid }) });
      state.runId = r.run_id;
      state.runFilter = 'failed';   // 刚跑完，直接看失败
      await watchRun(r.run_id);
    } catch (e) { alert('启动失败：' + e.message); }
    finally { btn.disabled = false; }
  };

  if (state.runId) {
    await watchRun(state.runId);
  } else {
    // 没有当前跑批时，自动加载最近一次
    try {
      const runs = await api(`/api/projects/${pid}/runs`);
      if (runs.length) {
        state.runId = runs[0].id;
        await watchRun(runs[0].id);
      } else {
        body.innerHTML = '<div class="card"><p class="muted">还没有跑批记录，点右上角「运行全部用例」。</p></div>';
      }
    } catch (e) {
      body.innerHTML = `<div class="card"><p class="muted">加载跑批记录失败：${esc(e.message)}</p></div>`;
    }
  }
}

async function watchRun(runId) {
  const statusEl = $('#runStatus');
  const bar = $('#bar');
  const body = $('#main').lastElementChild;
  statusEl.textContent = '运行中…';

  // 优先用 SSE 实时进度；失败则退回轮询
  try {
    const resp = await fetch(`/api/runs/${runId}/stream`, {
      headers: { 'Authorization': 'Bearer ' + state.token },
    });
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split('\n\n');
      buf = parts.pop();
      for (const part of parts) {
        if (!part.startsWith('data: ')) continue;
        const data = JSON.parse(part.slice(6));
        statusEl.textContent = `${data.status} · ${data.passed}/${data.total}`;
        bar.style.width = (data.total ? (data.passed + data.failed) / data.total * 100 : 0) + '%';
        if (['done', 'awaiting_confirm', 'failed'].includes(data.status)) { buf = ''; }
      }
    }
  } catch (e) { /* 退回轮询 */ }

  const run = await api(`/api/runs/${runId}`);
  statusEl.textContent = `状态：${run.status}`;
  bar.style.width = '100%';
  const paint = () => {
    body.innerHTML = renderRunSummary(run);
    if (state.runFilter) {
      body.insertAdjacentHTML('beforeend', renderItems(run.items, state.runFilter));
    } else {
      body.insertAdjacentHTML(
        'beforeend',
        '<div class="card"><p class="empty">点上面的「用例总数 / 通过 / 失败」查看明细</p></div>'
      );
    }
    body.querySelectorAll('[data-filter]').forEach((c) => {
      c.onclick = () => {
        state.runFilter = state.runFilter === c.dataset.filter ? null : c.dataset.filter;
        paint();
      };
    });
  };
  paint();
}

function renderItems(items, filter) {
  const match = (i) => {
    if (!filter || filter === 'all') return true;
    if (filter === 'passed') return i.status === 'passed';
    if (filter === 'failed') return i.status !== 'passed';
    return i.verdict === filter;
  };
  const rows = items.filter(match);
  if (!rows.length) return '<div class="card"><p class="empty">没有符合条件的用例</p></div>';

  const trs = rows.map((i) => {
    const checks = ((i.assert_detail || {}).checks || [])
      .map((c) => `<div>${esc(c.name)}：期望 ${esc(c.expected)}，实际 ${esc(c.actual)} ${c.ok ? '✅' : '❌'}</div>`)
      .join('');
    const verdictTag = i.verdict
      ? `<span class="tag ${i.verdict === 'bug' ? 'bad' : 'warn'}">${esc(i.verdict)}</span>`
      : '';
    return `<tr>
      <td><span class="tag ${i.status === 'passed' ? 'ok' : 'bad'}">${i.status}</span></td>
      <td><code>${esc(i.method)} ${esc(i.path)}</code><div class="muted">${esc(i.case_name)}</div></td>
      <td>${i.resp_status}<div class="muted">${i.elapsed_ms}ms</div></td>
      <td>${verdictTag}<div class="muted">${esc(i.verdict_reason || '')}</div></td>
      <td><details><summary>看证据</summary><div>${checks}</div>
          <pre>${esc(JSON.stringify(i.request, null, 2))}</pre>
          <pre>${esc((i.resp_body || '').slice(0, 800))}</pre></details></td>
    </tr>`;
  }).join('');

  const titles = {
    all: '全部用例', passed: '通过的用例', failed: '失败的用例',
    bug: '判定为 bug 的用例（真问题）', case_error: '归因「用例写错」的失败',
  };
  return `<div class="card"><h3>${titles[filter] || '用例'}（${rows.length}）</h3>
    <table><thead><tr><th style="width:80px">状态</th><th>接口 / 用例</th><th style="width:90px">响应</th><th style="width:180px">归因</th><th style="width:90px">证据</th></tr></thead>
    <tbody>${trs}</tbody></table></div>`;
}

/* ---------------- 缺陷视图 ---------------- */
async function viewIssues() {
  const main = $('#main');
  main.innerHTML = '';
  const pid = state.projectId;
  const data = await api(`/api/projects/${pid}/issues`);

  const card = el('div', 'card');
  const drafts = data.filter((i) => i.status === 'draft');
  const submitted = data.filter((i) => i.status === 'submitted');

  card.innerHTML = `<div class="row"><h2 style="margin:0">缺陷</h2>
      <span class="muted">草稿 ${drafts.length} · 已提交 ${submitted.length}</span>
      <span style="flex:1"></span>
      <button id="btnConfirm" class="primary" ${drafts.length ? '' : 'disabled'}>确认提交选中缺陷</button>
    </div>
    <p class="muted">缺陷由「失败 + 归因为 bug」自动生成，提交前需人工确认（人机协同）。</p>`;

  const rows = data.map((i) => `<tr>
      <td>${i.status === 'draft' ? `<input type="checkbox" data-issue="${i.id}">` : '—'}</td>
      <td><span class="tag ${i.severity === 'high' ? 'bad' : 'warn'}">${esc(i.severity)}</span>
          <span class="tag ${i.status === 'draft' ? 'warn' : 'ok'}">${esc(i.status)}</span></td>
      <td>${esc(i.title)}<div class="muted">${esc(i.method)} <code>${esc(i.path)}</code></div></td>
      <td>期望 ${esc(i.expected)}<div class="muted">实际 ${esc(i.actual)}</div></td>
      <td><details><summary>复现</summary><pre>${esc(i.curl)}</pre><pre>${esc(i.steps)}</pre></details></td>
    </tr>`).join('');
  card.insertAdjacentHTML('beforeend',
    data.length ? `<table><thead><tr><th style="width:40px"></th><th style="width:120px">级别/状态</th><th>标题</th><th>期望/实际</th><th>复现</th></tr></thead><tbody>${rows}</tbody></table>`
                : '<p class="empty">还没有缺陷</p>');

  main.appendChild(card);

  const btn = card.querySelector('#btnConfirm');
  if (btn && !canWrite()) { btn.disabled = true; btn.textContent = '只读不可提交'; }
  if (btn) btn.onclick = async () => {
    const ids = [...card.querySelectorAll('[data-issue]:checked')].map((c) => Number(c.dataset.issue));
    if (!ids.length) return alert('请先勾选要提交的缺陷');
    btn.disabled = true;
    try {
      const r = await api('/api/issues/confirm', { method: 'POST', body: JSON.stringify({ issue_ids: ids }) });
      alert(`已提交 ${r.submitted} 条缺陷`);
      renderAll();
    } catch (e) { alert(e.message); btn.disabled = false; }
  };
}

/* ---------------- 统计视图 ---------------- */
async function viewStats() {
  const main = $('#main');
  const pid = state.projectId;
  const s = await api(`/api/projects/${pid}/stats`);

  const card = (label, value, color, goto, hint, filter) => `
    <div class="metric ${goto ? 'clickable' : ''}" ${goto ? `data-goto="${goto}"` : ''} ${filter ? `data-filter="${filter}"` : ''}>
      <div class="muted">${label}</div>
      <div class="v" ${color ? `style="color:${color}"` : ''}>${value}</div>
      ${hint ? `<div class="muted" style="font-size:12px;margin-top:6px">${hint}</div>` : ''}
    </div>`;

  main.innerHTML = `<div class="card"><h2 style="margin-top:0">统计</h2>
    <p class="muted">带箭头的卡片可以点，会跳到对应页面。</p>
    <div class="cards">
      ${card('接口数', s.endpoints, '', 'cases', '→ 接口与用例', '')}
      ${card('用例覆盖率', s.coverage + '%', '', 'cases', '→ 看哪些接口没用例', '')}
      ${card('跑批次数', s.runs, '', 'run', '→ 执行与报告', '')}
      ${card('执行用例', s.cases_executed, '', 'run', '→ 全部用例', 'all')}
      ${card('通过率', s.pass_rate + '%', '', 'run', '→ 看通过的', 'passed')}
      ${card('检出的 bug', s.bugs, 'var(--bad)', 'issues', '→ 看缺陷', '')}
      ${card('用例误报', s.false_positive, 'var(--warn)', 'run', '→ 只看用例写错的', 'case_error')}
      <div class="metric"><div class="muted">平均耗时</div><div class="v">${s.avg_duration_ms}ms</div></div>
    </div>
    <p class="muted">「检出的 bug」= 归因为 bug 的缺陷数；「用例误报」= 归因为用例写错的失败数。</p></div>`;

  main.querySelectorAll('[data-goto]').forEach((c) => {
    c.onclick = () => {
      state.tab = c.dataset.goto;
      state.runFilter = c.dataset.filter || null;   // 由统计卡片决定进页面后看哪一类
      renderAll();
    };
  });
}

/* ---------------- 成员（仅 admin） ---------------- */
async function viewMembers() {
  const main = $('#main');
  const pid = state.projectId;
  const members = await api(`/api/projects/${pid}/members`);

  const roleName = (r) => (r === 'admin' ? '管理员' : r === 'tester' ? '测试' : '只读');
  const rows = members.map((m) => `<tr>
      <td>${esc(m.name)}</td>
      <td>${esc(m.email)}</td>
      <td>
        <select data-uid="${m.user_id}" class="role-select">
          ${['admin', 'tester', 'viewer'].map((r) =>
            `<option value="${r}" ${r === m.role ? 'selected' : ''}>${roleName(r)}（${r}）</option>`).join('')}
        </select>
      </td>
      <td><button class="ghost" data-remove="${m.user_id}">移除</button></td>
    </tr>`).join('');

  main.innerHTML = `<div class="card">
      <h2 style="margin-top:0">成员管理</h2>
      <p class="muted">只有管理员能改成员角色。角色决定这个人能看到什么、能做什么。</p>
      <div class="row" style="margin:12px 0">
        <input id="newEmail" placeholder="要添加的邮箱（需已注册）" style="flex:1;padding:8px;border:1px solid var(--line);border-radius:8px">
        <select id="newRole" class="role-select">
          <option value="tester">测试（tester）</option>
          <option value="viewer">只读（viewer）</option>
          <option value="admin">管理员（admin）</option>
        </select>
        <button id="btnAddMember" class="primary">添加成员</button>
      </div>
      <table><thead><tr><th>姓名</th><th>邮箱</th><th style="width:200px">角色</th><th style="width:100px">操作</th></tr></thead>
      <tbody>${rows}</tbody></table>
    </div>
    <div class="card">
      <h3>三个角色分别能做什么</h3>
      <table>
        <thead><tr><th>能力</th><th>只读 viewer</th><th>测试 tester</th><th>管理员 admin</th></tr></thead>
        <tbody>
          <tr><td>看接口 / 用例 / 报告</td><td>✅</td><td>✅</td><td>✅</td></tr>
          <tr><td>导入 OpenAPI / 生成用例</td><td>❌</td><td>✅</td><td>✅</td></tr>
          <tr><td>执行跑批</td><td>❌</td><td>✅</td><td>✅</td></tr>
          <tr><td>提交缺陷</td><td>❌</td><td>✅</td><td>✅</td></tr>
          <tr><td>管理成员</td><td>❌</td><td>❌</td><td>✅</td></tr>
          <tr><td>看审计日志</td><td>❌</td><td>❌</td><td>✅</td></tr>
        </tbody>
      </table>
    </div>`;

  main.querySelectorAll('[data-uid]').forEach((sel) => {
    sel.onchange = async () => {
      try {
        await api(`/api/projects/${pid}/members/${sel.dataset.uid}`, {
          method: 'PATCH', body: JSON.stringify({ email: '', role: sel.value }),
        });
        alert('角色已更新');
        renderAll();
      } catch (e) { alert(e.message); renderAll(); }
    };
  });
  main.querySelectorAll('[data-remove]').forEach((btn) => {
    btn.onclick = async () => {
      if (!confirm('确定移除这个成员？')) return;
      try {
        await api(`/api/projects/${pid}/members/${btn.dataset.remove}`, { method: 'DELETE' });
        renderAll();
      } catch (e) { alert(e.message); }
    };
  });
  const add = main.querySelector('#btnAddMember');
  add.onclick = async () => {
    const email = main.querySelector('#newEmail').value.trim();
    if (!email) return alert('请输入邮箱');
    try {
      await api(`/api/projects/${pid}/members`, {
        method: 'POST',
        body: JSON.stringify({ email, role: main.querySelector('#newRole').value }),
      });
      alert('已加入项目');
      renderAll();
    } catch (e) { alert(e.message); }
  };
}

/* ---------------- 审计（仅 admin） ---------------- */
async function viewAudit() {
  const main = $('#main');
  const pid = state.projectId;
  const logs = await api(`/api/projects/${pid}/audit`);
  const rows = logs.map((l) => `<tr>
      <td>${esc((l.at || '').replace('T', ' ').slice(0, 19))}</td>
      <td>${esc(l.actor)}</td>
      <td><span class="tag dim">${esc(l.action)}</span></td>
      <td>${esc(l.target || '')}</td>
      <td>${esc(l.detail || '')}</td>
    </tr>`).join('');
  main.innerHTML = `<div class="card"><h2 style="margin-top:0">审计日志</h2>
    <p class="muted">谁、在什么时候、做了什么，全部留痕。只有管理员能看。</p>
    ${logs.length ? `<table><thead><tr><th style="width:170px">时间</th><th style="width:100px">操作人</th><th style="width:150px">动作</th><th>对象</th><th>详情</th></tr></thead><tbody>${rows}</tbody></table>` : '<p class="empty">暂无日志</p>'}
    </div>`;
}

/* ---------------- 个人中心 ---------------- */
function saveAvatarDataUrl(dataUrl) {
  return api('/api/me', { method: 'PATCH', body: JSON.stringify({ avatar: dataUrl }) })
    .then(async () => {
      state.me = { ...state.me, avatar: dataUrl };
      renderUser();
      await viewProfile();
    })
    .catch((e) => alert('上传失败：' + e.message));
}

async function openCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('当前浏览器不支持调用摄像头（需要 https 或 localhost）。已改为选择图片文件。');
    return null;
  }
  const mask = openModal(`
    <h3>拍照</h3>
    <p class="muted">预览画面正常后点「拍照」。</p>
    <video id="camVideo" class="cam-video" autoplay playsinline muted></video>
    <div class="row" style="justify-content:flex-end;margin-top:12px">
      <button id="camCancel" class="btn-ghost">取消</button>
      <button id="camShot" class="primary" disabled>拍照</button>
    </div>`);

  const video = mask.querySelector('#camVideo');
  const shotBtn = mask.querySelector('#camShot');
  let stream = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    });
    video.srcObject = stream;
    shotBtn.disabled = false;
  } catch (e) {
    mask.close();
    const tips = {
      NotAllowedError: '你拒绝了摄像头权限',
      NotFoundError: '没有检测到摄像头',
      NotReadableError: '摄像头被其他程序占用',
    };
    alert((tips[e.name] || ('打不开摄像头：' + e.name)) + '。已改为选择图片文件。');
    return null;
  }

  const stop = () => { if (stream) stream.getTracks().forEach((t) => t.stop()); };
  mask.querySelector('#camCancel').onclick = () => { stop(); mask.close(); };

  return new Promise((resolve) => {
    shotBtn.onclick = () => {
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
      stop();
      mask.close();
      resolve(dataUrl);
    };
  });
}

async function viewProfile() {
  const main = $('#main');
  const me = await api('/api/me');
  state.me = me;
  const r = currentRole();
  const roleText = me.is_admin ? '系统管理员'
    : r === 'admin' ? '项目管理员' : r === 'tester' ? '测试' : r === 'viewer' ? '只读' : '—';
  const hasPic = me.avatar && me.avatar.length > 4;
  const avatarHtml = hasPic
    ? `<img src="${esc(me.avatar)}" alt="">`
    : esc((me.name || '?').slice(0, 1));

  main.innerHTML = `
    <div class="card">
      <div class="profile-head">
        <button class="profile-avatar" id="avatarBtn" title="点击更换头像">${avatarHtml}</button>
        <div>
          <h2 style="margin:0">${esc(me.name)}</h2>
          <div class="muted">${esc(me.email)} · ${roleText}</div>
          <div class="muted">已加入 ${(me.projects || []).length} 个项目</div>
        </div>
      </div>
      <p class="muted" style="margin:12px 0 0">点击头像可拍照或从相册选择。</p>
    </div>

    <div class="card">
      <h3>基本资料</h3>
      <div class="form-row">
        <div class="form-item"><label>昵称</label><input id="pfName" value="${esc(me.name)}"></div>
        <div class="form-item"><label>公司邮箱（不可修改）</label><input value="${esc(me.email)}" disabled></div>
      </div>
      <div class="row" style="justify-content:flex-end">
        <button class="primary" id="pfSave">保存资料</button>
      </div>
    </div>

    <div class="card">
      <h3>修改密码</h3>
      <div class="form-row">
        <div class="form-item"><label>原密码</label>
          <div class="pw-wrap"><input id="pwOld" type="password"><button class="pw-eye" data-eye="pwOld">👁</button></div></div>
        <div class="form-item"><label>新密码（至少 6 位）</label>
          <div class="pw-wrap"><input id="pwNew" type="password"><button class="pw-eye" data-eye="pwNew">👁</button></div></div>
        <div class="form-item"><label>确认新密码</label>
          <div class="pw-wrap"><input id="pwNew2" type="password"><button class="pw-eye" data-eye="pwNew2">👁</button></div></div>
      </div>
      <div class="row" style="justify-content:flex-end"><button class="primary" id="pwSave">修改密码</button></div>
    </div>

    <div class="card">
      <h3>账号</h3>
      <p class="muted">退出后需要重新登录。演示账号默认口令：demo1234。</p>
      <button id="pfLogout" class="btn-ghost">退出登录</button>
    </div>

    <input type="file" id="camInput" accept="image/*" capture="user" style="display:none">
    <input type="file" id="galInput" accept="image/*" style="display:none">`;

  // ---------- 头像：拍照 / 相册 ----------
  const pickAvatar = () => {
    const mask = openModal(`
      <h3>更换头像</h3>
      <p class="muted">选择来源，图片会自动压缩到 256×256。</p>
      <div class="row" style="margin-top:14px">
        <button id="avCam" class="primary" style="flex:1">📷 拍照</button>
        <button id="avGal" style="flex:1">🖼 从相册选择</button>
      </div>
      <div class="row" style="justify-content:flex-end;margin-top:12px">
        <button id="avCancel" class="btn-ghost">取消</button>
      </div>`);
    mask.querySelector('#avCancel').onclick = () => mask.close();
    mask.querySelector('#avCam').onclick = async () => {
      mask.close();
      const dataUrl = await openCamera();
      if (dataUrl) saveAvatarDataUrl(dataUrl);
      else main.querySelector('#camInput').click();   // 没相机就退回选文件
    };
    mask.querySelector('#avGal').onclick = () => {
      mask.close();
      main.querySelector('#galInput').click();
    };
  };

  const handleFile = (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) return alert('请选择图片文件');
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = async () => {
        const size = 256;
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        const side = Math.min(img.width, img.height);
        ctx.drawImage(img, (img.width - side) / 2, (img.height - side) / 2, side, side, 0, 0, size, size);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
        try {
          await api('/api/me', { method: 'PATCH', body: JSON.stringify({ avatar: dataUrl }) });
          state.me = { ...state.me, avatar: dataUrl };
          renderUser();
          await viewProfile();
        } catch (e) { alert('上传失败：' + e.message); }
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  };

  main.querySelector('#avatarBtn').onclick = pickAvatar;
  main.querySelector('#camInput').onchange = (e) => handleFile(e.target.files[0]);
  main.querySelector('#galInput').onchange = (e) => handleFile(e.target.files[0]);

  // ---------- 基本资料 ----------
  main.querySelector('#pfSave').onclick = async (ev) => {
    const btn = ev.target;
    btn.disabled = true;
    try {
      const body = { name: main.querySelector('#pfName').value.trim() };
      const res = await api('/api/me', { method: 'PATCH', body: JSON.stringify(body) });
      state.me = { ...state.me, ...res };
      renderUser();
      await viewProfile();
      alert('已保存');
    } catch (e) { alert('保存失败：' + e.message); }
    finally { btn.disabled = false; }
  };

  // ---------- 改密码 ----------
  main.querySelector('#pwSave').onclick = async (ev) => {
    const oldP = main.querySelector('#pwOld').value;
    const n1 = main.querySelector('#pwNew').value;
    const n2 = main.querySelector('#pwNew2').value;
    if (!oldP || !n1) return alert('请填写原密码和新密码');
    if (n1 !== n2) return alert('两次输入的新密码不一致');
    const btn = ev.target;
    btn.disabled = true;
    try {
      await api('/api/me/password', { method: 'POST', body: JSON.stringify({ old_password: oldP, new_password: n1 }) });
      alert('密码已修改，请重新登录');
      localStorage.clear();
      location.href = '/login';
    } catch (e) { alert('修改失败：' + e.message); }
    finally { btn.disabled = false; }
  };

  main.querySelectorAll('[data-eye]').forEach((btn) => {
    btn.onclick = () => {
      const input = main.querySelector('#' + btn.dataset.eye);
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.textContent = show ? '🙈' : '👁';
    };
  });

  main.querySelector('#pfLogout').onclick = () => { localStorage.clear(); location.href = '/login'; };
}

/* ---------------- 路由 ---------------- */
async function renderAll() {
  renderProjects();
  renderTabs();
  const cur = state.projects.find((p) => p.id === state.projectId);
  state.projectBase = cur ? cur.base_url : '';
  if (state.tab === 'profile') { await viewProfile(); return; }
  if (!state.projectId) {
    $('#main').innerHTML = '<div class="card"><p class="muted">还没有项目。管理员可以点上方「+ 新建项目」。</p></div>';
    return;
  }
  try {
    // 非管理员不能停在管理员页面
    if (['members', 'audit'].includes(state.tab) && !isAdmin()) state.tab = 'cases';
    if (state.tab === 'cases') await viewCases();
    else if (state.tab === 'run') await viewRun();
    else if (state.tab === 'issues') await viewIssues();
    else if (state.tab === 'members') await viewMembers();
    else if (state.tab === 'audit') await viewAudit();
    else await viewStats();
  } catch (e) {
    $('#main').innerHTML = `<div class="card"><p style="color:var(--bad)">加载失败：${esc(e.message)}</p></div>`;
  }
}

function renderUser() {
  const me = state.me || state.user || {};
  const name = me.name || '';
  const avatar = me.avatar || '';
  const box = $('#avatar');
  if (box) {
    if (avatar && /^https?:\/\//.test(avatar)) {
      box.innerHTML = `<img src="${esc(avatar)}" alt="">`;
    } else {
      box.textContent = avatar || (name ? name.slice(0, 1) : '?');
    }
  }
  const r = currentRole();
  const roleText = me.is_admin ? '系统管理员' : r === 'admin' ? '管理员' : r === 'tester' ? '测试' : r === 'viewer' ? '只读' : '';
  $('#who').textContent = name + (roleText ? ' · ' + roleText : '');
  $('#ddName').textContent = name;
  $('#ddEmail').textContent = me.email || '';
}

function openNewProject() {
  const mask = openModal(`
    <h3>新建项目</h3>
    <p class="muted">一个项目 = 一套被测服务。填它的根地址，Agent 会自己去找到接口文档。</p>
    <label>项目名称<input id="npName" value="我的被测服务"></label>
    <label>服务地址（根地址，不含 /api 之类的路径）
      <input id="npBase" value="http://127.0.0.1:8000"></label>
    <p class="muted" style="margin:6px 0 0">例：本地 Spring/Flask 是 <code>http://localhost:8080</code>，线上是 <code>https://xxx.com</code></p>
    <p class="muted" id="npProbe" style="min-height:18px"></p>
    <div class="row" style="justify-content:flex-end;margin-top:10px">
      <button id="npProbeBtn">检测地址</button>
      <button id="npCancel" class="btn-ghost">取消</button>
      <button id="npOk" class="primary">创建</button>
    </div>`);

  const q = (id) => mask.querySelector('#' + id);
  q('npCancel').onclick = () => mask.close();
  q('npProbeBtn').onclick = async () => {
    const base = q('npBase').value.trim();
    q('npProbe').textContent = '检测中…';
    try {
      const r = await api('/api/probe', { method: 'POST', body: JSON.stringify({ base_url: base }) });
      q('npProbe').textContent = r.found
        ? `✅ 找到文档：${r.found}（${r.paths_count} 个路径）`
        : '❌ 没找到 OpenAPI 文档。可以创建后用「粘贴 cURL」或「上传 spec 文件」接入。';
    } catch (e) { q('npProbe').textContent = '检测失败：' + e.message; }
  };
  q('npOk').onclick = async () => {
    const name = q('npName').value.trim();
    const base = q('npBase').value.trim();
    if (!name || !base) return alert('名称和地址都要填');
    try {
      const r = await api('/api/projects', { method: 'POST', body: JSON.stringify({ name, base_url: base }) });
      mask.close();
      state.projectId = r.id;
      state.tab = 'cases';
      await loadProjects();
      await renderAll();
    } catch (e) { alert(e.message); }
  };
}

function openProjectSettings() {
  const p = state.projects.find((x) => x.id === state.projectId);
  if (!p) return alert('先选一个项目');
  const canAdmin = p.role === 'admin';
  const mask = openModal(`
    <h3>项目设置</h3>
    <label>项目名称<input id="psName" value="${esc(p.name)}" ${canAdmin ? '' : 'disabled'}></label>
    <label>服务地址<input id="psBase" value="${esc(p.base_url || '')}" ${canAdmin ? '' : 'disabled'}></label>
    <label>环境
      <select id="psEnv" ${canAdmin ? '' : 'disabled'}>
        <option value="test" ${p.env === 'test' ? 'selected' : ''}>测试环境（允许写操作）</option>
        <option value="prod" ${p.env === 'prod' ? 'selected' : ''}>生产环境（只读，禁止跑批）</option>
      </select>
    </label>
    <div class="row" style="justify-content:space-between;margin-top:16px">
      <button id="psDelete" class="btn-ghost" style="color:var(--bad);border-color:#fbd5d6" ${canAdmin ? '' : 'disabled'}>删除项目</button>
      <div class="row">
        <button id="psCancel" class="btn-ghost">取消</button>
        <button id="psSave" class="primary" ${canAdmin ? '' : 'disabled'}>保存</button>
      </div>
    </div>`);

  const q = (id) => mask.querySelector('#' + id);
  q('psCancel').onclick = () => mask.close();
  q('psSave').onclick = async () => {
    try {
      await api(`/api/projects/${p.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: q('psName').value.trim(),
          base_url: q('psBase').value.trim(),
          env: q('psEnv').value,
        }),
      });
      mask.close();
      await loadProjects();
      await renderAll();
    } catch (e) { alert('保存失败：' + e.message); }
  };
  q('psDelete').onclick = async () => {
    if (!confirm(`删除项目「${p.name}」？\n接口、用例、跑批、缺陷会一起删除，不可恢复。`)) return;
    try {
      await api(`/api/projects/${p.id}`, { method: 'DELETE' });
      mask.close();
      state.projectId = null;
      await loadProjects();
      if (state.projects.length) state.projectId = state.projects[0].id;
      state.tab = 'cases';
      await renderAll();
    } catch (e) { alert('删除失败：' + e.message); }
  };
}

async function init() {
  document.title = 'AI 接口测试 Agent · build ' + (window.__BUILD__ || '?');
  try {
    state.me = await api('/api/me');
    state.isAdminUser = !!state.me.is_admin;
  } catch (e) {
    state.me = state.user;
    state.isAdminUser = false;
  }

  const dd = $('#userDropdown');
  $('#userBtn').onclick = (e) => { e.stopPropagation(); dd.classList.toggle('open'); };
  document.addEventListener('click', () => dd.classList.remove('open'));
  dd.querySelector('[data-menu="logout"]').onclick = () => { localStorage.clear(); location.href = '/login'; };
  dd.querySelector('[data-menu="profile"]').onclick = () => {
    state.tab = 'profile'; dd.classList.remove('open'); renderAll();
  };

  $('#newProject').onclick = () => openNewProject();
  $('#projectSettings').onclick = () => openProjectSettings();
  if (!state.isAdminUser) $('#newProject').style.display = 'none';

  await loadProjects();
  renderUser();
  if (state.projects.length && !state.projectId) state.projectId = state.projects[0].id;
  await renderAll();
}

async function loadProjects() {
  state.projects = await api('/api/projects');
  if (state.me) state.isAdminUser = !!state.me.is_admin;
  renderUser();
}

init();
