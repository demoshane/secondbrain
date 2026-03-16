// Second Brain GUI — ES module
const API = 'http://127.0.0.1:37491';
let currentPath = null;
let easyMDE = null;
let brainPath = null;
let isDirty = false;

// --- Sidebar collapse state ---
function getCollapseState() {
    try {
        return JSON.parse(localStorage.getItem('sb-sidebar-collapse') || '{}');
    } catch (_) {
        return {};
    }
}

function setCollapseState(key, collapsed) {
    try {
        const state = getCollapseState();
        state[key] = collapsed;
        localStorage.setItem('sb-sidebar-collapse', JSON.stringify(state));
    } catch (_) {}
}

// Extract top-level folder name from an absolute note path
function folderName(notePath) {
    const parts = notePath.split('/');
    // parts[-1] = filename, parts[-2] = folder; fallback 'other' if flat
    return parts.length >= 2 ? (parts[parts.length - 2] || 'other') : 'other';
}

// --- Sidebar ---
async function loadNotes() {
    const res = await fetch(`${API}/notes`);
    const { notes } = await res.json();
    // Derive brain_path from the first note path (strip deepest components)
    if (notes.length && !brainPath) {
        const parts = notes[0].path.split('/');
        // Heuristic: brain root is 2 levels up from note path
        brainPath = parts.slice(0, -2).join('/') || '/';
    }
    renderHierarchySidebar(notes);
}

// Flat list used by search results and tag-filter mode
function renderFlatList(notes) {
    const list = document.getElementById('note-list');
    list.innerHTML = '';
    // Group by type (same as original renderSidebar behavior)
    const groups = {};
    for (const n of notes) {
        const t = n.type || 'other';
        if (!groups[t]) groups[t] = [];
        groups[t].push(n);
    }
    for (const [type, items] of Object.entries(groups).sort()) {
        const hdr = document.createElement('li');
        hdr.className = 'type-group-header';
        hdr.textContent = type;
        list.appendChild(hdr);
        for (const n of items) {
            const li = document.createElement('li');
            li.dataset.path = n.path;
            li.innerHTML = `<div>${n.title || n.path.split('/').pop()}</div>`;
            li.addEventListener('click', () => openNote(n.path));
            list.appendChild(li);
        }
    }
    document.getElementById('sidebar-loading').style.display = 'none';
}

// Hierarchy sidebar: Recent section + folder > type grouping
function renderHierarchySidebar(notes) {
    const list = document.getElementById('note-list');
    list.innerHTML = '';
    const collapseState = getCollapseState();

    // Helper: create a note <li>
    function makeNoteLi(n) {
        const li = document.createElement('li');
        li.dataset.path = n.path;
        li.innerHTML = `<div>${n.title || n.path.split('/').pop()}</div>`;
        li.addEventListener('click', () => openNote(n.path));
        return li;
    }

    // Helper: create a collapsible section wrapper <li>
    function makeSection(key, headerText, noteItems, extraClass) {
        const isCollapsed = collapseState[key] === true;

        const section = document.createElement('li');
        section.className = `folder-section${extraClass ? ' ' + extraClass : ''}${isCollapsed ? ' collapsed' : ''}`;
        section.dataset.folder = key;

        const hdr = document.createElement('div');
        hdr.className = 'folder-header';
        hdr.innerHTML = `<span class="collapse-toggle">${isCollapsed ? '▶' : '▼'}</span> ${headerText}`;
        hdr.addEventListener('click', () => {
            const nowCollapsed = !section.classList.contains('collapsed');
            section.classList.toggle('collapsed', nowCollapsed);
            hdr.querySelector('.collapse-toggle').textContent = nowCollapsed ? '▶' : '▼';
            setCollapseState(key, nowCollapsed);
        });
        section.appendChild(hdr);

        const ul = document.createElement('ul');
        ul.className = 'folder-notes';
        for (const n of noteItems) ul.appendChild(makeNoteLi(n));
        section.appendChild(ul);

        return section;
    }

    // Helper: create a type-within-folder sub-section
    function makeTypeSection(folderKey, typeName, noteItems) {
        const typeKey = `${folderKey}::${typeName}`;
        const isCollapsed = collapseState[typeKey] === true;

        const section = document.createElement('li');
        section.className = `type-section${isCollapsed ? ' collapsed' : ''}`;
        section.dataset.typeKey = typeKey;

        const hdr = document.createElement('div');
        hdr.className = 'type-header';
        hdr.innerHTML = `<span class="collapse-toggle">${isCollapsed ? '▶' : '▼'}</span> ${typeName} <span class="section-count">(${noteItems.length})</span>`;
        hdr.addEventListener('click', () => {
            const nowCollapsed = !section.classList.contains('collapsed');
            section.classList.toggle('collapsed', nowCollapsed);
            hdr.querySelector('.collapse-toggle').textContent = nowCollapsed ? '▶' : '▼';
            setCollapseState(typeKey, nowCollapsed);
        });
        section.appendChild(hdr);

        const ul = document.createElement('ul');
        ul.className = 'type-notes';
        for (const n of noteItems) ul.appendChild(makeNoteLi(n));
        section.appendChild(ul);

        return section;
    }

    // 1. Recent section — first 10 notes (server returns created_at DESC)
    const recentNotes = notes.slice(0, 10);
    const recentSection = makeSection('recent', `Recent <span class="section-count">(${recentNotes.length})</span>`, recentNotes, 'recent-section');
    list.appendChild(recentSection);

    // 2. Build folder > type map
    const folderMap = {}; // { folderName: { typeName: [notes] } }
    for (const n of notes) {
        const folder = folderName(n.path);
        const type = n.type || 'other';
        if (!folderMap[folder]) folderMap[folder] = {};
        if (!folderMap[folder][type]) folderMap[folder][type] = [];
        folderMap[folder][type].push(n);
    }

    // 3. Render each folder section
    for (const [folder, typeMap] of Object.entries(folderMap).sort()) {
        const totalCount = Object.values(typeMap).reduce((sum, arr) => sum + arr.length, 0);
        const isCollapsed = collapseState[folder] === true;

        const folderSection = document.createElement('li');
        folderSection.className = `folder-section${isCollapsed ? ' collapsed' : ''}`;
        folderSection.dataset.folder = folder;

        const folderHdr = document.createElement('div');
        folderHdr.className = 'folder-header';
        folderHdr.innerHTML = `<span class="collapse-toggle">${isCollapsed ? '▶' : '▼'}</span> ${folder}/ <span class="section-count">(${totalCount})</span>`;
        folderHdr.addEventListener('click', () => {
            const nowCollapsed = !folderSection.classList.contains('collapsed');
            folderSection.classList.toggle('collapsed', nowCollapsed);
            folderHdr.querySelector('.collapse-toggle').textContent = nowCollapsed ? '▶' : '▼';
            setCollapseState(folder, nowCollapsed);
        });
        folderSection.appendChild(folderHdr);

        const typesUl = document.createElement('ul');
        typesUl.className = 'folder-types';

        for (const [typeName, noteItems] of Object.entries(typeMap).sort()) {
            typesUl.appendChild(makeTypeSection(folder, typeName, noteItems));
        }

        folderSection.appendChild(typesUl);
        list.appendChild(folderSection);
    }

    document.getElementById('sidebar-loading').style.display = 'none';
}

// --- Note viewer ---
async function openNote(path) {
    currentPath = path;
    // Mark active
    document.querySelectorAll('#note-list li[data-path]').forEach(el => {
        el.classList.toggle('active', el.dataset.path === path);
    });
    exitEditMode();
    const res = await fetch(`${API}/notes/${encodeURIComponent(path)}`);
    if (!res.ok) { document.getElementById('viewer').innerHTML = '<em>Error loading note.</em>'; return; }
    const { body } = await res.json();
    renderMarkdown(body);
    loadMeta(path);
    loadActions();
    loadIntelligence();
    document.getElementById('open-editor-btn').onclick = () => {
        if (window.pywebview) pywebview.api.open_in_editor(path);
    };
}

function renderMarkdown(md) {
    // EasyMDE bundles marked — use it directly
    const viewer = document.getElementById('viewer');
    if (md == null) { viewer.innerHTML = '<em>Note body missing — restart the server and reload.</em>'; viewer.style.display = ''; return; }
    if (typeof marked !== 'undefined') {
        viewer.innerHTML = marked.parse(md);
    } else {
        viewer.textContent = md;
    }
    viewer.style.display = '';
    document.getElementById('editor-area').style.display = 'none';
    document.getElementById('save-btn').style.display = 'none';
    document.getElementById('edit-btn').style.display = '';
}

// --- Delete button reference ---
const deleteBtn = document.getElementById('delete-btn');

// --- Edit mode ---
document.getElementById('edit-btn').addEventListener('click', enterEditMode);
document.getElementById('save-btn').addEventListener('click', saveNote);

async function enterEditMode() {
    if (!currentPath) return;
    const res = await fetch(`${API}/notes/${encodeURIComponent(currentPath)}?raw=true`);
    const { content } = await res.json();
    document.getElementById('viewer').style.display = 'none';
    const ta = document.getElementById('editor-area');
    ta.style.display = '';
    if (easyMDE) { easyMDE.toTextArea(); easyMDE = null; }
    easyMDE = new EasyMDE({
        element: ta,
        initialValue: content,
        autosave: { enabled: false },
        spellChecker: false,
        toolbar: ['bold','italic','heading','|','preview','side-by-side','|','guide'],
    });
    isDirty = false;
    easyMDE.codemirror.on('change', () => { isDirty = true; });
    document.getElementById('save-btn').style.display = '';
    document.getElementById('edit-btn').style.display = 'none';
    deleteBtn.style.display = 'none';
    // Ctrl+S / Cmd+S to save
    document.addEventListener('keydown', handleSaveKey);
}

function handleSaveKey(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); saveNote(); }
}

function exitEditMode() {
    document.removeEventListener('keydown', handleSaveKey);
    if (easyMDE) { easyMDE.toTextArea(); easyMDE = null; }
    document.getElementById('editor-area').style.display = 'none';
    document.getElementById('save-btn').style.display = 'none';
    document.getElementById('edit-btn').style.display = '';
    deleteBtn.style.display = '';
}

async function saveNote() {
    if (!currentPath || !easyMDE) return;
    const md = easyMDE.value();
    const res = await fetch(`${API}/notes/${encodeURIComponent(currentPath)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: md }),
    });
    if (res.ok) {
        isDirty = false;
        exitEditMode();
        await loadNotes();
        document.querySelectorAll('#note-list li[data-path]').forEach(el => {
            el.classList.toggle('active', el.dataset.path === currentPath);
        });
        renderMarkdown(md);
    } else {
        const errSpan = document.getElementById('save-error');
        if (errSpan) { errSpan.textContent = 'Save failed.'; errSpan.style.display = ''; }
    }
}

// --- Search ---
let searchTimer = null;
document.getElementById('search-input').addEventListener('input', e => {
    clearTimeout(searchTimer);
    const q = e.target.value.trim();
    if (!q) { loadNotes(); return; }
    searchTimer = setTimeout(() => runSearch(q), 300);
});

async function runSearch(query) {
    const mode = document.getElementById('search-mode').value;
    const res = await fetch(`${API}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode }),
    });
    const { results } = await res.json();
    renderFlatList(results.map(r => ({ path: r.path || r, title: r.title || r, type: r.type || 'result' })));
}

// --- Right panel: meta ---
async function loadMeta(path) {
    const res = await fetch(`${API}/notes/${encodeURIComponent(path)}/meta`);
    if (!res.ok) return;
    const { backlinks, related } = await res.json();
    const bl = document.getElementById('backlinks-list');
    bl.innerHTML = backlinks.map(n => `<li data-path="${n.path}">${n.title || n.path}</li>`).join('') || '<li><em>None</em></li>';
    bl.querySelectorAll('li[data-path]').forEach(li => li.addEventListener('click', () => openNote(li.dataset.path)));
    const rl = document.getElementById('related-list');
    rl.innerHTML = related.map(n => `<li data-path="${n.path || n}">${n.title || n.path || n}</li>`).join('') || '<li><em>None</em></li>';
    rl.querySelectorAll('li[data-path]').forEach(li => li.addEventListener('click', () => openNote(li.dataset.path)));
}

// --- Action items panel ---
async function loadActions() {
    const res = await fetch(`${API}/actions`);
    const { actions } = await res.json();
    const list = document.getElementById('actions-list');
    list.innerHTML = actions.map(a =>
        `<li><label><input type="checkbox" data-id="${a.id}"> ${a.text || a.description || JSON.stringify(a)}</label></li>`
    ).join('') || '<li><em>No open actions</em></li>';
    list.querySelectorAll('input[type=checkbox]').forEach(cb => {
        cb.addEventListener('change', async () => {
            if (cb.checked) {
                await fetch(`${API}/actions/${cb.dataset.id}/done`, { method: 'POST' });
                setTimeout(loadActions, 300);
            }
        });
    });
}

// --- Intelligence panel ---
async function loadIntelligence() {
    const res = await fetch(`${API}/intelligence`);
    const { recap, nudges } = await res.json();
    document.getElementById('recap-content').textContent = recap || 'No recent recap.';
    const nl = document.getElementById('nudges-list');
    nl.innerHTML = nudges.map(n => `<li>${n.title || n.path || JSON.stringify(n)}</li>`).join('') || '<li><em>No stale notes</em></li>';
}

// --- New note modal ---
document.getElementById('new-note-btn').addEventListener('click', () => {
    document.getElementById('new-note-modal').style.display = 'flex';
});
document.getElementById('modal-cancel').addEventListener('click', () => {
    document.getElementById('new-note-modal').style.display = 'none';
});
document.getElementById('modal-save').addEventListener('click', async () => {
    const title = document.getElementById('modal-title').value.trim();
    const type = document.getElementById('modal-type').value;
    const body = document.getElementById('modal-body').value;
    if (!title) return;
    const res = await fetch(`${API}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, type, body, brain_path: brainPath }),
    });
    if (res.ok) {
        const { path } = await res.json();
        document.getElementById('new-note-modal').style.display = 'none';
        document.getElementById('modal-title').value = '';
        document.getElementById('modal-body').value = '';
        await loadNotes();
        openNote(path);
    }
});

// --- pywebviewready: safe to use pywebview.api ---
window.addEventListener('pywebviewready', () => {
    document.getElementById('open-editor-btn').style.display = '';
});
// Hide open-in-editor button until pywebviewready fires
document.getElementById('open-editor-btn').style.display = 'none';

// --- SSE live refresh ---
function updateStatusDot(connected) {
    const dot = document.getElementById('sse-status');
    if (!dot) return;
    dot.classList.toggle('sse-connected', connected);
    dot.classList.toggle('sse-disconnected', !connected);
}

function showConflictBanner(path) {
    const viewer = document.getElementById('viewer');
    const banner = document.createElement('div');
    banner.id = 'conflict-banner';
    banner.style.cssText = 'background:#fff3cd;border:1px solid #ffc107;padding:8px 12px;margin-bottom:8px;border-radius:4px;';
    banner.innerHTML = 'Note was updated externally. '
        + '<button id="conflict-keep">Keep my edits</button> '
        + '<button id="conflict-load">Load new version</button>';
    // Remove existing banner if any
    const existing = document.getElementById('conflict-banner');
    if (existing) existing.remove();
    viewer.parentNode.insertBefore(banner, viewer);
    document.getElementById('conflict-keep').onclick = () => banner.remove();
    document.getElementById('conflict-load').onclick = () => {
        banner.remove();
        isDirty = false;
        exitEditMode();
        openNote(path);
    };
}

function handleNoteEvent({ type, path }) {
    // Always refresh sidebar silently
    loadNotes();

    if (!currentPath) return;

    // Match: currentPath is absolute, path is relative — use endsWith
    const matchesCurrent = currentPath.endsWith('/' + path) || currentPath === path;
    if (!matchesCurrent) return;

    if (type === 'deleted') {
        currentPath = null;
        document.getElementById('viewer').innerHTML = '<em>Note was deleted.</em>';
        exitEditMode();
        return;
    }

    if (type === 'modified' || type === 'created') {
        if (easyMDE !== null) {
            // Editor is open — always show conflict banner regardless of isDirty.
            // Any open editor session must not be silently destroyed by an external event.
            // The user can choose Keep (dismiss banner) or Load (reload and close editor).
            showConflictBanner(currentPath);
        } else if (isDirty) {
            // isDirty but editor already closed (defensive: treat as conflict)
            showConflictBanner(currentPath);
        } else {
            openNote(currentPath);
        }
    }
}

let _sseWasConnected = false;

function connectSSE() {
    const evtSource = new EventSource(`${API}/events`);

    evtSource.onopen = () => {
        const wasDisconnected = !_sseWasConnected;
        _sseWasConnected = true;
        updateStatusDot(true);
        if (wasDisconnected) loadNotes();  // catch missed events on reconnect
    };

    evtSource.addEventListener('note', (e) => {
        try {
            const event = JSON.parse(e.data);
            handleNoteEvent(event);
        } catch (_) {}
    });

    evtSource.onerror = () => {
        _sseWasConnected = false;
        updateStatusDot(false);
        // EventSource auto-reconnects; onopen will fire again
    };
}

// --- Delete flow ---
deleteBtn.addEventListener('click', () => {
    if (!currentPath) return;
    const filename = currentPath.split('/').pop();
    document.getElementById('delete-modal-filename').textContent = filename;
    document.getElementById('delete-modal-error').style.display = 'none';
    document.getElementById('delete-modal-error').textContent = '';
    document.getElementById('delete-note-modal').style.display = 'flex';
});

document.getElementById('delete-modal-cancel').addEventListener('click', () => {
    document.getElementById('delete-note-modal').style.display = 'none';
});

document.getElementById('delete-modal-confirm').addEventListener('click', async () => {
    const pathToDelete = currentPath;
    if (!pathToDelete) return;
    let res;
    try {
        res = await fetch(`${API}/notes/${encodeURIComponent(pathToDelete)}`, { method: 'DELETE' });
    } catch (err) {
        const errEl = document.getElementById('delete-modal-error');
        errEl.textContent = 'Network error. Please try again.';
        errEl.style.display = '';
        return;
    }
    if (!res.ok) {
        const errEl = document.getElementById('delete-modal-error');
        errEl.textContent = 'Delete failed. Please try again.';
        errEl.style.display = '';
        return;
    }
    // Success: close modal, optimistic sidebar removal, clear state
    document.getElementById('delete-note-modal').style.display = 'none';
    document.querySelectorAll(`#note-list li[data-path="${pathToDelete}"]`).forEach(el => el.remove());
    currentPath = null;
    // Exit edit mode if open (clears EasyMDE, resets state)
    exitEditMode();
    // Show transient "Note deleted" message, then clear viewer
    const viewer = document.getElementById('viewer');
    viewer.innerHTML = '<em>Note deleted.</em>';
    setTimeout(() => {
        if (!currentPath) viewer.innerHTML = '';
    }, 2000);
    // Background refresh to sync note count / ordering
    loadNotes();
});

// --- Init ---
loadNotes();
loadActions();
loadIntelligence();
connectSSE();
