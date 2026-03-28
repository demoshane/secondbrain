'use strict';

// Second Brain Capture — Popup Logic
// Handles form population, API connectivity check, save, and capture history.

const DEFAULT_API_URL = 'http://127.0.0.1:37491';
const MAX_HISTORY = 10;

let currentApiUrl = DEFAULT_API_URL;
let currentPageUrl = '';
let captureSourceUrl = '';
let captureSourceType = 'web';

// ── Entry Point ───────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  // Load API URL from options
  const { apiUrl } = await chrome.storage.sync.get({ apiUrl: DEFAULT_API_URL });
  currentApiUrl = apiUrl;

  // Load default tags from options
  const { defaultTags } = await chrome.storage.sync.get({ defaultTags: '' });
  if (defaultTags) {
    document.getElementById('sb-tags').value = defaultTags;
  }

  // Check API connectivity (non-blocking — UI stays responsive)
  checkConnectivity();

  // Attach form handlers unconditionally — must happen regardless of population path
  document.getElementById('capture-form').addEventListener('submit', handleSave);
  document.getElementById('cancel-btn').addEventListener('click', () => window.close());

  // Attach summarise handlers unconditionally
  document.getElementById('summarise-btn').addEventListener('click', handleSummarise);
  document.getElementById('add-to-brain-btn').addEventListener('click', handleAddTobrainFromSummary);
  document.getElementById('summary-cancel-btn').addEventListener('click', discardSummary);

  // Check URL params first (Gmail button / tab fallback flow — avoids storage API limitations)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('sb_title')) {
    document.getElementById('sb-title').value = urlParams.get('sb_title') || '';
    document.getElementById('sb-body').value = urlParams.get('sb_body') || '';
    document.getElementById('sb-type').value = urlParams.get('sb_type') || 'note';
    document.getElementById('sb-tags').value = urlParams.get('sb_tags') || '';
    currentPageUrl = urlParams.get('sb_source_url') || '';
    captureSourceUrl = currentPageUrl;
    captureSourceType = urlParams.get('sb_source_type') || 'web';
    return; // skip further population (handlers already attached above)
  }

  // Check for pendingCapture (context menu flow) or fall back to icon-click flow
  let pendingCapture = null;
  try {
    ({ pendingCapture } = await chrome.storage.session.get('pendingCapture'));
  } catch (e) {
    // chrome.storage.session unavailable (some Chromium forks) — skip
  }

  if (pendingCapture) {
    // Context menu flow — remove pending data then populate form
    try { await chrome.storage.session.remove('pendingCapture'); } catch (e) {}
    await populateFromPendingCapture(pendingCapture);
  } else {
    // Icon click — extract article from current active tab
    await populateFromActiveTab();
  }

  // Render capture history
  renderHistory();
});

// ── Form Population ───────────────────────────────────────────────────────────

async function populateFromPendingCapture(pending) {
  currentPageUrl = pending.pageUrl || '';

  switch (pending.menuItemId) {
    case 'capture-page': {
      // Full article extraction via Readability.js
      setFormLoading(true);
      const result = await sendToContentScript(pending.pageUrl, { action: 'extract-article' });
      setFormLoading(false);

      if (result && result.success) {
        setField('sb-title', result.title || pending.pageTitle || '');
        setField('sb-body', result.textContent || '');
        setTypePreselect('note');
      } else {
        // Graceful fallback — use page title
        setField('sb-title', pending.pageTitle || '');
        setField('sb-body', result?.error ? `[Extraction failed: ${result.error}]\n\n${pending.pageUrl}` : pending.pageUrl);
        setTypePreselect('note');
        if (result?.error) {
          showError(`Article extraction issue: ${result.error}. You can still save manually.`);
        }
      }
      break;
    }

    case 'capture-selection': {
      // Selected text — use selectionText directly from context menu info
      const title = pending.pageTitle || deriveTitle(pending.pageUrl);
      setField('sb-title', `Selection from: ${title}`);
      setField('sb-body', pending.selectionText
        ? `${pending.selectionText}\n\nSource: ${pending.pageUrl}`
        : `Source: ${pending.pageUrl}`);
      setTypePreselect('note');
      break;
    }

    case 'capture-link': {
      // URL/link capture — bookmark style
      const linkTitle = deriveTitle(pending.linkUrl || pending.pageUrl);
      setField('sb-title', linkTitle);
      setField('sb-body', `URL: ${pending.linkUrl || pending.pageUrl}`);
      setTypePreselect('link');
      currentPageUrl = pending.linkUrl || pending.pageUrl;
      break;
    }

    case 'capture-gmail': {
      // Gmail thread capture — pre-fill with extracted thread data
      const gd = pending.gmailData;
      if (gd) {
        setField('sb-title', gd.subject || 'Gmail Thread');
        setTypePreselect('meeting'); // pre-suggest meeting per D-04
        setField('sb-body', gd.fullBody || '');
        setField('sb-tags', 'email');
      } else {
        // gmailData extraction failed — basic fallback
        setField('sb-title', 'Gmail Thread');
        setTypePreselect('meeting');
        setField('sb-body', `Source: ${pending.pageUrl}`);
        setField('sb-tags', 'email');
      }
      // Store source URL and type for POST
      captureSourceUrl = pending.pageUrl;
      captureSourceType = 'gmail';
      currentPageUrl = pending.pageUrl;
      break;
    }

    default: {
      // Unknown menu item — fall back to page extraction
      await populateFromActiveTab();
    }
  }
}

async function populateFromActiveTab() {
  // Icon click — get active tab and extract article
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  currentPageUrl = tab.url || '';
  captureSourceUrl = tab.url || '';
  captureSourceType = 'web';
  setFormLoading(true);

  const result = await sendToContentScript(tab.url, { action: 'extract-article' });
  setFormLoading(false);

  if (result && result.success) {
    setField('sb-title', result.title || tab.title || '');
    setField('sb-body', result.textContent || '');
    setTypePreselect('note');
  } else {
    // Fallback for pages where content script can't run (chrome:// pages, etc.)
    setField('sb-title', tab.title || '');
    setField('sb-body', `URL: ${tab.url}`);
    setTypePreselect('note');
  }
}

// ── Content Script Messaging ──────────────────────────────────────────────────

async function sendToContentScript(pageUrl, message) {
  try {
    // Find the tab with this URL (active tab for page captures)
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) return null;

    // chrome.scripting.executeScript can inject if content script isn't loaded
    const response = await chrome.tabs.sendMessage(tab.id, message);
    return response;
  } catch (err) {
    console.warn('[SB Popup] Content script message failed:', err.message);
    return null;
  }
}

// ── API Connectivity ──────────────────────────────────────────────────────────

async function checkConnectivity() {
  const statusBar = document.getElementById('status-bar');
  try {
    const res = await fetch(`${currentApiUrl}/ping`, {
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      statusBar.className = 'status-bar connected';
    } else {
      setApiOffline(statusBar);
    }
  } catch {
    setApiOffline(statusBar);
  }
}

function setApiOffline(statusBar) {
  statusBar.className = 'status-bar disconnected';
  // Add inline status message below status bar
  const msg = document.createElement('div');
  msg.className = 'status-message';
  msg.textContent = 'sb-api unreachable — check that sb-api is running on ' + currentApiUrl;
  statusBar.insertAdjacentElement('afterend', msg);
  // Disable save button
  document.getElementById('save-btn').disabled = true;
}

// ── Save Handler ──────────────────────────────────────────────────────────────

async function handleSave(e) {
  e.preventDefault();
  clearError();

  const title = document.getElementById('sb-title').value.trim();
  const type = document.getElementById('sb-type').value;
  const body = document.getElementById('sb-body').value.trim();
  const tagsRaw = document.getElementById('sb-tags').value.trim();
  const tags = tagsRaw ? tagsRaw.split(',').map((t) => t.trim()).filter(Boolean) : [];

  if (!title) {
    showError('Title is required.');
    return;
  }

  const saveBtn = document.getElementById('save-btn');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving…';

  try {
    const payload = {
      title,
      type,
      body,
      tags,
      source_url: captureSourceUrl || currentPageUrl || undefined,
      source_type: captureSourceType || 'web',
    };

    const res = await fetch(`${currentApiUrl}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(10000),
    });

    if (res.status === 201 || res.status === 200) {
      // Success
      addToHistory({ title, type, url: currentPageUrl });
      saveBtn.textContent = 'Saved!';
      saveBtn.style.background = '#16a34a';
      // Close after brief "Saved!" flash.
      // Use chrome.tabs.remove when running as a tab — window.close() is blocked
      // by some Chromium forks (Vivaldi) when the tab wasn't opened by JS.
      setTimeout(() => {
        if (chrome.tabs && typeof chrome.tabs.getCurrent === 'function') {
          chrome.tabs.getCurrent((tab) => {
            if (tab) chrome.tabs.remove(tab.id);
            else window.close();
          });
        } else {
          window.close();
        }
      }, 400);
    } else {
      const errData = await res.json().catch(() => ({}));
      showError(`Save failed (${res.status}): ${errData.error || errData.message || 'Unknown error'}`);
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';
    }
  } catch (err) {
    showError(`Network error: ${err.message}`);
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save';
  }
}

// ── Summarise Flow ────────────────────────────────────────────────────────

let _summariseResult = null; // { summary, title, url } — held until "Add to brain" or "Discard"

async function handleSummarise() {
  clearError();
  const btn = document.getElementById('summarise-btn');
  btn.disabled = true;
  btn.textContent = 'Summarising…';

  try {
    // Get active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      showError('No active tab found.');
      btn.disabled = false;
      btn.textContent = 'Summarise page';
      return;
    }

    const tabUrl = tab.url || '';
    const tabTitle = tab.title || 'Untitled';

    // Extract page text via content script (same path as article extraction)
    const result = await sendToContentScript(tabUrl, { action: 'extract-article' });
    const rawText = (result && result.success && result.textContent) ? result.textContent : '';
    const content = rawText.slice(0, 8000);

    if (!content) {
      showError('Could not extract page text. The page may not be accessible.');
      btn.disabled = false;
      btn.textContent = 'Summarise page';
      return;
    }

    // POST to backend
    const res = await fetch(`${currentApiUrl}/summarise-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: tabUrl, content }),
      signal: AbortSignal.timeout(30000),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      showError(`Summarise failed (${res.status}): ${errData.error || 'Unknown error'}`);
      btn.disabled = false;
      btn.textContent = 'Summarise page';
      return;
    }

    const data = await res.json();
    const summary = (data.summary || '').trim();

    if (!summary) {
      showError('LLM returned an empty summary. Try again.');
      btn.disabled = false;
      btn.textContent = 'Summarise page';
      return;
    }

    // Store result for "Add to brain"
    _summariseResult = { summary, title: `Summary: ${tabTitle}`, url: tabUrl };

    // Show summary panel, hide capture form
    document.getElementById('capture-form').classList.add('hidden');
    document.getElementById('summarise-section').classList.add('hidden');
    document.getElementById('summary-text').textContent = summary;
    document.getElementById('summary-panel').classList.remove('hidden');

  } catch (err) {
    showError(`Network error: ${err.message}`);
    btn.disabled = false;
    btn.textContent = 'Summarise page';
  }
}

async function handleAddTobrainFromSummary() {
  if (!_summariseResult) return;

  const addBtn = document.getElementById('add-to-brain-btn');
  addBtn.disabled = true;
  addBtn.textContent = 'Saving…';

  try {
    const payload = {
      title: _summariseResult.title,
      type: 'note',
      body: _summariseResult.summary,
      tags: ['summary'],
      source_url: _summariseResult.url,
      source_type: 'web',
    };

    const res = await fetch(`${currentApiUrl}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(10000),
    });

    if (res.status === 201 || res.status === 200) {
      addToHistory({ title: _summariseResult.title, type: 'note', url: _summariseResult.url });
      addBtn.textContent = 'Saved!';
      addBtn.style.background = '#16a34a';
      setTimeout(() => {
        if (chrome.tabs && typeof chrome.tabs.getCurrent === 'function') {
          chrome.tabs.getCurrent((tab) => {
            if (tab) chrome.tabs.remove(tab.id);
            else window.close();
          });
        } else {
          window.close();
        }
      }, 400);
    } else {
      const errData = await res.json().catch(() => ({}));
      showError(`Save failed (${res.status}): ${errData.error || errData.message || 'Unknown error'}`);
      addBtn.disabled = false;
      addBtn.textContent = 'Add to brain';
    }
  } catch (err) {
    showError(`Network error: ${err.message}`);
    addBtn.disabled = false;
    addBtn.textContent = 'Add to brain';
  }
}

function discardSummary() {
  _summariseResult = null;
  document.getElementById('summary-panel').classList.add('hidden');
  document.getElementById('capture-form').classList.remove('hidden');
  document.getElementById('summarise-section').classList.remove('hidden');
  document.getElementById('summarise-btn').disabled = false;
  document.getElementById('summarise-btn').textContent = 'Summarise page';
}

// ── Capture History ───────────────────────────────────────────────────────────

function addToHistory(entry) {
  try {
    const history = JSON.parse(localStorage.getItem('captureHistory') || '[]');
    history.unshift({ ...entry, savedAt: new Date().toISOString() });
    localStorage.setItem('captureHistory', JSON.stringify(history.slice(0, MAX_HISTORY)));
  } catch {
    // localStorage failure is non-fatal
  }
}

function renderHistory() {
  try {
    const history = JSON.parse(localStorage.getItem('captureHistory') || '[]');
    if (!history.length) return;

    const section = document.getElementById('history-section');
    const list = document.getElementById('history-list');
    section.classList.remove('hidden');
    list.replaceChildren();

    for (const entry of history) {
      const li = document.createElement('li');
      const time = relativeTime(entry.savedAt);

      const titleSpan = document.createElement('span');
      titleSpan.className = 'history-title';
      titleSpan.title = entry.title || '';
      titleSpan.textContent = entry.title || 'Untitled';

      const typeSpan = document.createElement('span');
      typeSpan.className = 'history-type';
      typeSpan.textContent = entry.type || 'note';

      const timeSpan = document.createElement('span');
      timeSpan.className = 'history-time';
      timeSpan.textContent = time;

      li.appendChild(titleSpan);
      li.appendChild(typeSpan);
      li.appendChild(timeSpan);
      list.appendChild(li);
    }
  } catch {
    // History render failure is non-fatal
  }
}

// ── Utility Helpers ───────────────────────────────────────────────────────────

function setField(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = value;
}

function setTypePreselect(type) {
  const select = document.getElementById('sb-type');
  if (select) select.value = type;
}

function setFormLoading(loading) {
  const form = document.getElementById('capture-form');
  if (loading) {
    form.classList.add('loading');
    document.getElementById('sb-body').placeholder = 'Extracting content…';
  } else {
    form.classList.remove('loading');
    document.getElementById('sb-body').placeholder = 'Content will be extracted here…';
  }
}

function showError(msg) {
  const el = document.getElementById('error-msg');
  el.textContent = msg;
  el.classList.remove('hidden');
}

function clearError() {
  const el = document.getElementById('error-msg');
  el.textContent = '';
  el.classList.add('hidden');
}

function deriveTitle(url) {
  if (!url) return 'Untitled';
  try {
    const u = new URL(url);
    const path = u.pathname.replace(/\/$/, '').split('/').pop();
    return path || u.hostname;
  } catch {
    return url.slice(0, 60);
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function relativeTime(isoString) {
  try {
    const diff = Date.now() - new Date(isoString).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  } catch {
    return '';
  }
}
