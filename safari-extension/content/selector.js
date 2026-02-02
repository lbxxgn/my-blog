// Text selection handler

export default class Selector {
  constructor() {
    this.init();
  }

  init() {
    // Listen for text selection
    document.addEventListener('mouseup', () => this.handleSelection());
    document.addEventListener('touchend', () => this.handleSelection());
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
