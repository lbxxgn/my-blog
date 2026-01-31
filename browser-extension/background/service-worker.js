// Service Worker for browser extension

console.log('Knowledge Base Extension Service Worker loaded');

const DEFAULT_API_URL = 'http://localhost:5001';
const REQUEST_TIMEOUT = 10000; // 10 seconds

// ==================== Helper Functions ====================

// Get API base URL from storage
async function getAPIBaseURL() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiUrl'], (result) => {
      resolve(result.apiUrl || DEFAULT_API_URL);
    });
  });
}

// Fetch with timeout
async function fetchWithTimeout(url, options = {}, timeout = REQUEST_TIMEOUT) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout}ms`);
    }
    throw error;
  }
}

// ==================== API Client Functions ====================

// Get API key from storage
async function getAPIKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiKey'], (result) => {
      resolve(result.apiKey);
    });
  });
}

// Submit content to backend
async function submitContent(data) {
  console.log('🔑 Getting API key...');
  const apiKey = await getAPIKey();
  const apiUrl = await getAPIBaseURL();
  console.log('🔑 API key found:', apiKey ? 'Yes' : 'No');
  console.log('🌐 API URL:', apiUrl);

  if (!apiKey) {
    console.error('❌ API key not configured!');
    throw new Error('API key not configured. Please set your API key in extension settings.');
  }

  console.log('🌐 Sending request to:', `${apiUrl}/api/plugin/submit`);
  console.log('📦 Data:', data);

  const response = await fetchWithTimeout(`${apiUrl}/api/plugin/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey
    },
    body: JSON.stringify(data)
  });

  console.log('📡 Response status:', response.status);

  if (!response.ok) {
    console.error('❌ API request failed:', response.status, response.statusText);
    throw new Error(`API error: ${response.status} - ${response.statusText}`);
  }

  const result = await response.json();
  console.log('✅ API response:', result);
  return result;
}

// Sync annotations to backend
async function syncAnnotations(url, annotations) {
  const apiKey = await getAPIKey();
  const apiUrl = await getAPIBaseURL();

  if (!apiKey) {
    throw new Error('API key not configured');
  }

  const response = await fetchWithTimeout(`${apiUrl}/api/plugin/sync-annotations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey
    },
    body: JSON.stringify({ url, annotations })
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Get annotations from backend
async function getAnnotations(url) {
  const apiKey = await getAPIKey();
  const apiUrl = await getAPIBaseURL();

  if (!apiKey) {
    throw new Error('API key not configured');
  }

  const response = await fetchWithTimeout(`${apiUrl}/api/plugin/annotations?url=${encodeURIComponent(url)}`, {
    method: 'GET',
    headers: {
      'X-API-Key': apiKey
    }
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// ==================== Service Worker Events ====================

// Install event
self.addEventListener('install', (event) => {
  console.log('Extension installed');
  self.skipWaiting();
});

// Activate event
self.addEventListener('activate', (event) => {
  console.log('Extension activated');
  event.waitUntil(self.clients.claim());
});

// Handle messages from content scripts and popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('📨 Service Worker received message:', request);
  console.log('📨 Action:', request.action);

  if (request.action === 'submitContent') {
    console.log('📨 Processing submitContent with data:', request.data);

    // Call API function directly (no dynamic import)
    submitContent(request.data)
      .then(response => {
        console.log('✅ Submit successful:', response);
        sendResponse({success: true, data: response});
      })
      .catch(error => {
        console.error('❌ Submit failed:', error);
        sendResponse({success: false, error: error.message});
      });

    return true; // Keep message channel open for async response
  }

  if (request.action === 'getAnnotations') {
    getAnnotations(request.url)
      .then(annotations => sendResponse({success: true, annotations}))
      .catch(error => sendResponse({success: false, error: error.message}));
    return true;
  }

  // Unknown action
  console.warn('⚠️ Unknown action:', request.action);
  return false;
});
