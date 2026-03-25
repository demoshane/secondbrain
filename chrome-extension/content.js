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

// ── Gmail Integration (Plan 36-03) ────────────────────────────────────────────
// Gmail-specific features are handled in Plan 36-03.
// This file loads on gmail.google.com but the Gmail capture logic will be added in the next plan.
