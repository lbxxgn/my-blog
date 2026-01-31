// Popup controller

console.log('Popup loaded');

const API_BASE = 'http://localhost:5001';

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

// Get API key from storage
function getAPIKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiKey'], (result) => {
      resolve(result.apiKey);
    });
  });
}

async function loadRecentCaptures() {
  const container = document.getElementById('recentCaptures');

  // Show loading state
  container.innerHTML = '<p class="empty-state">Loading...</p>';

  try {
    const apiKey = await getAPIKey();

    if (!apiKey) {
      container.innerHTML = '<p class="empty-state">Please configure API key in settings</p>';
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

    const response = await fetch(`${API_BASE}/api/plugin/recent?limit=5`, {
      headers: {
        'X-API-Key': apiKey
      },
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success || data.cards.length === 0) {
      container.innerHTML = '<p class="empty-state">No recent captures</p>';
      return;
    }

    container.innerHTML = data.cards.map(card => `
      <div class="capture-item" data-id="${card.id}">
        <h4>${escapeHtml(card.title)}</h4>
        <p class="preview">${escapeHtml(truncateContent(card.content, 100))}</p>
        <span class="time">${formatTime(card.created_at)}</span>
      </div>
    `).join('');

  } catch (error) {
    console.error('Failed to load recent captures:', error);
    if (error.name === 'AbortError') {
      container.innerHTML = '<p class="empty-state">Loading timed out</p>';
    } else {
      container.innerHTML = '<p class="empty-state">Failed to load captures</p>';
    }
  }
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
      loadRecentCaptures(); // Reload captures after setting key
    });
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function truncateContent(content, maxLength) {
  if (!content) return '';

  // Remove "Source: ..." prefix if present
  const lines = content.split('\n\n');
  const actualContent = lines.length > 1 ? lines.slice(1).join('\n\n') : content;

  if (actualContent.length <= maxLength) {
    return actualContent;
  }

  return actualContent.substring(0, maxLength) + '...';
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
