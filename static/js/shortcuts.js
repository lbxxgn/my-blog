/**
 * 全局快捷键处理
 * 支持跨平台的快捷键（Mac使用 Cmd，Windows/Linux 使用 Ctrl）
 */

class ShortcutHandler {
    constructor() {
        this.shortcuts = new Map();
        this.init();
    }

    init() {
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    }

    /**
     * 注册快捷键
     * @param {string} key - 快捷键组合，例如 'Ctrl+S', 'Cmd+K'
     * @param {Function} callback - 回调函数
     * @param {string} description - 快捷键描述
     */
    register(key, callback, description = '') {
        this.shortcuts.set(key.toLowerCase(), { callback, description });
    }

    /**
     * 处理键盘事件
     */
    handleKeyDown(e) {
        const key = this.getKeyString(e);
        const shortcut = this.shortcuts.get(key);

        if (shortcut) {
            e.preventDefault();
            e.stopPropagation();
            shortcut.callback(e);
        }
    }

    /**
     * 获取按键字符串
     */
    getKeyString(e) {
        const parts = [];

        // 检测修饰键
        if (e.ctrlKey && !e.metaKey) parts.push('ctrl');
        if (e.metaKey && !e.ctrlKey) parts.push('cmd');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');

        // 主键
        let key = e.key.toLowerCase();

        // 特殊键映射
        const keyMap = {
            ' ': 'space',
            'escape': 'esc',
            'arrowup': 'up',
            'arrowdown': 'down',
            'arrowleft': 'left',
            'arrowright': 'right'
        };

        if (keyMap[key]) {
            key = keyMap[key];
        }

        parts.push(key);

        return parts.join('+');
    }

    /**
     * 获取所有已注册的快捷键
     */
    getShortcuts() {
        return Array.from(this.shortcuts.entries()).map(([key, value]) => ({
            key: this.formatKey(key),
            description: value.description
        }));
    }

    /**
     * 格式化快捷键显示
     */
    formatKey(key) {
        return key
            .replace('ctrl', 'Ctrl')
            .replace('cmd', 'Cmd⌘')
            .replace('shift', 'Shift')
            .replace('alt', 'Alt')
            .replace('esc', 'Esc')
            .split('+')
            .join('+');
    }
}

// 创建全局快捷键处理器实例
const shortcutHandler = new ShortcutHandler();

// 页面加载完成后注册快捷键
document.addEventListener('DOMContentLoaded', () => {
    const currentPage = document.body.dataset.page || 'home';

    // 通用快捷键（所有页面）
    shortcutHandler.register('ctrl+k', () => {
        // 打开快速搜索
        const searchInput = document.querySelector('.search-input-nav, input[name="q"], input[placeholder*="搜索"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }, '打开搜索');

    shortcutHandler.register('ctrl+/', () => {
        // 显示快捷键帮助
        showShortcutHelp();
    }, '显示快捷键帮助');

    // 根据页面类型注册特定快捷键
    switch (currentPage) {
        case 'editor':
            registerEditorShortcuts();
            break;
        case 'quick_note':
            registerQuickNoteShortcuts();
            break;
        case 'admin':
            registerAdminShortcuts();
            break;
        case 'timeline':
            registerTimelineShortcuts();
            break;
    }
});

/**
 * 编辑器页面快捷键
 */
function registerEditorShortcuts() {
    // 保存
    shortcutHandler.register('ctrl+s', () => {
        const saveBtn = document.querySelector('#saveBtn, button[type="submit"]');
        if (saveBtn) {
            saveBtn.click();
        }
    }, '保存文章');

    // 快速保存（不关闭）
    shortcutHandler.register('ctrl+shift+s', () => {
        // AJAX 保存草稿
        saveDraft();
    }, '保存草稿');

    // 切换预览
    shortcutHandler.register('ctrl+p', () => {
        togglePreview();
    }, '切换预览');

    // AI生成标签
    shortcutHandler.register('ctrl+shift+t', () => {
        if (typeof generateAITags === 'function') {
            generateAITags();
        }
    }, 'AI生成标签');

    // 关闭编辑器
    shortcutHandler.register('esc', () => {
        if (confirm('确定要离开编辑器吗？未保存的内容将丢失。')) {
            window.history.back();
        }
    }, '关闭编辑器');

    // 格式化快捷键（Quill编辑器）
    const editor = document.querySelector('.ql-editor');
    if (editor) {
        // Quill已经处理了大部分编辑快捷键
        // 这里添加一些自定义的
        shortcutHandler.register('ctrl+d', () => {
            // 插入当前日期
            const date = new Date().toLocaleDateString('zh-CN');
            insertAtCursor(date);
        }, '插入日期');
    }
}

/**
 * 快速记事页面快捷键
 */
function registerQuickNoteShortcuts() {
    // 保存
    shortcutHandler.register('ctrl+s', () => {
        const form = document.getElementById('quick-note-form');
        if (form) {
            form.dispatchEvent(new Event('submit'));
        }
    }, '快速保存');

    // 清空
    shortcutHandler.register('ctrl+shift+d', () => {
        const clearBtn = document.getElementById('clear-btn');
        if (clearBtn) {
            clearBtn.click();
        }
    }, '清空内容');

    // 新建笔记
    shortcutHandler.register('ctrl+n', () => {
        // 清空表单准备新建
        document.getElementById('title').value = '';
        document.getElementById('content').value = '';
        document.getElementById('content').focus();
    }, '新建笔记');
}

/**
 * 管理后台快捷键
 */
function registerAdminShortcuts() {
    // 新建文章
    shortcutHandler.register('ctrl+n', () => {
        const newPostBtn = document.querySelector('a[href*="/new"]');
        if (newPostBtn) {
            window.location.href = newPostBtn.href;
        }
    }, '新建文章');

    // 快速记事
    shortcutHandler.register('ctrl+shift+n', () => {
        const quickNoteBtn = document.querySelector('a[href*="quick_note"]');
        if (quickNoteBtn) {
            window.location.href = quickNoteBtn.href;
        }
    }, '打开快速记事');

    // 刷新列表
    shortcutHandler.register('ctrl+r', () => {
        location.reload();
    }, '刷新页面');
}

/**
 * 时间线页面快捷键
 */
function registerTimelineShortcuts() {
    // 快速记事
    shortcutHandler.register('ctrl+n', () => {
        const quickNoteBtn = document.querySelector('a[href*="quick_note"]');
        if (quickNoteBtn) {
            window.location.href = quickNoteBtn.href;
        }
    }, '新建笔记');

    // 筛选
    shortcutHandler.register('ctrl+f', () => {
        const filterInput = document.querySelector('input[placeholder*="筛选"]');
        if (filterInput) {
            filterInput.focus();
        }
    }, '筛选内容');

    // 刷新
    shortcutHandler.register('ctrl+r', () => {
        location.reload();
    }, '刷新时间线');
}

/**
 * 保存草稿（AJAX）
 */
function saveDraft() {
    const form = document.getElementById('editorForm');
    if (!form) return;

    const formData = new FormData(form);
    formData.set('is_published', 'false');

    fetch(form.action, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('草稿已保存', 'success');
        } else {
            showNotification('保存失败: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showNotification('保存失败: ' + error.message, 'error');
    });
}

/**
 * 切换预览面板
 */
function togglePreview() {
    const previewPane = document.querySelector('.preview-pane');
    if (previewPane) {
        previewPane.classList.toggle('active');
    } else {
        // 如果没有预览面板，创建一个
        createPreviewPane();
    }
}

/**
 * 创建预览面板
 */
function createPreviewPane() {
    const editorContainer = document.querySelector('.admin-editor');
    if (!editorContainer) return;

    // 检查是否已存在预览面板
    if (document.querySelector('.preview-pane')) return;

    const editorPane = editorContainer.querySelector('.editor-form');
    const previewPane = document.createElement('div');
    previewPane.className = 'preview-pane';
    previewPane.innerHTML = `
        <div class="preview-header">
            <h3>预览</h3>
            <button class="close-preview" onclick="togglePreview()">×</button>
        </div>
        <div class="preview-content" id="previewContent"></div>
    `;

    editorContainer.insertBefore(previewPane, editorPane);

    // 初始渲染预览
    updatePreview();

    // 监听内容变化
    const titleInput = document.getElementById('title');
    const contentTextarea = document.getElementById('content');

    if (titleInput) {
        titleInput.addEventListener('input', debounce(updatePreview, 300));
    }
    if (contentTextarea) {
        contentTextarea.addEventListener('input', debounce(updatePreview, 300));
    }
}

/**
 * 更新预览内容
 */
function updatePreview() {
    const title = document.getElementById('title').value;
    const content = document.getElementById('content').value;
    const previewContent = document.getElementById('previewContent');

    if (previewContent) {
        // 简单的 Markdown 转 HTML
        const html = markdownToHTML(content);
        previewContent.innerHTML = `
            <h1>${title || '（无标题）'}</h1>
            ${html}
        `;
    }
}

/**
 * 简单的 Markdown 转 HTML
 */
function markdownToHTML(markdown) {
    if (!markdown) return '';

    return markdown
        // 标题
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
        // 粗体和斜体
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // 链接
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
        // 代码
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        // 段落
        .replace(/\n\n/g, '</p><p>')
        .replace(/^/, '<p>')
        .replace(/$/, '</p>');
}

/**
 * 在光标位置插入文本
 */
function insertAtCursor(text) {
    const textarea = document.getElementById('content');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;

    textarea.value = value.substring(0, start) + text + value.substring(end);
    textarea.selectionStart = textarea.selectionEnd = start + text.length;
    textarea.focus();
}

/**
 * 显示快捷键帮助对话框
 */
function showShortcutHelp() {
    const shortcuts = shortcutHandler.getShortcuts();

    const modal = document.createElement('div');
    modal.className = 'shortcut-help-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>⌨️ 键盘快捷键</h2>
                <button class="close-modal" onclick="this.closest('.shortcut-help-modal').remove()">×</button>
            </div>
            <div class="modal-body">
                <table class="shortcut-table">
                    <thead>
                        <tr>
                            <th>快捷键</th>
                            <th>说明</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${shortcuts.map(s => `
                            <tr>
                                <td><code>${s.key}</code></td>
                                <td>${s.description}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <div class="shortcut-note">
                    <p><strong>提示：</strong></p>
                    <ul>
                        <li><code>Ctrl</code> 在 Windows/Linux 上使用</li>
                        <li><code>Cmd⌘</code> 在 macOS 上使用</li>
                        <li>按 <code>Ctrl+/</code> 可随时查看此帮助</li>
                    </ul>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // 点击背景关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

/**
 * 防抖函数
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 显示通知
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
        color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// 添加动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    .shortcut-help-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }

    .shortcut-help-modal .modal-content {
        background: var(--card-bg, #fff);
        border-radius: 12px;
        max-width: 600px;
        width: 90%;
        max-height: 80vh;
        overflow: hidden;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }

    .shortcut-help-modal .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        border-bottom: 1px solid var(--border-color, #e5e7eb);
    }

    .shortcut-help-modal .modal-header h2 {
        margin: 0;
        font-size: 1.5rem;
    }

    .shortcut-help-modal .close-modal {
        background: none;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .shortcut-help-modal .modal-body {
        padding: 20px;
        overflow-y: auto;
        max-height: calc(80vh - 80px);
    }

    .shortcut-table {
        width: 100%;
        border-collapse: collapse;
    }

    .shortcut-table th,
    .shortcut-table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid var(--border-color, #e5e7eb);
    }

    .shortcut-table th {
        background: var(--code-bg, #f9fafb);
        font-weight: 600;
    }

    .shortcut-table code {
        background: var(--code-bg, #f3f4f6);
        padding: 4px 8px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.9em;
    }

    .shortcut-note {
        margin-top: 20px;
        padding: 15px;
        background: var(--code-bg, #f9fafb);
        border-radius: 8px;
    }

    .shortcut-note ul {
        margin: 10px 0 0 0;
        padding-left: 20px;
    }

    .shortcut-note li {
        margin: 5px 0;
    }

    /* 预览面板样式 */
    .preview-pane {
        flex: 1;
        background: var(--card-bg, #fff);
        border-left: 1px solid var(--border-color, #e5e7eb);
        display: none;
    }

    .preview-pane.active {
        display: block;
    }

    .preview-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px 20px;
        border-bottom: 1px solid var(--border-color, #e5e7eb);
    }

    .preview-header h3 {
        margin: 0;
        font-size: 1.1rem;
    }

    .preview-header .close-preview {
        background: none;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        padding: 0;
    }

    .preview-content {
        padding: 20px;
        max-height: calc(100vh - 200px);
        overflow-y: auto;
    }

    .preview-content h1,
    .preview-content h2,
    .preview-content h3,
    .preview-content h4 {
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }

    .preview-content p {
        line-height: 1.6;
        margin-bottom: 1em;
    }

    .preview-content code {
        background: var(--code-bg, #f3f4f6);
        padding: 2px 6px;
        border-radius: 3px;
    }

    .preview-content pre {
        background: var(--code-bg, #f3f4f6);
        padding: 15px;
        border-radius: 6px;
        overflow-x: auto;
    }

    .preview-content a {
        color: var(--primary-color, #007bff);
        text-decoration: none;
    }

    .preview-content a:hover {
        text-decoration: underline;
    }
`;

document.head.appendChild(style);
