// Floating toolbar for quick actions

export default class Toolbar {
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

    // Position toolbar
    this.toolbar.style.left = `${detail.x}px`;
    this.toolbar.style.top = `${detail.y}px`;
    this.toolbar.style.display = 'block';
  }

  hide() {
    this.toolbar.style.display = 'none';
    this.currentSelection = null;
  }

  async saveSelection() {
    const content = {
      title: document.title,
      content: this.currentSelection.text,
      source_url: window.location.href,
      tags: [],
      annotation_type: 'capture'
    };

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
      // Send message to background script
      const response = await chrome.runtime.sendMessage({
        action: 'submitContent',
        data: content
      });

      if (response.success) {
        this.showNotification('✅ Saved to knowledge base!');
        console.log('Saved:', response.data);
      } else {
        this.showNotification('❌ Failed to save');
        console.error('Error:', response.error);
      }
    } catch (error) {
      this.showNotification('❌ Error: ' + error.message);
      console.error('Error:', error);
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
