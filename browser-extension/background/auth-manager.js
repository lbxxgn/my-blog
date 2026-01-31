// Authentication manager for API key

// Save API key
export async function setAPIKey(apiKey) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ apiKey }, () => {
      console.log('API key saved');
      resolve(true);
    });
  });
}

// Get API key
export async function getAPIKey() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['apiKey'], (result) => {
      resolve(result.apiKey || null);
    });
  });
}

// Clear API key
export async function clearAPIKey() {
  return new Promise((resolve) => {
    chrome.storage.local.remove(['apiKey'], () => {
      console.log('API key cleared');
      resolve(true);
    });
  });
}

// Validate API key with backend
export async function validateAPIKey(apiKey) {
  const API_BASE = 'http://localhost:5001/knowledge_base';

  try {
    const response = await fetch(`${API_BASE}/api/plugin/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      }
    });

    return response.ok;
  } catch (error) {
    console.error('Validation error:', error);
    return false;
  }
}
