(function() {
    'use strict';

    const state = {
        aiSuggestion: null,
        historyCards: [],
        imageNotes: new Map(),
        isOrganizing: false,
        lastOrganizedFingerprint: '',
        autoOrganizeTimer: null
    };

    document.addEventListener('DOMContentLoaded', () => {
        if (document.body.dataset.page !== 'editor') {
            return;
        }

        initAssistDock();
        initAiOrganizer();
        initAiAssistActions();
        initHistoryNotes();
        initDraftHealth();
        initImageWorkbench();
        updateDraftHealth({ status: 'idle', message: '未修改' });
        updateAiSuggestionState('待整理');
    });

    function initAssistDock() {
        const toggles = Array.from(document.querySelectorAll('.assist-toggle'));
        toggles.forEach(button => {
            button.addEventListener('click', () => {
                const panelName = button.dataset.panelTarget;
                const isActive = button.classList.contains('is-active');
                setActivePanel(isActive ? null : panelName);
            });
        });
    }

    function setActivePanel(panelName) {
        document.querySelectorAll('.assist-toggle').forEach(button => {
            button.classList.toggle('is-active', button.dataset.panelTarget === panelName);
        });

        document.querySelectorAll('.assist-panel').forEach(panel => {
            panel.hidden = panel.dataset.panelName !== panelName;
        });
    }

    function getCsrfToken() {
        return document.querySelector('meta[name="csrf_token"]')?.content || '';
    }

    function getEditorText() {
        if (window.quill) {
            return window.quill.getText().trim();
        }
        return document.getElementById('content')?.value?.trim() || '';
    }

    function getEditorHtml() {
        if (window.quill) {
            return window.quill.root.innerHTML;
        }
        return document.getElementById('content')?.value || '';
    }

    function showStatus(id, message, kind = 'saving') {
        const node = document.getElementById(id);
        if (!node) return;
        node.textContent = message;
        node.className = `save-status ${kind}`;
    }

    function clearStatus(id) {
        const node = document.getElementById(id);
        if (!node) return;
        node.textContent = '';
        node.className = 'save-status';
    }

    function initAiOrganizer() {
        const trigger = document.getElementById('aiOrganizeBtn');
        const applyBtn = document.getElementById('applyAiSuggestions');
        const insertSummaryBtn = document.getElementById('insertAiSummary');

        trigger?.addEventListener('click', () => organizeContent({ manual: true }));
        applyBtn?.addEventListener('click', applyAiSuggestion);
        insertSummaryBtn?.addEventListener('click', insertAiSummary);

        window.addEventListener('editor:content-change', () => {
            if (state.autoOrganizeTimer) {
                window.clearTimeout(state.autoOrganizeTimer);
            }

            state.autoOrganizeTimer = window.setTimeout(() => {
                const content = getEditorText();
                const title = document.getElementById('title')?.value?.trim() || '';
                const fingerprint = `${title}::${content.slice(0, 500)}`;
                if (content.length < 120 || fingerprint === state.lastOrganizedFingerprint) {
                    return;
                }
                organizeContent({ auto: true });
            }, 1400);
        });
    }

    function initAiAssistActions() {
        document.getElementById('aiTagAssistBtn')?.addEventListener('click', () => window.generateAITags?.());
        document.getElementById('aiSummaryAssistBtn')?.addEventListener('click', () => window.generateAISummary?.());
        document.getElementById('aiContinueAssistBtn')?.addEventListener('click', () => window.continueAIWriting?.());
        document.getElementById('aiRecommendAssistBtn')?.addEventListener('click', () => window.generateAIRecommendations?.());
    }

    async function organizeContent(options = {}) {
        if (state.isOrganizing) {
            return;
        }

        const title = document.getElementById('title')?.value?.trim() || '';
        const content = getEditorText();
        const categories = Array.from(document.querySelectorAll('#category_id option'))
            .filter(option => option.value)
            .map(option => ({ id: option.value, name: option.textContent.trim() }));

        if (!content) {
            if (options.manual) {
                showStatus('aiOrganizeStatus', '请先输入内容，再让 AI 整理。', 'error');
            }
            return;
        }

        const trigger = document.getElementById('aiOrganizeBtn');
        state.isOrganizing = true;
        updateAiSuggestionState(options.auto ? '整理中' : '正在整理');
        if (trigger) trigger.disabled = true;
        showStatus('aiOrganizeStatus', options.auto ? 'AI 正在后台更新建议...' : 'AI 正在整理标题、摘要和分类建议...', 'saving');

        try {
            const response = await fetch('/admin/ai/organize-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    title,
                    content,
                    categories
                })
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || '整理失败');
            }

            state.aiSuggestion = data.suggestion;
            state.lastOrganizedFingerprint = `${title}::${content.slice(0, 500)}`;
            renderAiSuggestion(data.suggestion);
            if (options.manual) {
                setActivePanel('ai');
            }
            const sourceLabel = data.suggestion.source === 'ai' ? 'AI' : '启发式';
            updateAiSuggestionState(sourceLabel === 'AI' ? '建议已更新' : '基础建议');
            showStatus('aiOrganizeStatus', `${sourceLabel} 建议已准备好，可以一键应用。`, 'saved');
        } catch (error) {
            updateAiSuggestionState('整理失败');
            showStatus('aiOrganizeStatus', `整理失败：${error.message}`, 'error');
        } finally {
            state.isOrganizing = false;
            if (trigger) trigger.disabled = false;
        }
    }

    function renderAiSuggestion(suggestion) {
        const panel = document.getElementById('aiSuggestionPanel');
        if (!panel || !suggestion) return;

        document.getElementById('suggestedTitle').textContent = suggestion.title || '-';
        document.getElementById('suggestedType').textContent = formatContentType(suggestion.content_type);
        document.getElementById('suggestedCategory').textContent = suggestion.category?.name || '暂不调整';
        document.getElementById('suggestedSummary').textContent = suggestion.summary || '未生成摘要';
        document.getElementById('suggestedTags').innerHTML = (suggestion.tags || [])
            .map(tag => `<span class="suggestion-tag">#${escapeHtml(tag)}</span>`)
            .join('') || '<span class="suggestion-value">暂无标签建议</span>';

        panel.hidden = false;
    }

    function applyAiSuggestion() {
        const suggestion = state.aiSuggestion;
        if (!suggestion) return;

        const titleInput = document.getElementById('title');
        const tagsInput = document.getElementById('tags');
        const categorySelect = document.getElementById('category_id');

        if (titleInput && suggestion.title) {
            titleInput.value = suggestion.title;
        }

        if (tagsInput && Array.isArray(suggestion.tags) && suggestion.tags.length > 0) {
            tagsInput.value = suggestion.tags.join(', ');
        }

        if (categorySelect && suggestion.category?.id) {
            categorySelect.value = String(suggestion.category.id);
        }

        window.dispatchEvent(new CustomEvent('editor:content-change', {
            detail: {
                html: getEditorHtml(),
                text: getEditorText()
            }
        }));
        updateAiSuggestionState('已应用建议');
        showStatus('aiOrganizeStatus', '建议已应用到当前编辑器。', 'saved');
    }

    function insertAiSummary() {
        const summary = state.aiSuggestion?.summary;
        if (!summary) {
            showStatus('aiOrganizeStatus', '当前没有可插入的摘要。', 'error');
            return;
        }

        const summaryHtml = `<p><strong>摘要：</strong>${escapeHtml(summary)}</p><p><br></p>`;
        if (typeof window.insertEditorHtml === 'function') {
            window.insertEditorHtml(summaryHtml, 0);
        }
        showStatus('aiOrganizeStatus', '摘要已插入到正文开头。', 'saved');
    }

    function updateAiSuggestionState(message) {
        const node = document.getElementById('aiSuggestionState');
        if (node) {
            node.textContent = message;
        }
    }

    function initHistoryNotes() {
        const searchInput = document.getElementById('historyNotesSearch');
        const refreshButton = document.getElementById('openHistoryNotes');
        const debounced = debounce(() => loadHistoryNotes(searchInput?.value || ''), 260);

        searchInput?.addEventListener('input', debounced);
        refreshButton?.addEventListener('click', () => {
            setActivePanel('history');
            loadHistoryNotes(searchInput?.value || '');
        });

        loadHistoryNotes('');
    }

    async function loadHistoryNotes(query) {
        const list = document.getElementById('historyNotesList');
        if (!list) return;

        list.innerHTML = '<div class="workbench-empty">正在加载历史卡片...</div>';
        try {
            const url = `/api/cards?limit=20${query ? `&q=${encodeURIComponent(query)}` : ''}`;
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json'
                }
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || '加载失败');
            }

            state.historyCards = data.cards || [];
            renderHistoryNotes();
        } catch (error) {
            list.innerHTML = `<div class="workbench-empty">加载失败：${escapeHtml(error.message)}</div>`;
        }
    }

    function renderHistoryNotes() {
        const list = document.getElementById('historyNotesList');
        if (!list) return;

        if (!state.historyCards.length) {
            list.innerHTML = '<div class="workbench-empty">没有找到匹配的历史卡片或快速记事。</div>';
            return;
        }

        list.innerHTML = state.historyCards.map(card => `
            <article class="history-note-item" data-card-id="${card.id}">
                <div class="history-note-meta">${formatCardStatus(card.status)} · ${formatDate(card.created_at)}</div>
                <div class="history-note-title">${escapeHtml(card.title || '未命名笔记')}</div>
                <div class="history-note-preview">${escapeHtml(truncate(card.content || '', 120))}</div>
                <div class="history-note-actions">
                    <button type="button" class="btn btn-secondary btn-sm" data-insert-card="${card.id}">插入摘录</button>
                    <button type="button" class="btn btn-secondary btn-sm" data-insert-link="${card.id}">插入引用块</button>
                </div>
            </article>
        `).join('');

        list.querySelectorAll('[data-insert-card]').forEach(button => {
            button.addEventListener('click', () => {
                const card = state.historyCards.find(item => String(item.id) === button.dataset.insertCard);
                if (card) {
                    insertCardExcerpt(card);
                }
            });
        });

        list.querySelectorAll('[data-insert-link]').forEach(button => {
            button.addEventListener('click', () => {
                const card = state.historyCards.find(item => String(item.id) === button.dataset.insertLink);
                if (card) {
                    insertCardReference(card);
                }
            });
        });
    }

    function insertCardExcerpt(card) {
        const html = `
            <section class="editor-reference-card" data-card-id="${card.id}">
                <p><strong>历史笔记：</strong>${escapeHtml(card.title || '未命名笔记')}</p>
                <blockquote>${escapeHtml(truncate(card.content || '', 220))}</blockquote>
            </section>
            <p><br></p>
        `;
        if (typeof window.insertEditorHtml === 'function') {
            window.insertEditorHtml(html);
        }
        showStatus('saveStatus', `已插入历史笔记「${card.title || '未命名笔记'}」`, 'saved');
    }

    function insertCardReference(card) {
        const html = `
            <section class="editor-reference-card editor-reference-card--compact" data-card-id="${card.id}">
                <p><strong>延伸阅读：</strong>${escapeHtml(card.title || '未命名笔记')}</p>
                <p>${escapeHtml(truncate(card.content || '', 90))}</p>
            </section>
            <p><br></p>
        `;
        if (typeof window.insertEditorHtml === 'function') {
            window.insertEditorHtml(html);
        }
        showStatus('saveStatus', `已插入引用块「${card.title || '未命名笔记'}」`, 'saved');
    }

    function initDraftHealth() {
        window.addEventListener('draftsync:status', (event) => {
            updateDraftHealth(event.detail || {});
        });

        window.addEventListener('editor:content-change', () => {
            updateDraftHealth({
                status: 'dirty',
                message: '有未保存修改'
            });
        });
    }

    function updateDraftHealth(detail) {
        const stateEl = document.getElementById('draftHealthState');
        const localEl = document.getElementById('draftHealthLocal');
        const serverEl = document.getElementById('draftHealthServer');
        if (!stateEl || !localEl || !serverEl) return;

        const labels = {
            idle: '未修改',
            dirty: '等待自动保存',
            saving: '正在同步',
            saved: '已同步',
            offline: '仅本地备份',
            recovered: '已恢复草稿'
        };

        stateEl.textContent = detail.message || labels[detail.status] || '未修改';
        localEl.textContent = detail.localTime ? `已备份 ${formatRelative(detail.localTime)}` : '尚未备份';
        serverEl.textContent = detail.serverTime ? `已同步 ${formatRelative(detail.serverTime)}` : '尚未同步';
        updateAutosaveIndicator(detail.status, detail.message || labels[detail.status] || '未修改');
    }

    function initImageWorkbench() {
        const refreshButton = document.getElementById('syncImageWorkbench');
        refreshButton?.addEventListener('click', renderImageWorkbench);
        window.addEventListener('editor:images-updated', renderImageWorkbench);
        window.addEventListener('editor:content-change', renderImageWorkbench);

        setTimeout(renderImageWorkbench, 300);
    }

    function renderImageWorkbench() {
        const list = document.getElementById('imageWorkbenchList');
        const empty = document.getElementById('imageWorkbenchEmpty');
        const imageCount = document.getElementById('draftHealthImages');
        if (!list || !window.quill) return;

        const images = Array.from(window.quill.root.querySelectorAll('img'));
        if (imageCount) {
            imageCount.textContent = `${images.length} 张`;
        }

        if (!images.length) {
            list.innerHTML = '';
            if (empty) empty.style.display = 'block';
            return;
        }

        if (empty) empty.style.display = 'none';
        list.innerHTML = images.map((img, index) => {
            const note = state.imageNotes.get(img.src) || '';
            return `
                <article class="image-workbench-item ${index === 0 ? 'is-cover' : ''}" data-image-index="${index}">
                    ${index === 0 ? '<div class="image-badge">首图</div>' : ''}
                    <img class="image-workbench-thumb" src="${escapeAttribute(img.src)}" alt="">
                    <div class="image-workbench-order">
                        <button type="button" class="btn btn-secondary btn-sm" data-image-up="${index}" ${index === 0 ? 'disabled' : ''}>上移</button>
                        <button type="button" class="btn btn-secondary btn-sm" data-image-down="${index}" ${index === images.length - 1 ? 'disabled' : ''}>下移</button>
                        <button type="button" class="btn btn-secondary btn-sm" data-image-cover="${index}" ${index === 0 ? 'disabled' : ''}>设为首图</button>
                        <button type="button" class="btn btn-secondary btn-sm" data-image-remove="${index}">移除</button>
                    </div>
                    <textarea class="image-workbench-note" placeholder="给这张图补一句备注..." data-image-note="${index}">${escapeHtml(note)}</textarea>
                    <div class="image-workbench-actions">
                        <button type="button" class="btn btn-secondary btn-sm" data-save-note="${index}">保存图注</button>
                    </div>
                </article>
            `;
        }).join('');

        bindImageWorkbenchActions(images);
    }

    function bindImageWorkbenchActions(images) {
        document.querySelectorAll('[data-image-up]').forEach(button => {
            button.addEventListener('click', () => reorderImage(Number(button.dataset.imageUp), -1));
        });
        document.querySelectorAll('[data-image-down]').forEach(button => {
            button.addEventListener('click', () => reorderImage(Number(button.dataset.imageDown), 1));
        });
        document.querySelectorAll('[data-image-cover]').forEach(button => {
            button.addEventListener('click', () => moveImageToTop(Number(button.dataset.imageCover)));
        });
        document.querySelectorAll('[data-image-remove]').forEach(button => {
            button.addEventListener('click', () => removeImage(Number(button.dataset.imageRemove)));
        });
        document.querySelectorAll('[data-save-note]').forEach(button => {
            button.addEventListener('click', () => saveImageNote(Number(button.dataset.saveNote), images));
        });
    }

    function getEditorImages() {
        return Array.from(window.quill?.root?.querySelectorAll('img') || []);
    }

    function reorderImage(index, direction) {
        const images = getEditorImages();
        const target = images[index];
        const sibling = images[index + direction];
        if (!target || !sibling) return;

        const targetBlock = getImageBlock(target);
        const siblingBlock = getImageBlock(sibling);
        if (!targetBlock || !siblingBlock) return;

        if (direction < 0) {
            siblingBlock.parentNode.insertBefore(targetBlock, siblingBlock);
        } else {
            siblingBlock.parentNode.insertBefore(siblingBlock, targetBlock);
        }
        syncEditorAfterDomMutation();
    }

    function moveImageToTop(index) {
        const images = getEditorImages();
        const target = images[index];
        if (!target) return;
        const block = getImageBlock(target);
        const container = window.quill.root;
        if (block && container.firstChild) {
            container.insertBefore(block, container.firstChild);
            syncEditorAfterDomMutation();
        }
    }

    function removeImage(index) {
        const images = getEditorImages();
        const target = images[index];
        const block = target ? getImageBlock(target) : null;
        if (block) {
            block.remove();
            syncEditorAfterDomMutation();
        }
    }

    function saveImageNote(index, images) {
        const target = images[index];
        const textarea = document.querySelector(`[data-image-note="${index}"]`);
        if (!target || !textarea) return;

        const note = textarea.value.trim();
        state.imageNotes.set(target.src, note);
        let caption = target.parentElement?.querySelector('.editor-image-caption');
        if (note) {
            if (!caption) {
                caption = document.createElement('p');
                caption.className = 'editor-image-caption';
                target.insertAdjacentElement('afterend', caption);
            }
            caption.textContent = note;
        } else if (caption) {
            caption.remove();
        }
        syncEditorAfterDomMutation();
        showStatus('saveStatus', '图片备注已保存到正文中。', 'saved');
    }

    function getImageBlock(image) {
        const parent = image.parentElement;
        if (!parent) return image;
        if (parent.tagName === 'P' || parent.tagName === 'DIV') {
            return parent;
        }
        return image;
    }

    function syncEditorAfterDomMutation() {
        const contentField = document.getElementById('content');
        if (contentField && window.quill) {
            contentField.value = window.quill.root.innerHTML;
        }
        window.dispatchEvent(new CustomEvent('editor:content-change', {
            detail: {
                html: getEditorHtml(),
                text: getEditorText()
            }
        }));
        window.dispatchEvent(new CustomEvent('editor:images-updated'));
    }

    function updateAutosaveIndicator(status, message) {
        const indicator = document.getElementById('autosaveIndicator');
        if (!indicator) return;
        const dot = indicator.querySelector('.indicator-dot');
        const text = indicator.querySelector('.indicator-text');
        if (!dot || !text) return;

        indicator.classList.remove('status-saving', 'status-saved', 'status-error');
        dot.classList.remove('dot-saving', 'dot-saved', 'dot-error');

        if (status === 'saving' || status === 'dirty') {
            indicator.classList.add('status-saving');
            dot.classList.add('dot-saving');
        } else if (status === 'offline') {
            indicator.classList.add('status-error');
            dot.classList.add('dot-error');
        } else {
            indicator.classList.add('status-saved');
            dot.classList.add('dot-saved');
        }

        text.textContent = message;
    }

    function formatContentType(type) {
        const labels = {
            daily: '日常记录',
            knowledge: '知识整理',
            idea: '灵感想法'
        };
        return labels[type] || '未分类';
    }

    function formatCardStatus(status) {
        const labels = {
            idea: '想法',
            draft: '草稿',
            incubating: '孵化中',
            published: '已发布'
        };
        return labels[status] || '笔记';
    }

    function formatDate(value) {
        if (!value) return '刚刚';
        return new Date(value).toLocaleDateString('zh-CN', {
            month: 'short',
            day: 'numeric'
        });
    }

    function formatRelative(value) {
        if (!value) return '刚刚';
        const diff = Math.max(0, Date.now() - new Date(value).getTime());
        const minutes = Math.floor(diff / 60000);
        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes} 分钟前`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours} 小时前`;
        return `${Math.floor(hours / 24)} 天前`;
    }

    function truncate(text, limit) {
        const normalized = String(text || '').replace(/\s+/g, ' ').trim();
        if (normalized.length <= limit) return normalized;
        return normalized.slice(0, limit).trimEnd() + '...';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    function escapeAttribute(text) {
        return String(text || '').replace(/"/g, '&quot;');
    }

    function debounce(fn, wait) {
        let timer = null;
        return (...args) => {
            window.clearTimeout(timer);
            timer = window.setTimeout(() => fn(...args), wait);
        };
    }

    window.EditorWorkbench = {
        openPanel: setActivePanel,
        updateAiSuggestionState
    };
})();
