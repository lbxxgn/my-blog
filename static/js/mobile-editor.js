/**
 * 移动端快速发布编辑器
 * 提供沉浸式编辑体验
 */
(function() {
    'use strict';

    // 状态
    let selectedTags = [];
    let selectedCategory = null;
    let selectedImages = [];
    let accessLevel = 'public';
    let draftKey = 'mobile_editor_draft';
    let isPublishing = false;
    let editorStatusTimer = null;

    // 初始化
    document.addEventListener('DOMContentLoaded', function() {
        initMobileEditor();
        loadDraft();
    });

    /**
     * 打开移动端编辑器
     */
    function openMobileEditor() {
        const overlay = document.getElementById('mobileEditorOverlay');
        const panel = document.getElementById('mobileEditorPanel');

        if (overlay && panel) {
            overlay.classList.add('show');
            panel.classList.add('show');
            document.body.style.overflow = 'hidden';

            // 聚焦文本框
            setTimeout(() => {
                const textarea = document.getElementById('mobileEditorTextarea');
                if (textarea) textarea.focus();
            }, 300);
        }
    }
    window.openMobileEditor = openMobileEditor;

    /**
     * 关闭移动端编辑器
     */
    function closeMobileEditor() {
        const overlay = document.getElementById('mobileEditorOverlay');
        const panel = document.getElementById('mobileEditorPanel');

        if (overlay && panel) {
            overlay.classList.remove('show');
            panel.classList.remove('show');
            document.body.style.overflow = '';
        }
    }
    window.closeMobileEditor = closeMobileEditor;

    /**
     * 判断当前是否有可恢复的草稿内容
     */
    function hasMeaningfulDraftContent() {
        const textarea = document.getElementById('mobileEditorTextarea');
        const title = document.getElementById('mobileEditorTitle');

        return Boolean(
            (textarea && textarea.value.trim().length > 0) ||
            (title && title.value.trim().length > 0) ||
            selectedImages.length > 0 ||
            selectedTags.length > 0 ||
            selectedCategory ||
            accessLevel !== 'public'
        );
    }

    /**
     * 关闭编辑器时保留现场，避免误丢草稿
     */
    function dismissEditor() {
        if (isPublishing) {
            showToast('正在发送，请稍候', 'error');
            setEditorStatus('正在发送，请稍候...', 'info', { persistent: true });
            return;
        }

        if (hasMeaningfulDraftContent()) {
            saveDraft();
        } else {
            clearDraft();
        }
        closeMobileEditor();
    }

    function setEditorStatus(message, type = 'info', options = {}) {
        const statusEl = document.getElementById('mobileEditorStatus');
        if (!statusEl) return;

        if (editorStatusTimer) {
            clearTimeout(editorStatusTimer);
            editorStatusTimer = null;
        }

        statusEl.textContent = message || '';
        statusEl.classList.remove('is-error', 'is-success', 'show');

        if (type === 'error') {
            statusEl.classList.add('is-error');
        } else if (type === 'success') {
            statusEl.classList.add('is-success');
        }

        if (message) {
            statusEl.classList.add('show');
        }

        if (message && !options.persistent) {
            const duration = options.duration || 2200;
            editorStatusTimer = setTimeout(() => {
                statusEl.textContent = '';
                statusEl.classList.remove('is-error', 'is-success', 'show');
                editorStatusTimer = null;
            }, duration);
        }
    }

    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = 'toast-message';
        if (type === 'error') {
            toast.classList.add('is-error');
        }
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 2200);
    }

    function setPublishButtonState(label, disabled = true) {
        const publishBtn = document.getElementById('mobileEditorPublish');
        if (!publishBtn) return;

        publishBtn.disabled = disabled;
        publishBtn.textContent = label;
    }

    function resetPublishButton() {
        const publishBtn = document.getElementById('mobileEditorPublish');
        if (!publishBtn) return;

        publishBtn.textContent = '发送';
        updatePublishButton();
    }

    /**
     * 初始化编辑器
     */
    function initMobileEditor() {
        // 关闭按钮
        const closeBtn = document.getElementById('mobileEditorClose');
        if (closeBtn) {
            closeBtn.addEventListener('click', dismissEditor);
        }

        // 点击遮罩关闭
        const overlay = document.getElementById('mobileEditorOverlay');
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) {
                    dismissEditor();
                }
            });
        }

        // 文本输入 - 自动保存草稿
        const textarea = document.getElementById('mobileEditorTextarea');
        if (textarea) {
            textarea.addEventListener('input', function() {
                if (!isPublishing) {
                    setEditorStatus('');
                }
                saveDraft();
                updatePublishButton();
            });
        }

        // 标题输入
        const titleInput = document.getElementById('mobileEditorTitle');
        if (titleInput) {
            titleInput.addEventListener('input', function() {
                if (!isPublishing) {
                    setEditorStatus('');
                }
                saveDraft();
            });
        }

        // 发布按钮
        const publishBtn = document.getElementById('mobileEditorPublish');
        if (publishBtn) {
            publishBtn.addEventListener('click', publishPost);
        }

        // 工具栏按钮
        initToolbarButtons();

        // 初始化标签和分类选择器
        initSelectors();
    }

    /**
     * 初始化工具栏按钮
     */
    function initToolbarButtons() {
        // 图片按钮
        const imageBtn = document.getElementById('toolbarImage');
        if (imageBtn) {
            imageBtn.addEventListener('click', function() {
                const input = document.getElementById('mobileEditorImageInput');
                if (input) input.click();
            });
        }

        // 图片输入
        const imageInput = document.getElementById('mobileEditorImageInput');
        if (imageInput) {
            imageInput.addEventListener('change', handleImageSelect);
        }

        // 标签按钮
        const tagsBtn = document.getElementById('toolbarTags');
        if (tagsBtn) {
            tagsBtn.addEventListener('click', openQuickTagInput);
        }

        // 分类按钮
        const categoryBtn = document.getElementById('toolbarCategory');
        if (categoryBtn) {
            categoryBtn.addEventListener('click', openCategorySelector);
        }

        // 权限按钮
        const accessBtn = document.getElementById('toolbarAccess');
        if (accessBtn) {
            accessBtn.addEventListener('click', toggleAccessLevel);
        }

        const accessPill = document.getElementById('mobileEditorAccessPill');
        if (accessPill) {
            accessPill.addEventListener('click', toggleAccessLevel);
        }

        updateAccessPill();
    }

    /**
     * 处理图片选择
     */
    function handleImageSelect(e) {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        if (!isPublishing) {
            setEditorStatus('');
        }

        // 限制最多9张图片
        const remaining = 9 - selectedImages.length;
        const filesToProcess = Array.from(files).slice(0, remaining);

        filesToProcess.forEach(file => {
            const reader = new FileReader();
            reader.onload = function(event) {
                selectedImages.push({
                    file: file,
                    dataUrl: event.target.result
                });
                renderImages();
                saveDraft();
                updatePublishButton();
            };
            reader.readAsDataURL(file);
        });

        // 清空 input
        e.target.value = '';
    }

    /**
     * 渲染图片预览
     */
    function renderImages() {
        const container = document.getElementById('mobileEditorImages');
        if (!container) return;

        container.innerHTML = '';

        selectedImages.forEach((img, index) => {
            const item = document.createElement('div');
            item.className = 'mobile-editor-image-item';
            item.innerHTML = `
                <img src="${img.dataUrl}" alt="">
                <button type="button" class="mobile-editor-image-remove" data-index="${index}">×</button>
            `;
            container.appendChild(item);
        });

        // 添加图片按钮（如果还没满9张）
        if (selectedImages.length < 9) {
            const addBtn = document.createElement('button');
            addBtn.type = 'button';
            addBtn.className = 'mobile-editor-image-item mobile-editor-add-image';
            addBtn.innerHTML = '+';
            addBtn.addEventListener('click', function() {
                document.getElementById('mobileEditorImageInput').click();
            });
            container.appendChild(addBtn);
        }

        // 删除按钮事件
        container.querySelectorAll('.mobile-editor-image-remove').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const index = parseInt(this.getAttribute('data-index'));
                selectedImages.splice(index, 1);
                renderImages();
                saveDraft();
                updatePublishButton();
            });
        });
    }

    /**
     * 初始化选择器
     */
    function initSelectors() {
        // 关闭选择器
        document.querySelectorAll('.selector-close, .selector-overlay').forEach(el => {
            el.addEventListener('click', function(e) {
                if (e.target === el || el.classList.contains('selector-close')) {
                    closeSelectors();
                }
            });
        });

        const tagsInput = document.getElementById('tagsQuickInput');
        if (tagsInput) {
            tagsInput.addEventListener('input', function() {
                renderTagsList(this.value);
            });

            tagsInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    submitQuickTagInput();
                }
            });
        }
    }

    /**
     * 打开标签选择器
     */
    function openTagsSelector() {
        const overlay = document.getElementById('tagsSelectorOverlay');
        const panel = document.getElementById('tagsSelectorPanel');
        const input = document.getElementById('tagsQuickInput');

        if (overlay && panel) {
            overlay.classList.add('show');
            panel.classList.add('show');
            if (input) {
                input.value = '';
            }
            renderTagsList('');

            setTimeout(() => {
                if (input) {
                    input.focus();
                }
            }, 80);
        }
    }

    function openQuickTagInput() {
        openTagsSelector();
    }

    function resolveTagByName(name, index) {
        const allTags = window.availableTags || [];
        const matchedTag = allTags.find(tag => String(tag.name || '').toLowerCase() === name.toLowerCase());
        if (matchedTag) {
            return matchedTag;
        }

        const newTag = {
            id: Date.now() + index,
            name
        };

        allTags.push(newTag);
        window.availableTags = allTags;
        return newTag;
    }

    function parseTagNames(rawValue) {
        return Array.from(
            new Set(
                String(rawValue || '')
                    .split(/[#,\s，]+/)
                    .map(name => name.trim())
                    .filter(Boolean)
                    .slice(0, 10)
            )
        );
    }

    function mergeTagNames(tagNames) {
        tagNames.forEach((name, index) => {
            const exists = selectedTags.some(tag => String(tag.name || '').toLowerCase() === name.toLowerCase());
            if (!exists) {
                selectedTags.push(resolveTagByName(name, index));
            }
        });

        renderSelections();
        saveDraft();
    }

    function submitQuickTagInput() {
        const input = document.getElementById('tagsQuickInput');
        if (!input) {
            return;
        }

        const names = parseTagNames(input.value);
        if (names.length === 0) {
            return;
        }

        mergeTagNames(names);
        input.value = '';
        renderTagsList('');
        input.focus();
    }

    /**
     * 渲染标签列表
     */
    function renderTagsList(query = '') {
        const container = document.getElementById('tagsSelectorContent');
        if (!container) return;

        const allTags = window.availableTags || [];
        const normalizedQuery = String(query || '').trim().toLowerCase();
        const selectedTagIds = new Set(selectedTags.map(tag => tag.id));
        const suggestedTags = allTags
            .filter(tag => !selectedTagIds.has(tag.id))
            .filter(tag => !normalizedQuery || String(tag.name || '').toLowerCase().includes(normalizedQuery))
            .slice(0, 12);

        let html = '<div class="selector-helper">回车可直接添加，点标签也能快速选中。</div>';

        if (normalizedQuery) {
            const exactMatch = allTags.some(tag => String(tag.name || '').toLowerCase() === normalizedQuery);
            if (!exactMatch) {
                html += `
                    <div class="selector-section-title">快速添加</div>
                    <div class="selector-chip-grid">
                        <button type="button" class="selector-chip create" data-create-tag="${escapeHtmlAttr(query)}">+ 创建 #${escapeHtml(query.trim())}</button>
                    </div>
                `;
            }
        }

        if (selectedTags.length > 0) {
            html += '<div class="selector-section-title">已选标签</div><div class="selector-chip-grid">';
            selectedTags.forEach(tag => {
                html += renderTagChip(tag, true);
            });
            html += '</div>';
        }

        html += '<div class="selector-section-title">推荐标签</div>';
        if (suggestedTags.length > 0) {
            html += '<div class="selector-chip-grid">';
            suggestedTags.forEach(tag => {
                html += renderTagChip(tag, false);
            });
            html += '</div>';
        } else {
            html += '<div class="selector-empty">没有匹配的推荐标签，直接回车就能创建。</div>';
        }

        container.innerHTML = html;

        container.querySelectorAll('[data-tag-id]').forEach(item => {
            item.addEventListener('click', function() {
                const tagId = Number(this.getAttribute('data-tag-id'));
                if (tagId) {
                    toggleTagSelection(tagId);
                }
            });
        });

        container.querySelectorAll('[data-create-tag]').forEach(item => {
            item.addEventListener('click', function() {
                const name = this.getAttribute('data-create-tag');
                if (!name) {
                    return;
                }

                mergeTagNames(parseTagNames(name));
                const input = document.getElementById('tagsQuickInput');
                if (input) {
                    input.value = '';
                    input.focus();
                }
                renderTagsList('');
            });
        });
    }

    /**
     * 渲染单个标签项
     */
    function renderTagChip(tag, isSelected) {
        return `
            <button type="button" class="selector-chip ${isSelected ? 'active' : ''}" data-tag-id="${tag.id}">
                #${escapeHtml(tag.name)}
            </button>
        `;
    }

    /**
     * 切换标签选择
     */
    function toggleTagSelection(tagId) {
        const tag = (window.availableTags || []).find(t => t.id === tagId);
        if (!tag) return;

        const index = selectedTags.findIndex(t => t.id === tagId);
        if (index > -1) {
            selectedTags.splice(index, 1);
        } else {
            selectedTags.push(tag);
        }

        const currentQuery = document.getElementById('tagsQuickInput')?.value || '';
        renderTagsList(currentQuery);
        renderSelections();
        saveDraft();
    }

    /**
     * 打开分类选择器
     */
    function openCategorySelector() {
        const overlay = document.getElementById('categorySelectorOverlay');
        const panel = document.getElementById('categorySelectorPanel');

        if (overlay && panel) {
            overlay.classList.add('show');
            panel.classList.add('show');
            renderCategoryList();
        }
    }

    /**
     * 渲染分类列表
     */
    function renderCategoryList() {
        const container = document.getElementById('categorySelectorContent');
        if (!container) return;

        const allCategories = window.availableCategories || [];

        let html = '';

        // 无分类选项
        html += `
            <div class="selector-item ${!selectedCategory ? 'selected' : ''}" data-category-id="">
                <span class="selector-item-name">无分类</span>
                <span class="selector-item-check">${!selectedCategory ? '✓' : ''}</span>
            </div>
        `;

        allCategories.forEach(cat => {
            const isSelected = selectedCategory && selectedCategory.id === cat.id;
            html += `
                <div class="selector-item ${isSelected ? 'selected' : ''}" data-category-id="${cat.id}">
                    <span class="selector-item-name">${cat.name}</span>
                    <span class="selector-item-check">${isSelected ? '✓' : ''}</span>
                </div>
            `;
        });

        container.innerHTML = html;

        // 绑定点击事件
        container.querySelectorAll('.selector-item').forEach(item => {
            item.addEventListener('click', function() {
                const catId = this.getAttribute('data-category-id');
                if (catId === '') {
                    selectedCategory = null;
                } else {
                    selectedCategory = (window.availableCategories || []).find(c => c.id === parseInt(catId));
                }
                renderCategoryList();
                renderSelections();
                closeSelectors();
                saveDraft();
            });
        });
    }

    /**
     * 渲染已选标签和分类
     */
    function renderSelections() {
        const container = document.getElementById('mobileEditorSelections');
        if (!container) return;

        let html = '';

        if (selectedCategory) {
            html += `
                <span class="selection-pill">
                    📂 ${selectedCategory.name}
                </span>
            `;
        }

        selectedTags.forEach(tag => {
            html += `
                <span class="selection-pill remove">
                    #${tag.name}
                    <span class="selection-pill-remove" data-tag-id="${tag.id}">×</span>
                </span>
            `;
        });

        container.innerHTML = html;
        container.style.display = (selectedCategory || selectedTags.length > 0) ? 'flex' : 'none';

        // 绑定移除事件
        container.querySelectorAll('.selection-pill-remove').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const tagId = parseInt(this.getAttribute('data-tag-id'));
                selectedTags = selectedTags.filter(t => t.id !== tagId);
                renderSelections();
                saveDraft();
            });
        });
    }

    /**
     * 关闭所有选择器
     */
    function closeSelectors() {
        document.querySelectorAll('.selector-overlay, .selector-panel').forEach(el => {
            el.classList.remove('show');
        });
    }

    /**
     * 切换访问权限
     */
    function toggleAccessLevel() {
        // 简单版：直接切换
        const levels = ['public', 'login', 'private'];
        const currentIndex = levels.indexOf(accessLevel);
        accessLevel = levels[(currentIndex + 1) % levels.length];

        const btn = document.getElementById('toolbarAccess');
        if (btn) {
            const icons = { public: '＋', login: '＋', private: '＋' };
            const icon = btn.querySelector('.toolbar-icon');
            if (icon) icon.textContent = icons[accessLevel];
        }

        updateAccessPill();
        saveDraft();
    }

    function updateAccessPill() {
        const pill = document.getElementById('mobileEditorAccessPill');
        if (!pill) return;

        const labels = {
            public: '公开',
            login: '登录可见',
            private: '私密'
        };

        pill.textContent = labels[accessLevel] || '🌐 公开';
    }

    /**
     * 创建新标签
     */
    window.createNewTag = function() {
        const name = prompt('请输入新标签名称：');
        if (name && name.trim()) {
            mergeTagNames(parseTagNames(name));
            renderTagsList(document.getElementById('tagsQuickInput')?.value || '');
        }
    };

    /**
     * 更新发布按钮状态
     */
    function updatePublishButton() {
        const textarea = document.getElementById('mobileEditorTextarea');
        const publishBtn = document.getElementById('mobileEditorPublish');

        if (textarea && publishBtn) {
            const hasContent = textarea.value.trim().length > 0 || selectedImages.length > 0;
            publishBtn.disabled = isPublishing || !hasContent;
        }
    }

    /**
     * 保存草稿
     */
    function saveDraft() {
        const title = document.getElementById('mobileEditorTitle')?.value || '';
        const content = document.getElementById('mobileEditorTextarea')?.value || '';

        const draft = {
            title,
            content,
            tags: selectedTags,
            category: selectedCategory,
            images: selectedImages.map(img => img.dataUrl), // 只保存 dataUrl
            accessLevel,
            savedAt: Date.now()
        };

        try {
            localStorage.setItem(draftKey, JSON.stringify(draft));
        } catch (e) {
            console.warn('Failed to save draft:', e);
        }
    }

    /**
     * 加载草稿
     */
    function loadDraft() {
        try {
            const draftData = localStorage.getItem(draftKey);
            if (!draftData) return;

            const draft = JSON.parse(draftData);
            const hasDraftState = draft && (
                String(draft.title || '').trim().length > 0 ||
                String(draft.content || '').trim().length > 0 ||
                (Array.isArray(draft.images) && draft.images.length > 0) ||
                (Array.isArray(draft.tags) && draft.tags.length > 0) ||
                draft.category ||
                (draft.accessLevel && draft.accessLevel !== 'public')
            );
            if (!hasDraftState) return;

            // 检查草稿是否过期（24小时）
            if (Date.now() - draft.savedAt > 24 * 60 * 60 * 1000) {
                clearDraft();
                return;
            }

            // 恢复草稿
            if (document.getElementById('mobileEditorTitle')) {
                document.getElementById('mobileEditorTitle').value = draft.title || '';
            }
            if (document.getElementById('mobileEditorTextarea')) {
                document.getElementById('mobileEditorTextarea').value = draft.content || '';
            }

            selectedTags = draft.tags || [];
            selectedCategory = draft.category || null;
            accessLevel = draft.accessLevel || 'public';

            // 恢复图片（只恢复 dataUrl，没有 file 对象）
            if (draft.images && draft.images.length > 0) {
                selectedImages = draft.images.map(dataUrl => ({
                    dataUrl,
                    file: null
                }));
                renderImages();
            }

            renderSelections();
            updateAccessPill();
            updatePublishButton();
        } catch (e) {
            console.warn('Failed to load draft:', e);
        }
    }

    /**
     * 清除草稿
     */
    function clearDraft() {
        try {
            localStorage.removeItem(draftKey);
        } catch (e) {}

        // 重置状态
        selectedTags = [];
        selectedCategory = null;
        selectedImages = [];
        accessLevel = 'public';

        // 重置表单
        const titleInput = document.getElementById('mobileEditorTitle');
        const textarea = document.getElementById('mobileEditorTextarea');
        if (titleInput) titleInput.value = '';
        if (textarea) textarea.value = '';

        renderSelections();
        renderImages();
        updateAccessPill();
        updatePublishButton();
    }

    /**
     * 发布文章
     */
    async function publishPost() {
        if (isPublishing) {
            return;
        }

        const title = document.getElementById('mobileEditorTitle')?.value || '';
        const content = document.getElementById('mobileEditorTextarea')?.value || '';

        if (!content.trim() && selectedImages.length === 0) {
            setEditorStatus('至少输入一点内容，或带上一张图片。', 'error');
            showToast('请输入内容或添加图片', 'error');
            return;
        }

        isPublishing = true;
        setPublishButtonState('发送中...');
        setEditorStatus('正在整理内容...', 'info', { persistent: true });

        try {
            const csrfToken = document.querySelector('meta[name="csrf_token"]')?.content;
            const uploadedImageUrls = await uploadSelectedImages(csrfToken);
            const composedContent = composePostContent(content, uploadedImageUrls);
            setEditorStatus('正在发送内容...', 'info', { persistent: true });

            // 构建 FormData
            const formData = new FormData();
            formData.append('title', title || buildTitleFromContent(composedContent));
            formData.append('content', composedContent);
            formData.append('is_published', 'true');
            formData.append('access_level', accessLevel);
            if (csrfToken) {
                formData.append('csrf_token', csrfToken);
            }

            if (selectedCategory) {
                formData.append('category_id', selectedCategory.id);
            }

            if (selectedTags.length > 0) {
                formData.append('tags', selectedTags.map(t => t.name).join(', '));
            }

            // 提交文章 - 使用 fetch API 提交到编辑器
            const response = await fetch('/admin/new', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            if (response.ok) {
                const destinationUrl = response.redirected ? response.url : null;
                clearDraft();
                closeMobileEditor();
                setEditorStatus('');
                showToast('发送成功');

                if (destinationUrl) {
                    setTimeout(() => {
                        window.location.href = destinationUrl;
                    }, 500);
                    return;
                }

                const refreshed = window.InfiniteScroll && typeof window.InfiniteScroll.refresh === 'function'
                    ? await window.InfiniteScroll.refresh()
                    : false;

                if (refreshed) {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    return;
                }

                setTimeout(() => {
                    window.location.href = '/';
                }, 500);
            } else {
                const error = await response.text();
                throw new Error(error || '发布失败');
            }
        } catch (error) {
            console.error('Publish error:', error);
            setEditorStatus(error.message || '发布失败，请稍后重试。', 'error', { persistent: true });
            showToast(`发布失败：${error.message || '未知错误'}`, 'error');
        } finally {
            isPublishing = false;
            resetPublishButton();
        }
    }

    async function uploadSelectedImages(csrfToken) {
        if (selectedImages.length === 0) {
            return [];
        }

        const uploadedUrls = [];

        for (let index = 0; index < selectedImages.length; index++) {
            const image = selectedImages[index];
            const file = image.file || await dataUrlToFile(image.dataUrl, `mobile-image-${index + 1}.png`);

            if (!file) {
                throw new Error(`第 ${index + 1} 张图片无法读取，请重新选择`);
            }

            setPublishButtonState(`上传中 ${index + 1}/${selectedImages.length}`);
            setEditorStatus(`正在上传第 ${index + 1} 张图片，共 ${selectedImages.length} 张`, 'info', { persistent: true });

            const formData = new FormData();
            formData.append('file', file);
            if (csrfToken) {
                formData.append('csrf_token', csrfToken);
            }

            const response = await fetch('/admin/upload', {
                method: 'POST',
                headers: csrfToken ? { 'X-CSRFToken': csrfToken } : {},
                body: formData
            });

            const payload = await parseJsonResponse(response);
            if (!response.ok || !payload.success) {
                throw new Error(payload.error || `第 ${index + 1} 张图片上传失败`);
            }

            const imageUrl = payload.url || payload.urls?.large || payload.urls?.original || payload.urls?.medium || payload.urls?.thumbnail;
            if (!imageUrl) {
                throw new Error(`第 ${index + 1} 张图片上传后没有返回可用地址`);
            }

            uploadedUrls.push(imageUrl);
        }

        setPublishButtonState('发送中...');
        return uploadedUrls;
    }

    function composePostContent(content, imageUrls) {
        const trimmedContent = String(content || '').trim();
        if (!imageUrls || imageUrls.length === 0) {
            return trimmedContent;
        }

        const imageMarkup = imageUrls.map(url => `<img src="${escapeHtmlAttr(url)}" alt="">`).join('\n');
        return trimmedContent ? `${trimmedContent}\n\n${imageMarkup}` : imageMarkup;
    }

    async function dataUrlToFile(dataUrl, fallbackName) {
        if (!dataUrl || typeof dataUrl !== 'string' || !dataUrl.startsWith('data:')) {
            return null;
        }

        const response = await fetch(dataUrl);
        const blob = await response.blob();
        const mimeType = blob.type || 'image/png';
        const extension = mimeType.split('/')[1] || 'png';
        return new File([blob], fallbackName.replace(/\.\w+$/, `.${extension}`), { type: mimeType });
    }

    async function parseJsonResponse(response) {
        const responseClone = response.clone();
        try {
            return await response.json();
        } catch (error) {
            const text = await responseClone.text();
            return {
                success: false,
                error: text || '服务器返回了无法解析的响应'
            };
        }
    }

    function insertAtCursor(text) {
        const textarea = document.getElementById('mobileEditorTextarea');
        if (!textarea) return;

        const start = textarea.selectionStart || 0;
        const end = textarea.selectionEnd || 0;
        textarea.value = `${textarea.value.slice(0, start)}${text}${textarea.value.slice(end)}`;
        textarea.selectionStart = textarea.selectionEnd = start + text.length;
        textarea.focus();
        saveDraft();
        updatePublishButton();
    }

    function buildTitleFromContent(content) {
        const normalized = String(content || '')
            .replace(/<[^>]+>/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();

        return normalized ? normalized.slice(0, 28) : '无标题';
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function escapeHtmlAttr(value) {
        return escapeHtml(value);
    }

    // 暴露全局函数
    window.MobileEditor = {
        open: openMobileEditor,
        close: closeMobileEditor,
        publishPost
    };

})();
