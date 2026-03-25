'use strict';

const DEFAULT_API_URL = 'http://127.0.0.1:37491';

async function loadOptions() {
  const { apiUrl, defaultTags } = await chrome.storage.sync.get({
    apiUrl: DEFAULT_API_URL,
    defaultTags: '',
  });
  document.getElementById('apiUrl').value = apiUrl;
  document.getElementById('defaultTags').value = defaultTags;
}

async function saveOptions() {
  const apiUrl = document.getElementById('apiUrl').value.trim() || DEFAULT_API_URL;
  const defaultTags = document.getElementById('defaultTags').value.trim();

  await chrome.storage.sync.set({ apiUrl, defaultTags });

  const status = document.getElementById('status');
  status.textContent = 'Saved!';
  setTimeout(() => { status.textContent = ''; }, 1500);
}

document.addEventListener('DOMContentLoaded', loadOptions);
document.getElementById('saveBtn').addEventListener('click', saveOptions);
