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
let files = [], scan = [], passwords = {};
const fileInput = $('#files'), drop = $('#drop');

function addFiles(newFiles) {
  const existingNames = new Set(files.map(f => f.name));
  for (const f of newFiles) {
    if (!existingNames.has(f.name)) {
      files.push(f);
    }
  }
  scanFiles();
}

drop?.addEventListener('dragover', e => e.preventDefault());
drop?.addEventListener('drop', e => {
  e.preventDefault();
  if (e.dataTransfer?.files?.length) {
    addFiles([...e.dataTransfer.files]);
  }
});

if (fileInput) {
  fileInput.onchange = () => {
    if (fileInput.files?.length) {
      addFiles([...fileInput.files]);
      fileInput.value = '';
    }
  };
}

const dateModeEl = $('#dateMode');
if (dateModeEl) dateModeEl.onchange = e => { const pd = $('#policyDate'); if (pd) pd.disabled = !e.target.checked; };

async function scanFiles() {
  if (!files.length) {
    scan = [];
    renderFiles();
    const st = $('#status'); if (st) st.textContent = '';
    return;
  }
  const fd = new FormData(); files.forEach(f => fd.append('files', f));
  const st = $('#status'); if (st) st.textContent = 'Inspecting files…';
  try {
    const r = await fetch('/api/scan', { method: 'POST', body: fd });
    if (!r.ok) throw new Error('File inspection failed.');
    scan = await r.json(); renderFiles(); if (st) st.textContent = `${files.length} file(s) ready.`;
  } catch (e) { const st2 = $('#status'); if (st2) st2.textContent = 'Could not inspect files: ' + e.message; }
}

function renderFiles() {
  const box = $('#fileList'); if (!box) return;
  box.innerHTML = '';
  scan.forEach((s, idx) => {
    const d = document.createElement('div'); d.className = 'file';
    d.innerHTML = `<b>${esc(s.filename)}</b><span class="pill">${esc(s.category)}</span><span class="pill">${fmt(s.size)}</span><span class="${s.locked ? 'lock' : ''}">${s.locked ? '🔒 Protected' : '✓ Ready'}</span><button type="button" class="remove-file-btn" data-index="${idx}" style="background:none;border:none;color:#94a3b8;font-size:16px;cursor:pointer;padding:0 6px;margin-left:auto;" title="Remove file">✕</button>`;
    box.appendChild(d);
  });
}

const fileListBox = $('#fileList');
if (fileListBox) {
  fileListBox.onclick = e => {
    const btn = e.target.closest('.remove-file-btn');
    if (!btn) return;
    const idx = parseInt(btn.dataset.index, 10);
    if (!isNaN(idx) && idx >= 0 && idx < files.length) {
      files.splice(idx, 1);
      scan.splice(idx, 1);
      renderFiles();
      const st = $('#status');
      if (st) st.textContent = files.length ? `${files.length} file(s) ready.` : '';
    }
  };
}

function fmt(n) { return n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(1)} MB`; }

const processBtn = $('#process');
if (processBtn) processBtn.onclick = async () => {
  if (!files.length) { alert('Upload at least one file.'); return; }
  if ($('#dateMode')?.checked && !$('#policyDate')?.value) { alert('Select a Policy Proposal Date.'); return; }
  for (const s of scan.filter(x => x.locked)) {
    if (!passwords[s.filename]) {
      const p = await askPassword(s.filename); if (p === null) return; passwords[s.filename] = p;
    }
  }
  await doProcess();
};

async function doProcess() {
  const fd = new FormData(); files.forEach(f => fd.append('files', f));
  fd.append('passwords_json', JSON.stringify(passwords));
  fd.append('use_policy_date', $('#dateMode')?.checked || false);
  fd.append('policy_date', $('#policyDate')?.value || '');
  const btn = $('#process'); if (btn) btn.disabled = true;
  const st = $('#status'); if (st) st.textContent = 'Processing RFQs…';
  try {
    const r = await fetch('/api/process', { method: 'POST', body: fd });
    const body = await r.json();
    if (!r.ok) {
      if ((r.status === 401 || r.status === 423) && body.detail?.locked_file) {
        delete passwords[body.detail.locked_file];
        const p = await askPassword(body.detail.locked_file, body.detail.message);
        if (p !== null) { passwords[body.detail.locked_file] = p; return doProcess(); }
      }
      throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
    }
    if (st) st.textContent = 'Processing complete. Opening processed RFQs data…';
    // Real same-tab page/route transition. Results are not rendered in place.
    window.location.assign(body.results_url || `/results/${body.case_id}`);
  } catch (e) {
    if (st) st.textContent = 'Error: ' + e.message;
    if (btn) btn.disabled = false;
  }
}

function askPassword(name, msg = 'Enter the password to continue.') {
  return new Promise(resolve => {
    const m = $('#modal'); m?.classList.remove('hidden');
    const mt = $('#modalText'); if (mt) mt.textContent = `${name} is password protected. ${msg}`;
    const pwd = $('#pwd'); if (pwd) pwd.value = '';
    const err = $('#pwdError'); if (err) err.textContent = '';
    setTimeout(() => $('#pwd')?.focus(), 50);
    const done = v => {
      m?.classList.add('hidden');
      const ok = $('#pwdOk'); if (ok) ok.onclick = null;
      const cancel = $('#pwdCancel'); if (cancel) cancel.onclick = null;
      resolve(v);
    };
    const ok = $('#pwdOk'); if (ok) ok.onclick = () => { const val = $('#pwd')?.value; if (!val) { const err2 = $('#pwdError'); if (err2) err2.textContent = 'Password is required.'; return; } done(val); };
    const cancel = $('#pwdCancel'); if (cancel) cancel.onclick = () => done(null);
  });
}

function esc(v) { return String(v ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c])); }
