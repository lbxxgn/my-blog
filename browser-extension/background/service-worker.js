// Service Worker for browser extension

console.log('Knowledge Base Extension Service Worker loaded');

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
  console.log('Received message:', request);

  if (request.action === 'submitContent') {
    // Forward to API client
    import('./api-client.js').then(module => {
      module.submitContent(request.data)
        .then(response => sendResponse({success: true, data: response}))
        .catch(error => sendResponse({success: false, error: error.message}));
    });
    return true; // Keep message channel open for async response
  }

  if (request.action === 'getAnnotations') {
    import('./api-client.js').then(module => {
      module.getAnnotations(request.url)
        .then(annotations => sendResponse({success: true, annotations}))
        .catch(error => sendResponse({success: false, error: error.message}));
    });
    return true;
  }
});
