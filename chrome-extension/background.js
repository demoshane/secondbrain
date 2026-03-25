'use strict';

// Service worker for Second Brain Capture extension.
// Handles context menu setup, pendingCapture session storage, and popup trigger.

const DEFAULT_API_URL = 'http://127.0.0.1:37491';

// ── Context Menu Setup ────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'capture-page',
    title: 'Save Page to Brain',
    contexts: ['page'],
  });
  chrome.contextMenus.create({
    id: 'capture-selection',
    title: 'Save Selection to Brain',
    contexts: ['selection'],
  });
  chrome.contextMenus.create({
    id: 'capture-link',
    title: 'Save Link to Brain',
    contexts: ['link'],
  });
  chrome.contextMenus.create({
    id: 'capture-gmail',
    title: 'Capture thread to Brain',
    contexts: ['page'],
    documentUrlPatterns: ['https://mail.google.com/*'],
  });
});

// ── Context Menu Click Handler ────────────────────────────────────────────────

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'capture-gmail') {
    // Gmail context menu — extract thread data from content script first,
    // then store pendingCapture and open popup.
    // contextMenus.onClicked IS a trusted gesture source, so openPopup() works here.
    let gmailData = null;
    try {
      gmailData = await chrome.tabs.sendMessage(tab.id, { action: 'extract-gmail' });
    } catch (err) {
      console.warn('[SB] extract-gmail message failed:', err.message);
    }

    await chrome.storage.session.set({
      pendingCapture: {
        menuItemId: 'capture-gmail',
        gmailData,
        pageUrl: tab.url,
        timestamp: Date.now(),
      },
    });

    try {
      await chrome.action.openPopup();
    } catch (err) {
      console.warn('[SB] openPopup failed for Gmail:', err.message);
    }
    return;
  }

  // Store capture context before opening popup.
  // chrome.action.openPopup() must be the LAST call — it requires user gesture context
  // (context menu click qualifies), and awaits before it can break the gesture chain.
  await chrome.storage.session.set({
    pendingCapture: {
      menuItemId: info.menuItemId,
      selectionText: info.selectionText || null,
      linkUrl: info.linkUrl || null,
      pageUrl: tab.url,
      pageTitle: tab.title,
      timestamp: Date.now(),
    },
  });

  // Open popup — MUST be last (user gesture chain requirement)
  try {
    await chrome.action.openPopup();
  } catch (err) {
    // openPopup() can fail if popup is already open or window not focused.
    // Swallow — the pendingCapture data is already stored; user can click icon.
    console.warn('[SB] openPopup failed:', err.message);
  }
});

// ── Gmail Popup Message Handler ───────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'open-popup-gmail') {
    // pendingCapture already stored by content script.
    // Attempt to open popup — gesture propagation from content script
    // button click through sendMessage is NOT guaranteed by Chrome.
    // openPopup() returns a promise in Chrome 120+; older versions throw.
    try {
      const result = chrome.action.openPopup();
      if (result && typeof result.then === 'function') {
        result.then(() => sendResponse({ ok: true }))
              .catch(() => sendResponse({ ok: false }));
        return true; // keep message channel open for async response
      }
      sendResponse({ ok: true });
    } catch (err) {
      sendResponse({ ok: false });
    }
  }
});

// ── API URL Helper ────────────────────────────────────────────────────────────

async function getApiUrl() {
  const { apiUrl } = await chrome.storage.sync.get({ apiUrl: DEFAULT_API_URL });
  return apiUrl;
}

// ── API Status Badge (poll every 30s) ────────────────────────────────────────

async function checkApiStatus() {
  const apiUrl = await getApiUrl();
  try {
    const res = await fetch(`${apiUrl}/ping`, { signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      chrome.action.setBadgeText({ text: '' });
      // Restore normal icon (remove greyed state if previously offline)
      chrome.action.setIcon({
        path: {
          16: 'icons/icon16.png',
          48: 'icons/icon48.png',
          128: 'icons/icon128.png',
        },
      });
    } else {
      setOfflineBadge();
    }
  } catch {
    setOfflineBadge();
  }
}

function setOfflineBadge() {
  chrome.action.setBadgeText({ text: '!' });
  chrome.action.setBadgeBackgroundColor({ color: '#cc0000' });
}

// Initial check + poll every 30 seconds via alarms
chrome.alarms.create('api-status-check', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'api-status-check') {
    checkApiStatus();
  }
});
// Check on service worker start
checkApiStatus();
