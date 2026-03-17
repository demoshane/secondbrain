// Second Brain GUI — ES module
const API = window.API_BASE || 'http://127.0.0.1:37491';
let currentPath = null;
let easyMDE = null;
let brainPath = null;
let isDirty = false;
let activeTagFilter = null;
let _suppressNextTagRefresh = false;
let _allNotes = []; // module-level cache of all notes from last loadNotes()

// --- Sidebar collapse state (server-side persistence via /ui/prefs) ---
let _collapseState = {}; // in-memory cache; loaded async at startup

async function _loadCollapseState() {
    try {
        const res = await fetch(`${API}/ui/prefs`);
        if (res.ok) {
            const prefs = await res.json();
            _collapseState = prefs.collapseState || {};
        }
    } catch (_) {}
}

function getCollapseState() {
    return _collapseState;
}

function setCollapseState(key, collapsed) {
    _collapseState[key] = collapsed;
    // Persist to server (fire-and-forget)
    fetch(`${API}/ui/prefs`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collapseState: _collapseState }),
    }).catch(() => {});
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
    _allNotes = notes;
    // Derive brain_path from the first note path (strip deepest components)
    if (notes.length && !brainPath) {
        const parts = notes[0].path.split('/');
        // Heuristic: brain root is 2 levels up from note path
        brainPath = parts.slice(0, -2).join('/') || '/';
    }
    // If tag filter is active, re-apply it after reload; don't blow away the filter view
    if (activeTagFilter) {
        runTagFilter(activeTagFilter);
    } else {
        renderHierarchySidebar(notes);
    }
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

// --- Tag autocomplete helpers ---

function _getAllUniqueTags() {
    const seen = new Set();
    for (const n of _allNotes) {
        for (const t of (n.tags || [])) seen.add(t);
    }
    return [...seen].sort();
}

function _attachTagDatalist(inputEl) {
    // Append to body so positioning works regardless of when input enters DOM
    const dropdown = document.createElement('div');
    dropdown.className = 'tag-autocomplete-dropdown';
    dropdown.style.display = 'none';
    document.body.appendChild(dropdown);

    function position() {
        const r = inputEl.getBoundingClientRect();
        dropdown.style.position = 'fixed';
        dropdown.style.left = r.left + 'px';
        dropdown.style.top = (r.bottom + 2) + 'px';
        dropdown.style.minWidth = Math.max(r.width, 140) + 'px';
    }

    function showSuggestions() {
        const q = inputEl.value.trim().toLowerCase();
        const matches = _getAllUniqueTags().filter(t => t.toLowerCase().includes(q));
        dropdown.innerHTML = '';
        if (!matches.length) { dropdown.style.display = 'none'; return; }
        matches.forEach(tag => {
            const item = document.createElement('div');
            item.className = 'tag-autocomplete-item';
            item.textContent = tag;
            item.addEventListener('mousedown', (e) => {
                e.preventDefault();
                inputEl.value = tag;
                dropdown.style.display = 'none';
                inputEl.dispatchEvent(new Event('tagselected'));
            });
            dropdown.appendChild(item);
        });
        position();
        dropdown.style.display = 'block';
    }

    inputEl.setAttribute('autocomplete', 'off');
    inputEl.addEventListener('input', showSuggestions);
    inputEl.addEventListener('focus', showSuggestions);
    inputEl.addEventListener('blur', () => setTimeout(() => { dropdown.style.display = 'none'; }, 150));

    // Clean up when input leaves DOM
    const obs = new MutationObserver(() => {
        if (!document.contains(inputEl)) { dropdown.remove(); obs.disconnect(); }
    });
    obs.observe(document.body, { childList: true, subtree: true });
}

// --- Tag chips ---

function renderTagChips(tags, notePath) {
    const container = document.getElementById('tag-chips');
    if (!container) return;
    container.innerHTML = '';
    const tagsCopy = [...tags];

    tagsCopy.forEach((tag, idx) => {
        // Guard: skip error strings leaking into the tag field (AI processing artifacts).
        // A valid tag is short and doesn't start with a prose sentence.
        if (typeof tag !== 'string' || tag.length > 60 || /^(The |Could |Error|Failed|Unable )/i.test(tag)) return;
        const chip = document.createElement('span');
        chip.className = 'tag-chip';
        chip.textContent = '#' + tag;
        chip.addEventListener('click', () => activateTagFilter(tag));
        chip.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            makeChipEditable(chip, idx, tagsCopy, notePath);
        });

        const del = document.createElement('span');
        del.className = 'tag-chip-delete';
        del.textContent = '×';
        del.title = 'Remove tag';
        del.addEventListener('click', (e) => {
            e.stopPropagation();
            const updated = tagsCopy.filter((_, i) => i !== idx);
            saveTags(updated, notePath);
        });
        chip.appendChild(del);
        container.appendChild(chip);
    });

    const addBtn = document.createElement('button');
    addBtn.className = 'tag-add-btn';
    addBtn.textContent = '+ Add tag';
    addBtn.addEventListener('click', () => addNewTag(tagsCopy, notePath));
    container.appendChild(addBtn);
}

function makeChipEditable(chipEl, tagIndex, allTags, notePath) {
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'tag-chip-input';
    input.autocomplete = 'off';
    input.value = allTags[tagIndex];
    _attachTagDatalist(input);
    chipEl.replaceWith(input);
    input.focus();
    input.select();

    let committed = false;
    function commit() {
        if (committed) return;
        committed = true;
        const newVal = input.value.trim();
        if (newVal === '') {
            // Empty = delete this tag
            const updated = allTags.filter((_, i) => i !== tagIndex);
            saveTags(updated, notePath);
        } else if (newVal !== allTags[tagIndex]) {
            allTags[tagIndex] = newVal;
            saveTags([...allTags], notePath);
        } else {
            renderTagChips(allTags, notePath);
        }
    }

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); commit(); }
        if (e.key === 'Escape') { committed = true; renderTagChips(allTags, notePath); }
    });
    input.addEventListener('blur', commit);
}

function addNewTag(allTags, notePath) {
    const container = document.getElementById('tag-chips');
    if (!container) return;
    // Remove the add button temporarily
    const addBtn = container.querySelector('.tag-add-btn');
    if (addBtn) addBtn.remove();

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'tag-chip-input';
    input.autocomplete = 'off';
    input.placeholder = 'new tag';
    _attachTagDatalist(input);
    container.appendChild(input);
    input.focus();

    let committed = false;
    function commit() {
        if (committed) return;
        committed = true;
        const newVal = input.value.trim();
        if (newVal) {
            const updatedTags = [...allTags, newVal];
            saveTags(updatedTags, notePath);
        } else {
            renderTagChips(allTags, notePath);
        }
    }

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); commit(); }
        if (e.key === 'Escape') { committed = true; renderTagChips(allTags, notePath); }
    });
    input.addEventListener('blur', commit);
}

async function saveTags(tags, notePath) {
    _suppressNextTagRefresh = true;
    // Optimistic update: update cache and re-render chips immediately
    const cachedNote = _allNotes.find(n => n.path === notePath);
    if (cachedNote) cachedNote.tags = tags;
    renderTagChips(tags, notePath);

    const res = await fetch(`${API}/notes/${encodeURIComponent(notePath)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags }),
    });

    if (!res.ok) {
        // Failure: flash error, revert
        _suppressNextTagRefresh = false;
        const container = document.getElementById('tag-chips');
        if (container) {
            container.classList.add('tag-save-error');
            setTimeout(() => container.classList.remove('tag-save-error'), 1500);
        }
        // Revert cache
        if (cachedNote) {
            // Re-fetch from server on failure; use original tags if available
            cachedNote.tags = tags; // best-effort: leave as-is, server has truth
        }
    }
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
    // Render tag chips using cached notes (GET /notes/<path> doesn't return tags)
    const cachedNote = _allNotes.find(n => n.path === path);
    renderTagChips(cachedNote ? (cachedNote.tags || []) : [], path);
    loadMeta(path);
    loadActions();
    loadIntelligence();
    loadAttachments(path);
    const viewerUploadBtn = document.getElementById('viewer-upload-btn');
    if (viewerUploadBtn) viewerUploadBtn.style.display = '';
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

// --- Tag filter ---

function activateTagFilter(tag) {
    activeTagFilter = tag;
    const banner = document.getElementById('filter-banner');
    banner.style.display = 'flex';
    // Use textContent for the label to prevent XSS, then append button separately
    banner.innerHTML = '';
    const label = document.createElement('span');
    label.textContent = 'Filtering: ';
    const strong = document.createElement('strong');
    strong.textContent = '#' + tag;
    label.appendChild(strong);
    banner.appendChild(label);
    const clearBtn = document.createElement('button');
    clearBtn.className = 'filter-clear-btn';
    clearBtn.id = 'filter-clear';
    clearBtn.textContent = '×';
    clearBtn.addEventListener('click', clearTagFilter);
    banner.appendChild(clearBtn);
    runTagFilter(tag);
}

function clearTagFilter() {
    activeTagFilter = null;
    const banner = document.getElementById('filter-banner');
    if (banner) banner.style.display = 'none';
    const q = document.getElementById('search-input').value.trim();
    if (q) runSearch(q); else loadNotes();
}

function runTagFilter(tag) {
    const q = document.getElementById('search-input').value.trim();
    if (q) {
        // Active search query present: delegate to runSearch which includes activeTagFilter (AND logic)
        runSearch(q);
    } else {
        // No search query: filter client-side from notes cache
        const filtered = _allNotes.filter(n => (n.tags || []).includes(tag));
        renderFlatList(filtered);
    }
}

// --- Search ---
let searchTimer = null;
document.getElementById('search-input').addEventListener('input', e => {
    clearTimeout(searchTimer);
    const q = e.target.value.trim();
    if (!q) {
        // If tag filter active, show filtered list; otherwise restore full sidebar
        if (activeTagFilter) { runTagFilter(activeTagFilter); return; }
        loadNotes();
        return;
    }
    searchTimer = setTimeout(() => runSearch(q), 300);
});

async function runSearch(query) {
    const mode = document.getElementById('search-mode').value;
    const body = { query, mode };
    // AND logic: include activeTagFilter as tags param when set
    if (activeTagFilter !== null) {
        body.tags = [activeTagFilter];
    }
    const res = await fetch(`${API}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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

function handleNoteEvent({ type, path, note_path }) {
    // Attachment event: refresh attachment list for the current note if it matches
    if (type === 'attachment') {
        if (currentPath && (currentPath === note_path || (note_path && currentPath.endsWith('/' + note_path)))) {
            loadAttachments(currentPath);
        }
        return;
    }

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
            // Tag save triggers a modified event; suppress one re-render to avoid
            // destroying an in-progress chip edit
            if (_suppressNextTagRefresh) { _suppressNextTagRefresh = false; return; }
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

// --- File upload & attachments ---

async function uploadFile(file) {
    if (!currentPath) return;
    const fd = new FormData();
    fd.append('file', file);
    fd.append('note_path', currentPath);
    const res = await fetch(`${API}/files/upload`, { method: 'POST', body: fd });
    if (res.ok) {
        await loadAttachments(currentPath);
        await loadNotes();
    }
    // silent success — no toast per CONTEXT.md
}

// Top toolbar "File" button — opens global file management modal
const uploadBtn = document.getElementById('upload-btn');
const fileInput = document.getElementById('file-input');
const filesModal = document.getElementById('files-modal');
const filesModalList = document.getElementById('files-modal-list');
const filesModalClose = document.getElementById('files-modal-close');

async function openFilesModal() {
    if (!filesModal || !filesModalList) return;
    filesModalList.innerHTML = '<li style="color:#999">Loading...</li>';
    filesModal.style.display = 'flex';
    try {
        const res = await fetch(`${API}/files`);
        const { files } = await res.json();
        if (!files || files.length === 0) {
            filesModalList.innerHTML = '<li style="color:#999"><em>No uploaded files yet.</em></li>';
            return;
        }
        filesModalList.innerHTML = '';
        files.forEach(f => {
            const li = document.createElement('li');
            li.style.cssText = 'padding:6px 0; border-bottom:1px solid #f0f0f0; cursor:pointer;';
            const sizeStr = f.size > 1048576
                ? (f.size / 1048576).toFixed(1) + ' MB'
                : (f.size / 1024).toFixed(0) + ' KB';
            li.textContent = `${f.name}  ·  ${sizeStr}`;
            li.title = f.path;
            li.addEventListener('click', () => {
                if (window.pywebview) window.pywebview.api.open_file(f.path).catch(() => {});
                else alert(`Path: ${f.path}`);
            });
            filesModalList.appendChild(li);
        });
    } catch (_) {
        filesModalList.innerHTML = '<li style="color:red"><em>Failed to load files.</em></li>';
    }
}

if (uploadBtn) {
    // Top toolbar button: open file management modal (note-agnostic)
    uploadBtn.addEventListener('click', openFilesModal);
    uploadBtn.disabled = false;  // always enabled — not note-specific
}
if (filesModalClose) {
    filesModalClose.addEventListener('click', () => { if (filesModal) filesModal.style.display = 'none'; });
}
if (filesModal) {
    filesModal.addEventListener('click', (e) => { if (e.target === filesModal) filesModal.style.display = 'none'; });
}
if (fileInput) {
    fileInput.addEventListener('change', e => {
        const file = e.target.files[0];
        if (file) uploadFile(file);
        e.target.value = '';
    });
}

// Viewer upload button (same action)
const viewerUploadBtn = document.getElementById('viewer-upload-btn');
if (viewerUploadBtn) {
    viewerUploadBtn.addEventListener('click', () => fileInput && fileInput.click());
}

// Drag-and-drop onto viewer
const viewerEl = document.getElementById('viewer');
if (viewerEl) {
    viewerEl.addEventListener('dragover', e => { e.preventDefault(); });
    viewerEl.addEventListener('drop', e => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file && currentPath) uploadFile(file);
    });
}

async function loadAttachments(notePath) {
    const section = document.getElementById('attachments-section');
    const list = document.getElementById('attachments-list');
    if (!section || !list) return;
    const res = await fetch(`${API}/notes/${encodeURIComponent(notePath)}/attachments`);
    if (!res.ok) { section.style.display = 'none'; return; }
    const data = await res.json();
    const items = data.attachments || [];
    if (items.length === 0) { section.style.display = 'none'; return; }
    section.style.display = 'block';
    list.innerHTML = '';
    items.forEach(att => {
        const li = document.createElement('li');
        li.style.cssText = 'padding: 4px 0; font-size: 13px; cursor: pointer;';
        const sizeStr = att.size > 1048576
            ? (att.size / 1048576).toFixed(1) + ' MB'
            : (att.size / 1024).toFixed(0) + ' KB';
        const dateStr = att.uploaded_at ? att.uploaded_at.slice(0, 10) : '';
        li.textContent = `${att.filename} · ${dateStr} · ${sizeStr}`;
        li.title = att.file_path;
        li.addEventListener('click', () => {
            // Show metadata in viewer; offer OS open
            const info = `File: ${att.filename}\nSize: ${sizeStr}\nDate: ${dateStr}\nPath: ${att.file_path}`;
            if (window.pywebview) {
                window.pywebview.api.open_file(att.file_path).catch(() => {});
            } else {
                alert(info);
            }
        });
        list.appendChild(li);
    });
}

// --- Batch capture ---
const batchCaptureBtn = document.getElementById('batch-capture-btn');
if (batchCaptureBtn) {
    batchCaptureBtn.addEventListener('click', async () => {
        batchCaptureBtn.disabled = true;
        batchCaptureBtn.textContent = 'Capturing...';
        try {
            const res = await fetch(`${API}/batch-capture`, { method: 'POST' });
            const data = await res.json();
            const msg = `Batch capture: ${data.succeeded.length} captured, ${data.failed.length} failed`;
            // Display in Intelligence panel using existing pattern
            const intel = document.getElementById('recap-content');
            if (intel) {
                const p = document.createElement('p');
                p.style.cssText = 'margin: 4px 0; font-size: 13px;';
                p.textContent = msg;
                intel.prepend(p);
            }
            await loadNotes();
        } finally {
            batchCaptureBtn.disabled = false;
            batchCaptureBtn.textContent = 'Batch Capture';
        }
    });
}

// --- Init ---
// Load collapse state from server before rendering sidebar so sections
// are shown in their correct collapsed/expanded state on first paint.
_loadCollapseState().then(() => loadNotes());
loadActions();
loadIntelligence();
connectSSE();
