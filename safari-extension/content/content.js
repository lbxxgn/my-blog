// Content script for web page interaction

console.log('Knowledge Base Content Script loaded');

import Selector from './selector.js';
import Toolbar from './toolbar.js';

// Initialize components
const selector = new Selector();
const toolbar = new Toolbar();

// Listen for messages from background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getSelectedContent') {
    const selection = selector.getSelection();
    sendResponse({ success: true, data: selection });
  }
  return true;
});
