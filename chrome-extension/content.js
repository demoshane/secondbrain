'use strict';

// Content script for Second Brain Capture extension.
// Handles article extraction (Readability.js), selection extraction, and Gmail integration.
// Note: Readability.js and purify.min.js are loaded before this file (manifest order).
// Gmail content script entry does NOT include Readability/DOMPurify.

// ── Message Handler ───────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  switch (msg.action) {
    case 'extract-article':
      handleExtractArticle(sendResponse);
      return true; // Keep channel open for async sendResponse

    case 'extract-selection':
      handleExtractSelection(sendResponse);
      return true;

    case 'extract-gmail':
      sendResponse(extractGmailThread());
      return true;

    default:
      return false;
  }
});

// ── Article Extraction ────────────────────────────────────────────────────────

function handleExtractArticle(sendResponse) {
  try {
    // Readability is only available on non-Gmail pages (see manifest)
    if (typeof Readability === 'undefined') {
      sendResponse({
        success: false,
        error: 'Readability not available on this page',
        title: document.title,
        textContent: document.body ? document.body.innerText.slice(0, 5000) : '',
        excerpt: '',
        url: location.href,
      });
      return;
    }

    // Clone the document — Readability modifies the DOM in-place
    const docClone = document.cloneNode(true);
    const reader = new Readability(docClone);
    const article = reader.parse();

    if (!article) {
      sendResponse({
        success: false,
        error: 'Readability could not parse this page',
        title: document.title,
        textContent: document.body ? document.body.innerText.slice(0, 5000) : '',
        excerpt: '',
        url: location.href,
      });
      return;
    }

    // Sanitize text content — DOMPurify on the text removes any XSS vectors
    const safeText =
      typeof DOMPurify !== 'undefined'
        ? DOMPurify.sanitize(article.textContent)
        : article.textContent;

    sendResponse({
      success: true,
      title: article.title || document.title,
      textContent: safeText,
      excerpt: article.excerpt || '',
      url: location.href,
    });
  } catch (err) {
    sendResponse({
      success: false,
      error: err.message,
      title: document.title,
      textContent: '',
      excerpt: '',
      url: location.href,
    });
  }
}

// ── Selection Extraction ──────────────────────────────────────────────────────

function handleExtractSelection(sendResponse) {
  try {
    const selection = window.getSelection();
    const selectionText = selection ? selection.toString().trim() : '';
    sendResponse({
      success: true,
      selectionText,
      url: location.href,
      pageTitle: document.title,
    });
  } catch (err) {
    sendResponse({
      success: false,
      error: err.message,
      selectionText: '',
      url: location.href,
      pageTitle: document.title,
    });
  }
}

// ── Gmail Integration ────────────────────────────────────────────────────────

const isGmail = location.hostname === 'mail.google.com';

if (isGmail) {
  const gmailObserver = new MutationObserver(() => {
    // Look for thread view — use data-thread-id or role="main" with thread content
    const threadView = document.querySelector('[data-thread-id]')
      || document.querySelector('[role="main"] [data-legacy-thread-id]');
    if (threadView && !document.querySelector('#sb-gmail-btn')) {
      injectGmailButton(threadView);
    }
  });

  // document.body may be null if the content script runs before Gmail's body exists.
  // Wait for it to be available before attaching the observer.
  const attachObserver = () => {
    if (document.body) {
      gmailObserver.observe(document.body, { childList: true, subtree: true });
    } else {
      document.addEventListener('DOMContentLoaded', () => {
        gmailObserver.observe(document.body, { childList: true, subtree: true });
      });
    }
  };
  attachObserver();
}

function injectGmailButton(threadView) {
  // Guard against duplicate
  if (document.querySelector('#sb-gmail-btn')) return;

  const btn = document.createElement('button');
  btn.id = 'sb-gmail-btn';
  btn.textContent = 'Save to Brain';
  Object.assign(btn.style, {
    padding: '6px 12px',
    background: '#4285f4',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '13px',
    marginLeft: '8px',
  });

  btn.onclick = async () => {
    const threadData = extractGmailThread();
    // Store pendingCapture directly via chrome.storage.session
    // (content scripts CAN access chrome.storage)
    await chrome.storage.session.set({
      pendingCapture: {
        menuItemId: 'capture-gmail',
        gmailData: threadData,
        pageUrl: location.href,
        timestamp: Date.now(),
      },
    });
    // Send message to background to open popup.
    // NOTE: chrome.action.openPopup() requires user gesture propagation.
    // The gesture chain from content script button click through
    // sendMessage is NOT guaranteed by Chrome (RESEARCH.md Pitfall 1).
    // Background handler calls openPopup() and returns success/failure.
    // On failure, content script shows in-page notification.
    try {
      const response = await chrome.runtime.sendMessage({ action: 'open-popup-gmail' });
      if (!response || !response.ok) {
        showInPageNotification('Capture stored — click the Second Brain extension icon to review and save.');
      }
    } catch (err) {
      showInPageNotification('Capture stored — click the Second Brain extension icon to review and save.');
    }
  };

  // Insert button into thread toolbar area or prepend to threadView
  const toolbar = threadView.querySelector('[role="toolbar"]');
  if (toolbar) {
    toolbar.appendChild(btn);
  } else {
    threadView.prepend(btn);
  }
}

function showInPageNotification(message) {
  // Remove any existing notification
  document.querySelector('#sb-gmail-notification')?.remove();
  const notification = document.createElement('div');
  notification.id = 'sb-gmail-notification';
  notification.textContent = message;
  Object.assign(notification.style, {
    position: 'fixed',
    bottom: '20px',
    right: '20px',
    zIndex: '10000',
    background: '#1a73e8',
    color: 'white',
    padding: '12px 20px',
    borderRadius: '8px',
    fontSize: '14px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
    maxWidth: '400px',
    cursor: 'pointer',
  });
  notification.onclick = () => notification.remove();
  document.body.appendChild(notification);
  setTimeout(() => notification.remove(), 8000);
}

function extractGmailThread() {
  // Subject: look for h2 in thread view or document title minus " - Gmail"
  const subjectEl = document.querySelector('[data-thread-id] h2')
    || document.querySelector('[role="main"] h2');
  const subject = subjectEl?.textContent?.trim()
    || document.title.replace(/ - .*$/, '').trim();

  // Messages: each message in thread has role="listitem" or data-legacy-message-id
  const messages = [];
  const msgEls = document.querySelectorAll('[data-legacy-message-id], [data-message-id]');

  msgEls.forEach(el => {
    // Sender: look for [email] attribute or first span in header
    const senderEl = el.querySelector('[email]') || el.querySelector('[data-hovercard-id]');
    const sender = senderEl?.getAttribute('email')
      || senderEl?.getAttribute('data-hovercard-id')
      || senderEl?.textContent?.trim() || 'Unknown';

    // Date: look for [title] attribute on date element (Gmail uses title for full timestamp)
    const dateEl = el.querySelector('[title]');
    const date = dateEl?.getAttribute('title') || '';

    // Body: get the message body text
    const bodyEl = el.querySelector('[data-message-id] > div')
      || el.querySelector('.a3s') // fallback to common Gmail body class
      || el;
    const bodyText = bodyEl?.innerText?.trim() || '';

    messages.push({ sender, date, body: bodyText });
  });

  // Recipients: extract from first message's header (To: line)
  // This is best-effort — Gmail doesn't expose recipients in a reliable attribute
  const recipientEls = document.querySelectorAll('[data-hovercard-id]');
  const recipients = [...new Set(
    Array.from(recipientEls)
      .map(el => el.getAttribute('data-hovercard-id') || el.textContent?.trim())
      .filter(Boolean)
  )];

  // Compose full body as markdown
  const fullBody = messages.map((m, i) =>
    `### Message ${i + 1}\n**From:** ${m.sender}\n**Date:** ${m.date}\n\n${m.body}`
  ).join('\n\n---\n\n');

  return {
    subject,
    sender: messages[0]?.sender || 'Unknown',
    recipients,
    date: messages[0]?.date || new Date().toISOString(),
    fullBody,
    messageCount: messages.length,
  };
}
