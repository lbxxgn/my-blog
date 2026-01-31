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
  console.log('📨 Service Worker received message:', request);
  console.log('📨 Action:', request.action);

  if (request.action === 'submitContent') {
    console.log('📨 Processing submitContent with data:', request.data);

    // Forward to API client
    import('./api-client.js').then(module => {
      console.log('📦 API client module loaded');

      module.submitContent(request.data)
        .then(response => {
          console.log('✅ Submit successful:', response);
          sendResponse({success: true, data: response});
        })
        .catch(error => {
          console.error('❌ Submit failed:', error);
          sendResponse({success: false, error: error.message});
        });
    }).catch(error => {
      console.error('❌ Failed to load API client:', error);
      sendResponse({success: false, error: 'Failed to load API client'});
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

  // Unknown action
  console.warn('⚠️ Unknown action:', request.action);
  return false;
});
