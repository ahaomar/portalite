const $app = document.getElementById('app');

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function fmt(n) {
  return Number(n).toLocaleString();
}

// ---------- world map: low-res equirectangular land outlines ----------
// Generated from Natural Earth 110m (simplified). Coordinates [lon, lat].
const WORLD_LAND = [
  // north america (very simplified)
  [[-168,66],[-158,71],[-140,70],[-125,72],[-110,73],[-95,74],[-80,73],[-70,68],[-62,60],[-55,52],[-60,47],[-67,45],[-70,42],[-75,38],[-76,34],[-81,30],[-80,25],[-84,30],[-90,29],[-95,28],[-97,26],[-100,22],[-105,20],[-106,24],[-112,26],[-114,30],[-120,34],[-124,40],[-124,48],[-130,54],[-135,58],[-140,60],[-150,60],[-155,58],[-160,55],[-165,60],[-168,66]],
  // greenland
  [[-45,60],[-40,65],[-32,68],[-25,70],[-22,73],[-25,77],[-33,80],[-45,82],[-58,82],[-68,80],[-72,78],[-65,76],[-58,75],[-53,70],[-50,65],[-45,60]],
  // south america
  [[-78,8],[-75,10],[-70,12],[-63,11],[-58,7],[-52,5],[-50,0],[-44,-3],[-38,-6],[-35,-8],[-38,-13],[-40,-20],[-44,-24],[-48,-26],[-52,-30],[-56,-35],[-58,-39],[-64,-41],[-65,-46],[-69,-50],[-70,-54],[-74,-52],[-74,-46],[-74,-40],[-72,-34],[-71,-28],[-70,-20],[-75,-15],[-80,-6],[-81,-2],[-78,3],[-78,8]],
  // europe
  [[-9,43],[-9,38],[-6,36],[0,38],[3,42],[7,43],[10,44],[14,41],[16,38],[19,40],[21,37],[24,38],[26,40],[29,41],[34,45],[38,47],[40,44],[30,46],[28,44],[20,42],[16,42],[13,45],[8,44],[4,43],[0,43],[-2,46],[-4,48],[-2,50],[3,51],[8,54],[8,57],[12,56],[18,55],[21,56],[24,58],[28,60],[24,65],[20,69],[26,71],[30,70],[40,68],[42,62],[40,58],[35,56],[30,52],[24,51],[19,52],[15,54],[12,52],[9,50],[6,50],[2,49],[-2,49],[-4,44],[-9,43]],
  // africa
  [[-17,15],[-16,20],[-13,25],[-9,30],[-6,35],[0,36],[10,37],[12,34],[20,32],[25,32],[32,31],[35,28],[37,22],[40,15],[43,12],[48,11],[51,10],[45,2],[41,-2],[40,-8],[38,-14],[35,-20],[33,-26],[30,-30],[26,-34],[20,-35],[18,-33],[15,-27],[12,-18],[13,-12],[9,-1],[9,4],[4,6],[-4,5],[-8,4],[-13,8],[-17,15]],
  // asia
  [[35,36],[44,38],[50,37],[54,37],[57,40],[60,45],[58,52],[60,56],[70,55],[75,54],[80,55],[85,58],[90,56],[95,58],[100,58],[105,55],[110,52],[115,50],[120,50],[125,53],[130,55],[135,57],[140,60],[145,62],[150,60],[155,58],[160,60],[165,62],[170,64],[175,66],[180,66],[180,70],[170,70],[160,71],[150,72],[140,73],[130,72],[120,74],[110,74],[100,73],[90,74],[80,72],[70,72],[60,70],[50,68],[42,66],[36,64],[32,60],[30,55],[28,50],[30,45],[33,42],[35,36]],
  // india+southeast asia block
  [[62,25],[66,25],[70,22],[72,20],[74,15],[77,8],[80,10],[82,15],[87,21],[90,22],[92,20],[94,16],[98,12],[100,7],[102,2],[104,1],[105,10],[102,14],[100,18],[98,22],[95,25],[90,27],[85,25],[80,28],[75,30],[70,32],[66,30],[62,29],[58,26],[62,25]],
  // australia
  [[114,-22],[113,-26],[115,-32],[118,-35],[124,-33],[130,-32],[134,-33],[138,-35],[141,-38],[146,-39],[150,-37],[153,-32],[153,-27],[150,-22],[146,-19],[142,-13],[138,-16],[135,-12],[131,-12],[126,-14],[122,-17],[114,-22]],
  // japan
  [[130,32],[133,34],[136,35],[140,36],[141,40],[142,44],[145,44],[143,40],[141,38],[138,37],[134,34],[131,31],[130,32]],
  // uk
  [[-5,50],[-3,53],[-4,56],[-2,58],[-5,58],[-6,55],[-8,54],[-6,52],[-5,50]],
  // indonesia (sumatra/java/borneo simplified)
  [[95,5],[98,3],[102,-1],[106,-5],[110,-7],[114,-8],[112,-4],[108,0],[104,2],[100,3],[95,5]],
  [[109,0],[113,1],[117,4],[119,1],[116,-2],[112,-3],[109,0]],
  // madagascar
  [[43,-16],[47,-15],[50,-16],[49,-21],[46,-25],[44,-24],[43,-20],[43,-16]],
  // new zealand
  [[173,-35],[176,-38],[178,-38],[176,-41],[172,-44],[168,-46],[170,-43],[173,-40],[173,-35]],
];

function projectMap(points, width = 720, height = 360) {
  const x = (lon) => ((lon + 180) / 360) * width;
  const y = (lat) => ((90 - lat) / 180) * height;
  return { x, y, width, height };
}

function renderMap(container, points) {
  if (!points || !points.length) {
    container.innerHTML = '<div class="empty">No geographic data detected</div>';
    return;
  }
  const { x, y, width, height } = projectMap(points);
  let land = '';
  for (const poly of WORLD_LAND) {
    const pts = poly.map(([lon, lat]) => `${x(lon).toFixed(1)},${y(lat).toFixed(1)}`).join(' ');
    land += `<polygon class="map-land" points="${pts}"/>`;
  }
  const values = points.map((p) => p.value);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const dots = points.map((p) => {
    const t = max === min ? 0.7 : 0.3 + 0.7 * ((p.value - min) / (max - min));
    const r = 2.5 + 4 * t;
    return `<circle class="map-dot" cx="${x(p.lon).toFixed(1)}" cy="${y(p.lat).toFixed(1)}" r="${r.toFixed(1)}"><title>${esc(p.name || p.label || '')}: ${fmt(p.value)}</title></circle>`;
  }).join('');
  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="map">${land}${dots}</svg>
    <div class="map-legend">${points.length} locations · bubble size = value (${fmt(min)}–${fmt(max)})</div>`;
}

// ---------- charts ----------
function renderBars(container, data, label) {
  if (!data || !data.length) {
    container.innerHTML = '<div class="empty">No numeric column available for charting</div>';
    return;
  }
  const max = Math.max(...data.map((d) => d.value));
  container.innerHTML = data.map((d) => `
    <div class="bar-row" title="${esc(d.label)}: ${fmt(d.value)}">
      <span class="bar-label">${esc(d.label)}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${(d.value / max) * 100}%"></div></div>
      <span class="bar-value">${fmt(d.value)}</span>
    </div>`).join('');
}

// ---------- pages ----------
async function api(path) {
  let res;
  try {
    res = await fetch(path);
  } catch (e) {
    throw new Error('cannot reach the Portalite server — is it still running?');
  }
  const text = await res.text();
  let data = null;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`server returned a non-JSON response (HTTP ${res.status}) — check the server console`);
  }
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

async function homePage() {
  $app.innerHTML = '<div class="loading">Loading catalog…</div>';
  let stats, datasets;
  try {
    [stats, datasets] = await Promise.all([api('/api/stats'), api('/api/datasets')]);
  } catch (e) {
    $app.innerHTML = `<div class="empty">API error: ${esc(e.message)}</div>`;
    return;
  }

  const cards = datasets.map((d) => `
    <a class="card" href="/dataset/${esc(d.id)}">
      <h3>${esc(d.name)}</h3>
      <p>${esc(d.description || '')}</p>
      <div class="meta">
        <span class="pill">${fmt(d.row_count)} rows</span>
        <span class="pill">${d.schema.length} cols</span>
        <span class="pill">${esc(d.file_type)}</span>
        ${d.geo ? '<span class="pill geo">◈ geo</span>' : ''}
      </div>
    </a>`).join('');

  $app.innerHTML = `
    <div class="stats-row">
      <div class="stat"><span class="num">${stats.datasets}</span><span class="label">datasets</span></div>
      <div class="stat"><span class="num">${fmt(stats.rows)}</span><span class="label">rows</span></div>
      <div class="stat"><span class="num">${fmt(stats.columns)}</span><span class="label">columns</span></div>
      <div class="stat"><span class="num">${stats.geospatial}</span><span class="label">geospatial</span></div>
    </div>

    <section class="upload-box" id="upload">
      <h2>Add a dataset</h2>
      <p style="color:var(--muted);font-size:0.9rem">Drop a CSV, JSON or Excel file — schema, REST API, chart and map are generated automatically.</p>
      <input type="file" id="fileInput" accept=".csv,.json,.xlsx,.xls">
      <small>or drag &amp; drop · max 200MB</small>
      <div class="upload-status" id="uploadStatus"></div>
    </section>

    ${datasets.length ? `<div class="card-grid">${cards}</div>` : `
      <div class="empty"><span class="big">◈</span>No datasets yet — upload a CSV above or restart with sample data mounted.</div>`}
  `;

  const input = document.getElementById('fileInput');
  const status = document.getElementById('uploadStatus');
  const box = document.getElementById('upload');

  async function doUpload(file) {
    status.className = 'upload-status';
    status.textContent = `Ingesting ${file.name}…`;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/datasets', { method: 'POST', body: fd });
      const meta = await res.json();
      if (!res.ok) throw new Error(meta.detail || 'upload failed');
      status.className = 'upload-status ok';
      status.textContent = `✓ Ingested: ${meta.name} (${fmt(meta.row_count)} rows)`;
      setTimeout(() => homePage(), 900);
    } catch (e) {
      status.className = 'upload-status err';
      status.textContent = `✕ ${e.message}`;
    }
  }

  input.addEventListener('change', () => input.files[0] && doUpload(input.files[0]));
  ['dragover', 'dragenter'].forEach((ev) => box.addEventListener(ev, (e) => { e.preventDefault(); box.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach((ev) => box.addEventListener(ev, (e) => { e.preventDefault(); box.classList.remove('drag'); }));
  box.addEventListener('drop', (e) => e.dataTransfer.files[0] && doUpload(e.dataTransfer.files[0]));
}

let tableState = { offset: 0, limit: 25, sort: null, direction: 'asc', q: '' };

async function datasetPage(id) {
  $app.innerHTML = '<div class="loading">Loading dataset…</div>';
  let meta;
  try {
    meta = await api(`/api/datasets/${id}`);
  } catch {
    $app.innerHTML = '<div class="empty"><span class="big">404</span>Dataset not found</div>';
    return;
  }
  tableState = { offset: 0, limit: 25, sort: null, direction: 'asc', q: '' };

  $app.innerHTML = `
    <a class="back" href="/">← Catalog</a>
    <div class="dhead">
      <div>
        <h2>${esc(meta.name)}</h2>
        <div class="sub">${esc(meta.description || '')} · uploaded ${new Date(meta.uploaded_at).toLocaleDateString()}</div>
        <div class="meta" style="margin-top:0.5rem">
          <span class="pill">${fmt(meta.row_count)} rows</span>
          <span class="pill">${meta.schema.length} columns</span>
          <span class="pill">${esc(meta.file_type)} file</span>
          ${meta.geo ? `<span class="pill geo">◈ ${esc(meta.geo.kind)}</span>` : ''}
        </div>
      </div>
      <div>
        <button onclick="deleteDataset('${esc(meta.id)}')" style="padding:6px 12px;border:1px solid var(--border);background:var(--panel);border-radius:6px;cursor:pointer;color:#cf222e">Delete</button>
      </div>
    </div>

    <div class="panel">
      <h2>Data preview</h2>
      <div class="search-row">
        <input id="searchInput" placeholder="Search all columns…" value="${esc(tableState.q)}">
        <button onclick="doSearch('${esc(meta.id)}')" style="padding:8px 16px;border:1px solid var(--border);background:var(--accent);color:#fff;border-radius:8px;cursor:pointer">Search</button>
      </div>
      <div style="overflow-x:auto"><table id="dataTable"></table></div>
      <div class="pager">
        <span id="pageInfo"></span>
        <button id="prevBtn">← Prev</button>
        <button id="nextBtn">Next →</button>
      </div>
    </div>

    <div class="viz-grid">
      <div class="panel">
        <h2>Distribution</h2>
        <div id="chartBox"></div>
      </div>
      <div class="panel map-panel">
        <h2>Geography</h2>
        <div id="mapBox"></div>
      </div>
    </div>
  `;

  document.getElementById('searchInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doSearch(meta.id);
  });
  document.getElementById('prevBtn').addEventListener('click', () => {
    tableState.offset = Math.max(0, tableState.offset - tableState.limit);
    loadTable(meta);
  });
  document.getElementById('nextBtn').addEventListener('click', () => {
    tableState.offset += tableState.limit;
    loadTable(meta);
  });

  loadTable(meta);
  loadVisualizations(meta);
}

async function loadTable(meta) {
  try {
    const params = new URLSearchParams({
      limit: tableState.limit, offset: tableState.offset,
    });
    if (tableState.sort) { params.set('sort', tableState.sort); params.set('direction', tableState.direction); }
    if (tableState.q) params.set('q', tableState.q);
    const data = await api(`/api/datasets/${meta.id}/rows?${params}`);
    const table = document.getElementById('dataTable');
    const visibleCols = meta.schema.filter((c) => !c.name.startsWith('__'));

    const head = visibleCols.map((c) =>
      `<th data-col="${esc(c.name)}">${esc(c.name)}<span class="type-tag">${c.type}</span></th>`
    ).join('');
    const body = data.rows.map((row) =>
      `<tr>${visibleCols.map((c) => `<td>${esc(row[c.name])}</td>`).join('')}</tr>`
    ).join('');
    table.innerHTML = `<thead><tr>${head}</tr></thead><tbody>${body || '<tr><td colspan="99" class="empty">No rows match</td></tr>'}</tbody>`;

    table.querySelectorAll('th').forEach((th) => th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (tableState.sort === col) {
        tableState.direction = tableState.direction === 'asc' ? 'desc' : 'asc';
      } else {
        tableState.sort = col;
        tableState.direction = 'asc';
      }
      tableState.offset = 0;
      loadTable(meta);
    }));

    const start = tableState.offset + 1;
    const end = tableState.offset + data.rows.length;
    document.getElementById('pageInfo').textContent = data.rows.length ? `${start}–${end}` : '0';
    document.getElementById('prevBtn').disabled = tableState.offset === 0;
    document.getElementById('nextBtn').disabled = data.rows.length < tableState.limit;
  } catch (e) {
    document.getElementById('dataTable').innerHTML =
      `<tr><td class="empty">Could not load rows: ${esc(e.message)}</td></tr>`;
  }
}

function doSearch(id) {
  tableState.q = document.getElementById('searchInput').value.trim();
  tableState.offset = 0;
  api(`/api/datasets/${id}`).then((meta) => loadTable(meta));
}

async function loadVisualizations(meta) {
  const chartBox = document.getElementById('chartBox');
  const mapBox = document.getElementById('mapBox');

  const cols = meta.schema.filter((c) => !c.name.startsWith('__'));
  const numericCols = cols.filter((c) => c.type === 'integer' || c.type === 'number');
  const stringCols = cols.filter((c) => c.type === 'string');
  const isTimeLike = (name) => /(^|_)(year|date|time|month|period)/i.test(name);

  const chartGroup = stringCols.length ? stringCols[0].name : null;
  const chartValue = numericCols.find((c) => !isTimeLike(c.name) && c.name !== chartGroup);

  if (chartGroup) {
    try {
      let url = `/api/datasets/${meta.id}/aggregate?group=${encodeURIComponent(chartGroup)}&limit=10`;
      if (chartValue) {
        url += `&value=${encodeURIComponent(chartValue.name)}&agg=sum`;
      }
      const data = await api(url);
      const label = chartValue ? `sum of ${chartValue.name} by ${chartGroup}` : `rows by ${chartGroup}`;
      renderBars(chartBox, data, label);
    } catch (e) {
      chartBox.innerHTML = `<div class="empty">Chart unavailable: ${esc(e.message)}</div>`;
    }
  } else {
    chartBox.innerHTML = '<div class="empty">No suitable columns for charting</div>';
  }

  if (meta.geo) {
    try {
      const geoValue = numericCols.find((c) => !isTimeLike(c.name) && c.name !== chartGroup);
      let url = `/api/datasets/${meta.id}/map`;
      if (geoValue) url += `?value=${encodeURIComponent(geoValue.name)}&agg=sum`;
      const points = await api(url);
      renderMap(mapBox, points);
    } catch (e) {
      mapBox.innerHTML = `<div class="empty">Map unavailable: ${esc(e.message)}</div>`;
    }
  } else {
    mapBox.innerHTML = '<div class="empty">No geographic columns detected — include country codes, country names, or lat/lon to enable maps</div>';
  }
}

async function deleteDataset(id) {
  if (!confirm('Delete this dataset and its API?')) return;
  await fetch(`/api/datasets/${id}`, { method: 'DELETE' });
  location.href = '/';
}

// ---------- router ----------
function route() {
  const m = location.pathname.match(/^\/dataset\/([\w-]+)/);
  if (m) datasetPage(m[1]);
  else homePage();
}
window.addEventListener('popstate', route);
route();
