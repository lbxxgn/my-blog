// API client for communicating with backend

const API_BASE = 'http://localhost:5001';

// Get API key from storage
async function getAPIKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiKey'], (result) => {
      resolve(result.apiKey);
    });
  });
}

// Submit content to backend
export async function submitContent(data) {
  const apiKey = await getAPIKey();

  if (!apiKey) {
    throw new Error('API key not configured. Please set your API key in extension settings.');
  }

  const response = await fetch(`${API_BASE}/api/plugin/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Sync annotations to backend
export async function syncAnnotations(url, annotations) {
  const apiKey = await getAPIKey();

  if (!apiKey) {
    throw new Error('API key not configured');
  }

  const response = await fetch(`${API_BASE}/api/plugin/sync-annotations`, {
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
export async function getAnnotations(url) {
  const apiKey = await getAPIKey();

  if (!apiKey) {
    throw new Error('API key not configured');
  }

  const response = await fetch(`${API_BASE}/api/plugin/annotations?url=${encodeURIComponent(url)}`, {
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
