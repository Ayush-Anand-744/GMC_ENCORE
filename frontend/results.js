const $ = s => {
  const el = document.querySelector(s);
  if (el) return el;
  const dummyCls = {
    add: () => {},
    remove: () => {},
    toggle: () => {},
    contains: () => false,
    replace: () => {}
  };
  return new Proxy({}, {
    get: (target, prop) => {
      if (prop === 'classList') return dummyCls;
      if (prop === 'style') return {};
      if (prop === 'dataset') return {};
      if (prop === 'addEventListener' || prop === 'removeEventListener') return () => {};
      if (prop === 'focus' || prop === 'blur' || prop === 'click') return () => {};
      if (prop === 'appendChild' || prop === 'removeChild' || prop === 'setAttribute' || prop === 'removeAttribute') return () => {};
      return undefined;
    },
    set: () => true
  });
};
let result = null;
let current = 'quote';
let rowFilter = 'all';

const caseId = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || '');

async function loadCase() {
  try {
    const r = await fetch(`/api/cases/${encodeURIComponent(caseId)}`);
    if (!r.ok) throw new Error(r.status === 404 ? 'This processed case is no longer available. The server may have restarted.' : 'Could not load processed data.');
    result = await r.json();
    renderFileChips(); renderPanel(); renderSummary();
  } catch (e) {
    const p = $('#panel'); if (p) p.innerHTML = `<div class="page-error"><b>Unable to load results.</b><p>${esc(e.message)}</p><a href="/">Return to upload</a></div>`;
    $('#summary')?.classList.add('hidden'); $('#downloads')?.classList.add('hidden');
  }
}

function renderFileChips() {
  const st = $('#sourceTabs');
  if (!st) return;
  st.innerHTML = (result?.classifications || []).map((x, i) => `
    <button class="file-chip ${i === 0 ? 'active' : ''}" type="button">
      <span class="file-chip-name">${esc(x.filename)}</span>
      <small>${esc(x.category === 'demography' ? 'Demography' : 'RFQ')}</small>
    </button>`).join('');
}

$('#mainTabs')?.addEventListener('click', e => {
  const b = e.target.closest('button[data-tab]'); if (!b) return;
  document.querySelectorAll('#mainTabs button').forEach(x => x?.classList.remove('active'));
  b?.classList.add('active'); current = b?.dataset.tab;
  const filterable = ['quote', 'hospital', 'additional'].includes(current);
  $('#tableFilterBar')?.classList.toggle('hidden', !filterable);
  renderPanel();
});

$('#tableFilterBar')?.addEventListener('click', e => {
  const b = e.target.closest('button[data-filter]'); if (!b) return;
  document.querySelectorAll('#tableFilterBar button').forEach(x => x?.classList.remove('active'));
  b?.classList.add('active'); rowFilter = b?.dataset.filter; renderPanel();
});

function isConflict(r) {
  return r?.valid_dropdown === false || Boolean(r?.unmatched_value) || Boolean(r?.uncertain) || Boolean(r?.conflict);
}

function effectiveStatus(r) {
  const field = String(r?.field || '');
  const source = String(r?.source_status || 'Not Available');
  // UI/status-label layer only. Extraction source status is intentionally left untouched.
  if (field === 'Organization Name' && source !== 'Not Available') return 'Derived';
  if (field === 'TPA' && source !== 'Not Available' && source !== 'Default Data') return 'Derived';
  if (source === 'RFQ Data') return isConflict(r) ? 'RFQ Data ❌' : 'RFQ Data ✅';
  if (source === 'Default Data') return 'Default Data';
  if (source === 'Derived') return (field === 'Organization Name' || field === 'TPA') ? 'Derived' : 'RFQ Data ✅';
  return 'Not Available';
}

function filteredRows(rows) {
  if (rowFilter === 'all') return rows || [];
  if (rowFilter === 'review') return (rows || []).filter(r => effectiveStatus(r) === 'Not Available');
  if (rowFilter === 'conflicts') return (rows || []).filter(r => effectiveStatus(r) === 'RFQ Data ❌' || isConflict(r));
  return rows || [];
}

function statusBadge(r) {
  const status = effectiveStatus(r);
  const cls = status === 'RFQ Data ✅' ? 'status-rfq-good' : status === 'RFQ Data ❌' ? 'status-rfq-bad' : status === 'Default Data' ? 'status-default' : status === 'Derived' ? 'status-derived' : 'status-na';
  return `<span class="status-tab ${cls}">${esc(status)}</span>`;
}

function confidenceBadge(r) {
  const status = effectiveStatus(r);
  const confidence = (status === 'RFQ Data ✅' || status === 'Default Data' || status === 'Default') ? 'High' : status === 'Derived' ? 'Medium' : status === 'RFQ Data ❌' ? 'Low' : 'Stable';
  const cls = confidence === 'High' ? 'conf-high' : confidence === 'Medium' ? 'conf-medium' : confidence === 'Low' ? 'conf-low' : 'conf-stable';
  return `<span class="confidence-badge ${cls}">${esc(confidence)}</span>`;
}

function renderPanel() {
  if (!result) return;
  const p = $('#panel');
  if (current === 'quote') return p.innerHTML = tableRows('Quote Form Filling Table', result.quote_rows || [], true);
  if (current === 'hospital') return p.innerHTML = tableRows('Hospitalization & Treatment Details', result.hospital_rows || [], false);
  if (current === 'additional') return p.innerHTML = tableRows('Additional Details', result.additional_rows || [], false);
  if (current === 'demo') return p.innerHTML = demoTable();
  if (current === 'demography-exception') return p.innerHTML = simpleTable('Demography Exception', result.demography_exceptions || result.validation_rows || [], 'Any exceptions or errors detected in Demography Data are shown here.');
  if (current === 'deviations') return p.innerHTML = simpleTable('Deviation / Cover Not Available', result.deviations || []);
  if (current === 'quote-exception') return p.innerHTML = simpleTable('Quote Exception', result.quote_exceptions || [], 'Any exceptions, unmatched values, or errors detected in Quote Data are shown here.');
  if (current === 'extracted') return p.innerHTML = simpleTable('Extracted Data', result.extracted_data || [], 'Complete parser-level extracted source data. This view is diagnostic and does not alter quote-field extraction.');
}

function tableRows(title, rows, showNotes) {
  const visible = filteredRows(rows);
  let last = '';
  let html = `<div class="table-title"><div><h3>${esc(title)}</h3><small>${visible.length} of ${(rows || []).length} fields shown</small></div><button class="download-table" type="button" data-kind="quote">↓ Download Table</button></div>`;
  if (!visible.length) return html + `<div class="empty-state">No fields match this filter.</div>`;
  html += `<div class="table-wrap quote-table-wrap"><table class="quote-table"><thead><tr><th>List of Category</th><th>RFQ / Customer Details</th><th>Proposed Details</th><th>Source Status</th><th>Confidence Level</th></tr></thead><tbody>`;
  visible.forEach(r => {
    if (r.section && r.section !== last) { html += `<tr class="section-row"><td colspan="5">${esc(r.section)}</td></tr>`; last = r.section; }
    html += `<tr class="${isConflict(r) ? 'conflict-row' : ''}"><td class="field-name">${esc(r.field)}</td><td>${esc(r.coverage_details ?? '')}</td><td>${esc(r.proposed_details ?? '')}</td><td>${statusBadge(r)}</td><td>${confidenceBadge(r)}</td></tr>`;
  });
  html += '</tbody></table></div>';
  if (showNotes && result.unmatched_notes?.length) html += `<div class="notes-stack">${result.unmatched_notes.map(n => `<div class="note">${esc(n)}</div>`).join('')}</div>`;
  return html;
}

function demoTable() {
  const rawRows = result.demography || [];
  const rows = rawRows.map(r => {
    const copy = { ...r };
    delete copy.Action; delete copy.action; delete copy.ACTION; delete copy['Action Required'];
    return copy;
  });
  const primary = rows.filter(r => ['self', 'employee'].includes(String(r.Relationship || '').toLowerCase())).length;
  return `<div class="table-title"><div><h3>Demographic Data (Bajaj Standard Template)</h3></div></div><div class="metrics demo-metrics"><div class="metric"><b>${rows.length}</b><small>Total Lives</small></div><div class="metric"><b>${primary}</b><small>Primary (Self)</small></div><div class="metric"><b>${rows.length - primary}</b><small>Dependents</small></div></div>${simpleTable('', rows)}`;
}

function simpleTable(title, rows, description = '', customClass = '') {
  const header = `${title ? `<div class="table-title"><div><h3>${esc(title)}</h3>${description ? `<small>${esc(description)}</small>` : ''}</div></div>` : ''}`;
  if (!rows || !rows.length) return header + `<div class="empty-state">No records.</div>`;
  const keys = Object.keys(rows[0]);
  const cls = customClass || (title ? title.toLowerCase().replace(/[^a-z0-9]+/g, '-') + '-table' : 'data-table');
  return `${header}<div class="table-wrap"><table class="data-table ${cls}"><thead><tr>${keys.map(k => `<th>${esc(k)}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${keys.map(k => `<td>${esc(r[k] ?? '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function renderSummary() {
  const s = result.summary || {};
  $('#summary').innerHTML = `<h3>Final Summary</h3><div class="metrics">${[
    ['Total Fields', s.total_fields ?? 0], ['Auto-Fill Rate', `${s.auto_fill_rate ?? 0}%`], ['Review Required', s.review_required ?? 0], ['Deviations', s.deviations ?? 0], ['Total Tokens', s.total_tokens ?? 0], ['Demo Lives', s.demo_lives ?? 0]
  ].map(([a, b]) => `<div class="metric"><b>${b}</b><small>${a}</small></div>`).join('')}</div><div class="readiness"><b>Extraction mode:</b> ${esc(result.extraction_mode || '')} &nbsp;|&nbsp; <b>Remark by:</b> ${esc(result.remark_by || '')}<br><br><b>Readiness:</b> ${(s.review_required || s.deviations) ? 'Needs review before submission' : 'Ready for submission'}<ul><li>Review ${s.review_required ?? 0} quote field(s) flagged for manual attention.</li><li>Confirm ${s.deviations ?? 0} deviation(s) and paste the UW remark if required.</li><li>Demography standardized: ${s.demo_lives ?? 0} lives, ${(result.demography_exceptions || result.validation_rows || []).length} exception(s) to review.</li></ul></div>`;
}

$('#downloads')?.addEventListener('click', e => {
  const b = e.target.closest('[data-kind]'); if (!b || !result?.case_id) return;
  location.href = `/api/cases/${encodeURIComponent(result.case_id)}/download/${encodeURIComponent(b.dataset.kind)}`;
});

$('#panel')?.addEventListener('click', e => {
  const b = e.target.closest('.download-table[data-kind]'); if (!b || !result?.case_id) return;
  location.href = `/api/cases/${encodeURIComponent(result.case_id)}/download/${encodeURIComponent(b.dataset.kind)}`;
});

function esc(v) { return String(v ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c])); }

loadCase();
