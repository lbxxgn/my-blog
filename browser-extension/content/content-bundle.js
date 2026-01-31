// Content script for web page interaction
// All-in-one bundle for better compatibility (no ES6 imports)

console.log('Knowledge Base Content Script loaded');

// ==================== Selector Class ====================
class Selector {
  constructor() {
    this.selectionTimeout = null;
    this.init();
  }

  init() {
    // Listen for text selection with debouncing
    const handleSelectionDebounced = () => {
      clearTimeout(this.selectionTimeout);
      this.selectionTimeout = setTimeout(() => this.handleSelection(), 150);
    };

    document.addEventListener('mouseup', handleSelectionDebounced);
    document.addEventListener('touchend', handleSelectionDebounced);
  }

  handleSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (selectedText.length > 0) {
      console.log('Text selected:', selectedText);
      // Notify toolbar to show
      this.showToolbar(selection);
    } else {
      this.hideToolbar();
    }
  }

  showToolbar(selection) {
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    // Send event to toolbar
    const event = new CustomEvent('kb:showToolbar', {
      detail: {
        text: selection.toString(),
        rect: rect,
        x: rect.left + rect.width / 2,
        y: rect.top - 50
      }
    });

    document.dispatchEvent(event);
  }

  hideToolbar() {
    const event = new CustomEvent('kb:hideToolbar');
    document.dispatchEvent(event);
  }

  getSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (selectedText.length === 0) {
      return null;
    }

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    return {
      text: selectedText,
      rect: rect,
      x: rect.left + rect.width / 2,
      y: rect.top - 50
    };
  }
}

// ==================== Toolbar Class ====================
class Toolbar {
  constructor() {
    this.toolbar = null;
    this.currentSelection = null;
    this.init();
  }

  init() {
    // Create toolbar element
    this.toolbar = document.createElement('div');
    this.toolbar.className = 'kb-toolbar';
    this.toolbar.style.display = 'none';
    document.body.appendChild(this.toolbar);

    // Add buttons
    this.addButton('📌', 'Save to knowledge base', () => this.handleSave());
    this.addButton('🏷️', 'Add tags', () => this.handleWithTags());
    this.addButton('✏️', 'Add note', () => this.handleWithNote());

    // Listen for toolbar events
    document.addEventListener('kb:showToolbar', (e) => this.show(e.detail));
    document.addEventListener('kb:hideToolbar', () => this.hide());
  }

  addButton(emoji, title, handler) {
    const btn = document.createElement('button');
    btn.className = 'kb-toolbar-btn';
    btn.innerHTML = emoji;
    btn.title = title;
    btn.onclick = handler;
    this.toolbar.appendChild(btn);
  }

  show(detail) {
    this.currentSelection = detail;
    this.toolbar.style.display = 'block';
    const toolbarRect = this.toolbar.getBoundingClientRect();
    const toolbarWidth = toolbarRect.width || 150;
    const toolbarHeight = toolbarRect.height || 50;

    // Calculate position with viewport bounds checking
    let x = detail.x - toolbarWidth / 2;
    let y = detail.y - toolbarHeight;

    // Keep within horizontal bounds
    const minX = 10;
    const maxX = window.innerWidth - toolbarWidth - 10;
    x = Math.max(minX, Math.min(x, maxX));

    // Keep within vertical bounds
    const minY = 10;
    const maxY = window.innerHeight - toolbarHeight - 10;
    y = Math.max(minY, Math.min(y, maxY));

    this.toolbar.style.left = `${x}px`;
    this.toolbar.style.top = `${y}px`;
  }

  hide() {
    this.toolbar.style.display = 'none';
    this.currentSelection = null;
  }

  handleSave() {
    if (!this.currentSelection) return;

    const content = {
      title: document.title,
      content: this.currentSelection.text,
      source_url: window.location.href,
      tags: []
    };

    this.submitToBackend(content);
    this.hide();
  }

  handleWithTags() {
    if (!this.currentSelection) return;

    const tags = prompt('Enter tags separated by commas:');
    if (!tags) return;

    const content = {
      title: document.title,
      content: this.currentSelection.text,
      source_url: window.location.href,
      tags: tags.split(',').map(t => t.trim()).filter(t => t)
    };

    this.submitToBackend(content);
    this.hide();
  }

  handleWithNote() {
    if (!this.currentSelection) return;

    const note = prompt('Add a note (optional):');
    if (!note) return;

    const content = {
      title: document.title,
      content: this.currentSelection.text + '\n\nNote: ' + note,
      source_url: window.location.href,
      tags: []
    };

    this.submitToBackend(content);
    this.hide();
  }

  async submitToBackend(content) {
    try {
      console.log('📤 Sending message to background script...');

      // Send message to background script with robust retry logic
      let response;
      let lastError;

      // Retry up to 3 times with exponential backoff
      for (let attempt = 1; attempt <= 3; attempt++) {
        try {
          response = await chrome.runtime.sendMessage({
            action: 'submitContent',
            data: content
          });
          // If successful, break out of retry loop
          break;
        } catch (retryError) {
          lastError = retryError;

          // Check if it's a context invalidated error
          if (retryError.message && retryError.message.includes('Extension context invalidated')) {
            console.warn('⚠️ Extension context invalidated, attempt ' + attempt + '/3...');

            // If this was the last attempt, give up
            if (attempt >= 3) {
              throw new Error('Service Worker not responding after 3 retries. Please reload the extension.');
            }

            // Exponential backoff: 500ms, 1000ms, 2000ms
            const delay = 500 * attempt;
            console.log('⏳ Waiting ' + delay + 'ms before retry...');
            await new Promise(resolve => setTimeout(resolve, delay));
          } else {
            // Not a context error, don't retry
            throw retryError;
          }
        }
      }

      console.log('📥 Received response:', response);

      if (response && response.success) {
        this.showNotification('✅ Saved to knowledge base!');
        console.log('✅ Saved successfully:', response.data);
      } else if (response) {
        this.showNotification('❌ Failed: ' + (response.error || 'Unknown error'));
        console.error('❌ Save failed:', response.error);
      } else {
        this.showNotification('❌ No response from extension');
        console.error('❌ No response received');
      }
    } catch (error) {
      this.showNotification('❌ Error: ' + error.message);
      console.error('❌ Exception caught:', error);

      // If all retries failed, show reload instructions
      if (error.message && error.message.includes('Service Worker not responding')) {
        this.showNotification('💡 请在 chrome://extensions/ 页面刷新扩展');
      }
    }
  }

  showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'kb-notification';
    notification.textContent = message;
    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #333; color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000; animation: kb-slide-in 0.3s ease-out;';

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
}

// ==================== Initialize ====================
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

console.log('Knowledge Base Extension initialized');
