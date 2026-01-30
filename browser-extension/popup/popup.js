// Popup controller

console.log('Popup loaded');

document.addEventListener('DOMContentLoaded', () => {
  init();
});

function init() {
  loadRecentCaptures();
  setupEventListeners();
  checkAPIKeyStatus();
}

function setupEventListeners() {
  document.getElementById('quickNoteBtn').addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://localhost:5001/quick-note' });
  });

  document.getElementById('settingsBtn').addEventListener('click', () => {
    showSettingsDialog();
  });
}

async function loadRecentCaptures() {
  // This would fetch from backend or local storage
  // For now, show placeholder
  const container = document.getElementById('recentCaptures');

  // Try to get from local storage
  chrome.storage.local.get(['recentCaptures'], (result) => {
    const captures = result.recentCaptures || [];

    if (captures.length === 0) {
      container.innerHTML = '<p class="empty-state">No recent captures</p>';
      return;
    }

    container.innerHTML = captures.map(capture => `
      <div class="capture-item" data-id="${capture.id}">
        <h4>${escapeHtml(capture.title)}</h4>
        <p class="preview">${escapeHtml(capture.content.substring(0, 100))}...</p>
        <span class="time">${formatTime(capture.created_at)}</span>
      </div>
    `).join('');
  });
}

function checkAPIKeyStatus() {
  const statusEl = document.getElementById('syncStatus');

  chrome.storage.local.get(['apiKey'], (result) => {
    if (result.apiKey) {
      statusEl.className = 'status-indicator status-ok';
      statusEl.title = 'Connected';
    } else {
      statusEl.className = 'status-indicator status-error';
      statusEl.title = 'Not configured - click settings to setup';
    }
  });
}

function showSettingsDialog() {
  const apiKey = prompt('Enter your API Key (from Knowledge Base settings):');

  if (apiKey) {
    chrome.storage.local.set({ apiKey }, () => {
      alert('API Key saved!');
      checkAPIKeyStatus();
    });
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
}
