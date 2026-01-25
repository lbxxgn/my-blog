// Enhanced Markdown Editor with rich features
const contentTextarea = document.getElementById('content');
const previewDiv = document.getElementById('preview');

// Markdown action mappings
const markdownActions = {
    bold: { before: '**', after: '**', placeholder: '粗体文本' },
    italic: { before: '*', after: '*', placeholder: '斜体文本' },
    strikethrough: { before: '~~', after: '~~', placeholder: '删除线文本' },
    h1: { before: '# ', after: '', placeholder: '一级标题', prefix: true },
    h2: { before: '## ', after: '', placeholder: '二级标题', prefix: true },
    h3: { before: '### ', after: '', placeholder: '三级标题', prefix: true },
    ul: { before: '- ', after: '', placeholder: '列表项', prefix: true },
    ol: { before: '1. ', after: '', placeholder: '列表项', prefix: true },
    quote: { before: '> ', after: '', placeholder: '引用内容', prefix: true },
    code: { before: '`', after: '`', placeholder: '代码' },
    codeblock: { before: '```\n', after: '\n```', placeholder: '代码块' },
    link: { before: '[', after: '](url)', placeholder: '链接文字' },
    image: { before: '![', after: '](url)', placeholder: '图片描述' },
    hr: { before: '\n---\n', after: '', placeholder: '', standalone: true },
    table: { before: '| 标题1 | 标题2 |\n|-------|-------|\n| 内容1 | 内容2 |', after: '', placeholder: '', standalone: true }
};

// Enhanced Markdown parser with more features
function parseMarkdown(text) {
    // Escape HTML first
    text = text.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;');

    let html = text;

    // Code blocks (must be first to avoid interference)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function(match, lang, code) {
        return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
    });

    // Horizontal rules
    html = html.replace(/^---$/gm, '<hr>');

    // Headers
    html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold and Italic combinations
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Strikethrough
    html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');

    // Code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Blockquotes
    html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

    // Unordered lists
    html = html.replace(/^\- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    // Note: ordered lists need special handling to separate from ul

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

    // Images
    html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">');

    // Line breaks and paragraphs
    html = html.replace(/\n\n+/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    // Wrap in paragraphs if not already wrapped
    if (!html.startsWith('<')) {
        html = '<p>' + html + '</p>';
    }

    return html;
}

// Update word count
function updateStats() {
    const text = contentTextarea.value;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    const chars = text.length;
    const lines = text.split('\n').length;

    document.getElementById('wordCount').textContent = words.toLocaleString();
    document.getElementById('charCount').textContent = chars.toLocaleString();
    document.getElementById('lineCount').textContent = lines.toLocaleString();
}

// Insert markdown syntax
function insertMarkdown(action) {
    const config = markdownActions[action];
    if (!config) return;

    const start = contentTextarea.selectionStart;
    const end = contentTextarea.selectionEnd;
    const text = contentTextarea.value;
    const selectedText = text.substring(start, end) || config.placeholder;

    let insertion;
    if (config.standalone) {
        insertion = config.before;
        contentTextarea.value = text.substring(0, end) + insertion + text.substring(end);
        contentTextarea.selectionStart = contentTextarea.selectionEnd = end + insertion.length;
    } else {
        insertion = config.before + selectedText + config.after;
        contentTextarea.value = text.substring(0, start) + insertion + text.substring(end);
        contentTextarea.selectionStart = start + config.before.length;
        contentTextarea.selectionEnd = start + config.before.length + selectedText.length;
    }

    contentTextarea.focus();
    contentTextarea.dispatchEvent(new Event('input'));
}

// Initialize editor
if (contentTextarea && previewDiv) {
    // Update preview on input
    contentTextarea.addEventListener('input', function() {
        previewDiv.innerHTML = parseMarkdown(this.value);
        updateStats();
    });

    // Initial preview and stats
    previewDiv.innerHTML = parseMarkdown(contentTextarea.value);
    updateStats();

    // Toolbar button clicks
    document.querySelectorAll('.toolbar-btn[data-action]').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.getAttribute('data-action');
            insertMarkdown(action);
        });
    });

    // Keyboard shortcuts
    contentTextarea.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key.toLowerCase()) {
                case 'b':
                    e.preventDefault();
                    insertMarkdown('bold');
                    break;
                case 'i':
                    e.preventDefault();
                    insertMarkdown('italic');
                    break;
                case 'z':
                    e.preventDefault();
                    document.execCommand('undo');
                    break;
                case 'y':
                    e.preventDefault();
                    document.execCommand('redo');
                    break;
            }
        }

        // Tab key for indentation
        if (e.key === 'Tab') {
            e.preventDefault();
            insertMarkdown('code');
        }
    });

    // Fullscreen toggle
    let isFullscreen = false;
    document.querySelector('[data-action="fullscreen"]').addEventListener('click', function() {
        isFullscreen = !isFullscreen;
        const editorContainer = document.querySelector('.admin-editor');

        if (isFullscreen) {
            editorContainer.classList.add('fullscreen-mode');
            document.body.style.overflow = 'hidden';
        } else {
            editorContainer.classList.remove('fullscreen-mode');
            document.body.style.overflow = '';
        }
    });

    // Auto-save to localStorage
    let saveTimeout;
    const saveStatus = document.getElementById('saveStatus');
    const titleInput = document.getElementById('title');
    const postId = titleInput ? window.location.pathname.split('/').pop() : '';

    function autoSave() {
        const content = contentTextarea.value;
        const title = titleInput ? titleInput.value : '';
        localStorage.setItem(`editor_draft_${postId}`, JSON.stringify({
            title,
            content,
            timestamp: new Date().toISOString()
        }));
        saveStatus.textContent = '已自动保存 ' + new Date().toLocaleTimeString();
        saveStatus.className = 'save-status saved';

        setTimeout(() => {
            saveStatus.textContent = '';
            saveStatus.className = 'save-status';
        }, 2000);
    }

    contentTextarea.addEventListener('input', function() {
        clearTimeout(saveTimeout);
        saveStatus.textContent = '正在保存...';
        saveStatus.className = 'save-status saving';
        saveTimeout = setTimeout(autoSave, 1000);
    });

    // Load draft on page load
    const savedDraft = localStorage.getItem(`editor_draft_${postId}`);
    if (savedDraft && !contentTextarea.value) {
        try {
            const draft = JSON.parse(savedDraft);
            if (confirm(`发现未保存的草稿 (${new Date(draft.timestamp).toLocaleString()})，是否恢复？`)) {
                if (titleInput) titleInput.value = draft.title;
                contentTextarea.value = draft.content;
                previewDiv.innerHTML = parseMarkdown(contentTextarea.value);
                updateStats();
            }
        } catch (e) {
            console.error('Failed to load draft:', e);
        }
    }
}

// Image upload functionality
const imageUpload = document.getElementById('imageUpload');
if (imageUpload) {
    imageUpload.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        const csrfToken = document.querySelector('meta[name="csrf_token"]').getAttribute('content');
        const formData = new FormData();
        formData.append('file', file);
        formData.append('csrf_token', csrfToken);

        try {
            const saveStatus = document.getElementById('saveStatus');
            saveStatus.textContent = '正在上传图片...';
            saveStatus.className = 'save-status saving';

            const response = await fetch('/admin/upload', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                const markdown = `![${file.name.split('.')[0] || '图片'}](${data.url})`;
                const textarea = document.getElementById('content');
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;

                textarea.value = textarea.value.substring(0, start) + markdown + textarea.value.substring(end);
                textarea.focus();
                textarea.selectionStart = textarea.selectionEnd = start + markdown.length;
                textarea.dispatchEvent(new Event('input'));

                saveStatus.textContent = '图片上传成功！';
                saveStatus.className = 'save-status saved';
                setTimeout(() => {
                    saveStatus.textContent = '';
                    saveStatus.className = 'save-status';
                }, 2000);
            } else {
                saveStatus.textContent = '上传失败: ' + data.error;
                saveStatus.className = 'save-status error';
                setTimeout(() => {
                    saveStatus.textContent = '';
                    saveStatus.className = 'save-status';
                }, 3000);
            }
        } catch (error) {
            alert('上传失败: ' + error.message);
        }

        e.target.value = '';
    });
}
