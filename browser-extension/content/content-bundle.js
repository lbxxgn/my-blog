// Content script for web page interaction
// All-in-one bundle for better compatibility

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

    if (!selectedText) {
      return null;
    }

    return {
      text: selectedText,
      html: selection.getRangeAt(0).cloneContents(),
      url: window.location.href,
      title: document.title
    };
  }

  clearSelection() {
    window.getSelection().removeAllRanges();
  }
}

// ==================== Toolbar Class ====================
class Toolbar {
  constructor() {
    this.toolbar = null;
    this.init();
  }

  init() {
    // Create toolbar element
    this.createToolbar();

    // Listen for show/hide events
    document.addEventListener('kb:showToolbar', (e) => this.show(e.detail));
    document.addEventListener('kb:hideToolbar', () => this.hide());
  }

  createToolbar() {
    this.toolbar = document.createElement('div');
    this.toolbar.className = 'kb-toolbar';
    this.toolbar.innerHTML = `
      <button class="kb-btn kb-btn-save" title="保存">📌</button>
      <button class="kb-btn kb-btn-tag" title="保存并添加标签">🏷️</button>
      <button class="kb-btn kb-btn-note" title="保存并添加备注">✏️</button>
      <button class="kb-btn kb-btn-close" title="关闭">❌</button>
    `;

    // Attach event listeners
    this.toolbar.querySelector('.kb-btn-save').addEventListener('click', () => this.saveSelection());
    this.toolbar.querySelector('.kb-btn-tag').addEventListener('click', () => this.saveWithTags());
    this.toolbar.querySelector('.kb-btn-note').addEventListener('click', () => this.saveWithNote());
    this.toolbar.querySelector('.kb-btn-close').addEventListener('click', () => this.hide());

    document.body.appendChild(this.toolbar);
  }

  show(detail) {
    this.currentSelection = detail;

    // Get toolbar dimensions (after it's displayed)
    this.toolbar.style.display = 'block';
    const toolbarRect = this.toolbar.getBoundingClientRect();
    const toolbarWidth = toolbarRect.width || 150; // Approximate width
    const toolbarHeight = toolbarRect.height || 50;

    // Calculate position with viewport bounds checking
    let x = detail.x - toolbarWidth / 2;
    let y = detail.y - toolbarHeight;

    // Keep within horizontal bounds
    const minX = 10;
    const maxX = window.innerWidth - toolbarWidth - 10;
    x = Math.max(minX, Math.min(x, maxX));

    // Keep within vertical bounds (don't go above or below viewport)
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

  async saveSelection() {
    console.log('💾 Save button clicked!');
    console.log('Selected text:', this.currentSelection.text);

    const content = {
      title: document.title,
      content: this.currentSelection.text,
      source_url: window.location.href,
      tags: [],
      annotation_type: 'capture'
    };

    console.log('Sending to backend:', content);
    await this.submitToBackend(content);
    this.hide();
  }

  async saveWithTags() {
    const tags = prompt('Enter tags (comma separated):');
    if (!tags) return;

    const content = {
      title: document.title,
      content: this.currentSelection.text,
      source_url: window.location.href,
      tags: tags.split(',').map(t => t.trim()),
      annotation_type: 'capture'
    };

    await this.submitToBackend(content);
    this.hide();
  }

  async saveWithNote() {
    const note = prompt('Add a note:');
    if (!note) return;

    const content = {
      title: document.title,
      content: `${this.currentSelection.text}\n\nNote: ${note}`,
      source_url: window.location.href,
      tags: ['note'],
      annotation_type: 'note'
    };

    await this.submitToBackend(content);
    this.hide();
  }

  async submitToBackend(content) {
    try {
      console.log('📤 Sending message to background script...');

      // Send message to background script
      const response = await chrome.runtime.sendMessage({
        action: 'submitContent',
        data: content
      });

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
    }
  }

  showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'kb-notification';
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #333;
      color: white;
      padding: 12px 20px;
      border-radius: 4px;
      z-index: 10000;
      animation: kb-slide-in 0.3s ease-out;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
}

// ==================== Initialize ====================
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

console.log('Knowledge Base Extension initialized');
