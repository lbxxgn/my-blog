// Popup controller

console.log('Popup loaded');

// Default API URL
const DEFAULT_API_URL = 'http://localhost:5001';

document.addEventListener('DOMContentLoaded', () => {
  init();
});

async function init() {
  await loadSettings();
  setupEventListeners();
  loadRecentCaptures();
  checkAPIKeyStatus();
}

async function loadSettings() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiUrl', 'apiKey'], (result) => {
      const apiUrl = result.apiUrl || DEFAULT_API_URL;
      const apiKey = result.apiKey || '';

      document.getElementById('apiUrl').value = apiUrl;
      document.getElementById('apiKeyInput').value = apiKey;

      resolve();
    });
  });
}

function setupEventListeners() {
  document.getElementById('quickNoteBtn').addEventListener('click', () => {
    chrome.storage.local.get(['apiUrl'], (result) => {
      const apiUrl = result.apiUrl || DEFAULT_API_URL;
      chrome.tabs.create({ url: `${apiUrl}/quick-note` });
    });
  });

  document.getElementById('knowledgeBaseBtn').addEventListener('click', () => {
    chrome.storage.local.get(['apiUrl'], (result) => {
      const apiUrl = result.apiUrl || DEFAULT_API_URL;
      chrome.tabs.create({ url: `${apiUrl}/timeline` });
    });
  });

  document.getElementById('settingsBtn').addEventListener('click', showSettingsModal);

  document.getElementById('closeModal').addEventListener('click', hideSettingsModal);

  document.getElementById('saveSettings').addEventListener('click', saveSettings);

  document.getElementById('testConnection').addEventListener('click', testConnection);

  // Close modal when clicking outside
  document.getElementById('settingsModal').addEventListener('click', (e) => {
    if (e.target.id === 'settingsModal') {
      hideSettingsModal();
    }
  });
}

function showSettingsModal() {
  document.getElementById('settingsModal').style.display = 'flex';
}

function hideSettingsModal() {
  document.getElementById('settingsModal').style.display = 'none';
}

async function saveSettings() {
  const apiUrl = document.getElementById('apiUrl').value.trim();
  const apiKey = document.getElementById('apiKeyInput').value.trim();

  // Validate API URL format
  let validatedUrl = apiUrl;
  if (apiUrl && !apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
    validatedUrl = 'https://' + apiUrl;
  }

  const settings = {
    apiUrl: validatedUrl || DEFAULT_API_URL,
    apiKey: apiKey
  };

  chrome.storage.local.set(settings, () => {
    // Update UI
    document.getElementById('apiUrl').value = validatedUrl;
    checkAPIKeyStatus();
    loadRecentCaptures();

    // Show success message
    alert('设置已保存！');
    hideSettingsModal();
  });
}

async function testConnection() {
  const apiUrl = document.getElementById('apiUrl').value.trim();
  const apiKey = document.getElementById('apiKeyInput').value.trim();

  if (!apiUrl) {
    alert('请输入 API 地址');
    return;
  }

  // Update status to testing
  updateConnectionStatus('testing', '正在测试连接...');

  try {
    let validatedUrl = apiUrl;
    if (!apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
      validatedUrl = 'https://' + apiUrl;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    const testUrl = `${validatedUrl}/api/plugin/recent?limit=1`;

    const response = await fetch(testUrl, {
      method: 'GET',
      headers: apiKey ? { 'X-API-Key': apiKey } : {},
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (response.ok || response.status === 401) {
      // 401 means server is reachable but auth failed (expected if no API key)
      updateConnectionStatus('success', '连接成功！');
      document.getElementById('apiUrl').value = validatedUrl;
    } else {
      updateConnectionStatus('error', `连接失败: HTTP ${response.status}`);
    }
  } catch (error) {
    updateConnectionStatus('error', `连接失败: ${error.message}`);
  }
}

function updateConnectionStatus(status, text) {
  const statusEl = document.getElementById('connectionStatus');
  const dot = statusEl.querySelector('.status-dot');
  const textEl = statusEl.querySelector('.status-text');

  // Remove all status classes
  dot.classList.remove('testing', 'success', 'error');

  // Add new status class
  dot.classList.add(status);
  textEl.textContent = text;
}

// Get API base URL from storage
async function getAPIBaseURL() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiUrl'], (result) => {
      resolve(result.apiUrl || DEFAULT_API_URL);
    });
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
  const apiUrl = await getAPIBaseURL();

  // Show loading state
  container.innerHTML = '<p class="empty-state">Loading...</p>';

  try {
    const apiKey = await getAPIKey();

    if (!apiKey) {
      container.innerHTML = '<p class="empty-state">请配置 API 密钥</p>';
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${apiUrl}/api/plugin/recent?limit=5`, {
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
      container.innerHTML = '<p class="empty-state">暂无捕获内容</p>';
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
    container.innerHTML = '<p class="empty-state">加载失败</p>';
  }
}

function checkAPIKeyStatus() {
  const statusEl = document.getElementById('syncStatus');

  chrome.storage.local.get(['apiKey'], (result) => {
    if (result.apiKey) {
      statusEl.className = 'status-indicator status-ok';
      statusEl.title = '已配置';
    } else {
      statusEl.className = 'status-indicator status-error';
      statusEl.title = '未配置 - 点击设置';
    }
  });
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

  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  return date.toLocaleDateString();
}
