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

    // 初始化
    document.addEventListener('DOMContentLoaded', function() {
        initMobileEditor();
        loadDraft();
    });

    /**
     * 打开移动端编辑器
     */
    window.openMobileEditor = function() {
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
    };

    /**
     * 关闭移动端编辑器
     */
    window.closeMobileEditor = function() {
        const overlay = document.getElementById('mobileEditorOverlay');
        const panel = document.getElementById('mobileEditorPanel');

        if (overlay && panel) {
            overlay.classList.remove('show');
            panel.classList.remove('show');
            document.body.style.overflow = '';
        }
    };

    /**
     * 初始化编辑器
     */
    function initMobileEditor() {
        // 关闭按钮
        const closeBtn = document.getElementById('mobileEditorClose');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                const textarea = document.getElementById('mobileEditorTextarea');
                const title = document.getElementById('mobileEditorTitle');
                const hasContent = (textarea && textarea.value.trim().length > 0) ||
                                   (title && title.value.trim().length > 0);

                if (hasContent) {
                    if (confirm('确定要关闭吗？未保存的内容将丢失。')) {
                        clearDraft();
                        closeMobileEditor();
                    }
                } else {
                    clearDraft();
                    closeMobileEditor();
                }
            });
        }

        // 点击遮罩关闭
        const overlay = document.getElementById('mobileEditorOverlay');
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) {
                    const textarea = document.getElementById('mobileEditorTextarea');
                    const title = document.getElementById('mobileEditorTitle');
                    const hasContent = (textarea && textarea.value.trim().length > 0) ||
                                       (title && title.value.trim().length > 0);

                    if (hasContent) {
                        if (confirm('确定要关闭吗？未保存的内容将丢失。')) {
                            clearDraft();
                            closeMobileEditor();
                        }
                    } else {
                        clearDraft();
                        closeMobileEditor();
                    }
                }
            });
        }

        // 文本输入 - 自动保存草稿
        const textarea = document.getElementById('mobileEditorTextarea');
        if (textarea) {
            textarea.addEventListener('input', function() {
                saveDraft();
                updatePublishButton();
            });
        }

        // 标题输入
        const titleInput = document.getElementById('mobileEditorTitle');
        if (titleInput) {
            titleInput.addEventListener('input', function() {
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
            tagsBtn.addEventListener('click', openTagsSelector);
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
    }

    /**
     * 处理图片选择
     */
    function handleImageSelect(e) {
        const files = e.target.files;
        if (!files || files.length === 0) return;

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
    }

    /**
     * 打开标签选择器
     */
    function openTagsSelector() {
        const overlay = document.getElementById('tagsSelectorOverlay');
        const panel = document.getElementById('tagsSelectorPanel');

        if (overlay && panel) {
            overlay.classList.add('show');
            panel.classList.add('show');
            renderTagsList();
        }
    }

    /**
     * 渲染标签列表
     */
    function renderTagsList() {
        const container = document.getElementById('tagsSelectorContent');
        if (!container) return;

        // 获取现有标签（从页面数据或 API）
        const allTags = window.availableTags || [];

        let html = '';

        // 常用标签（已选的在前）
        const selectedTagIds = selectedTags.map(t => t.id);
        const recentTags = allTags.filter(t => selectedTagIds.includes(t.id));
        const otherTags = allTags.filter(t => !selectedTagIds.includes(t.id));

        if (recentTags.length > 0) {
            html += '<div class="selector-section-title">常用标签</div>';
            recentTags.forEach(tag => {
                html += renderTagItem(tag, true);
            });
        }

        if (otherTags.length > 0) {
            html += '<div class="selector-section-title">全部标签</div>';
            otherTags.forEach(tag => {
                html += renderTagItem(tag, false);
            });
        }

        // 新建标签选项
        html += `
            <div class="selector-item" onclick="window.createNewTag && window.createNewTag()">
                <span class="selector-item-name">+ 新建标签</span>
            </div>
        `;

        container.innerHTML = html;

        // 绑定点击事件
        container.querySelectorAll('.selector-item[data-tag-id]').forEach(item => {
            item.addEventListener('click', function() {
                const tagId = this.getAttribute('data-tag-id');
                if (tagId) {
                    toggleTagSelection(parseInt(tagId));
                }
            });
        });
    }

    /**
     * 渲染单个标签项
     */
    function renderTagItem(tag, selected) {
        const isSelected = selectedTags.some(t => t.id === tag.id);
        return `
            <div class="selector-item ${isSelected ? 'selected' : ''}" data-tag-id="${tag.id}">
                <span class="selector-item-name">#${tag.name}</span>
                <span class="selector-item-check">${isSelected ? '✓' : ''}</span>
            </div>
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

        renderTagsList();
        renderSelections();
        saveDraft();
    }

    /**
     * 打开分类选择器
     */
    function openCategorySelector() {
        const overlay = document.getElementById('categorySelectorOverlay');
        const panel = document.getElementById('categorySelectorPanel';

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
            const icons = { public: '🌐', login: '🔒', private: '👁️' };
            const icon = btn.querySelector('.toolbar-icon');
            if (icon) icon.textContent = icons[accessLevel];
        }

        saveDraft();
    }

    /**
     * 创建新标签
     */
    window.createNewTag = function() {
        const name = prompt('请输入新标签名称：');
        if (name && name.trim()) {
            // 这里应该调用 API 创建标签
            // 暂时先添加到本地
            const newTag = { id: Date.now(), name: name.trim() };
            if (!window.availableTags) window.availableTags = [];
            window.availableTags.push(newTag);
            selectedTags.push(newTag);
            renderTagsList();
            renderSelections();
            saveDraft();
        }
    };

    /**
     * 更新发布按钮状态
     */
    function updatePublishButton() {
        const textarea = document.getElementById('mobileEditorTextarea');
        const publishBtn = document.getElementById('mobileEditorPublish');

        if (textarea && publishBtn) {
            const hasContent = textarea.value.trim().length > 0;
            publishBtn.disabled = !hasContent;
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
            if (!draft || !draft.content) return;

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
        updatePublishButton();
    }

    /**
     * 发布文章
     */
    async function publishPost() {
        const title = document.getElementById('mobileEditorTitle')?.value || '';
        const content = document.getElementById('mobileEditorTextarea')?.value || '';

        if (!content.trim()) {
            alert('请输入内容');
            return;
        }

        const publishBtn = document.getElementById('mobileEditorPublish');
        publishBtn.disabled = true;
        publishBtn.textContent = '发布中...';

        try {
            // 构建 FormData
            const formData = new FormData();
            formData.append('title', title || '无标题');
            formData.append('content', content);
            formData.append('is_published', 'true');
            formData.append('access_level', accessLevel);

            if (selectedCategory) {
                formData.append('category_id', selectedCategory.id);
            }

            if (selectedTags.length > 0) {
                formData.append('tags', selectedTags.map(t => t.name).join(', '));
            }

            // 获取 CSRF token
            const csrfToken = document.querySelector('meta[name="csrf_token"]')?.content;

            // 上传图片（如果有）- 这里简化处理，实际项目中需要先上传图片
            // 然后将图片 URL 插入内容

            // 提交文章 - 使用 fetch API 提交到编辑器
            const response = await fetch('/admin/editor', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            if (response.ok) {
                clearDraft();
                closeMobileEditor();
                alert('发布成功！');
                // 刷新页面
                window.location.reload();
            } else {
                const error = await response.text();
                throw new Error(error || '发布失败');
            }
        } catch (error) {
            console.error('Publish error:', error);
            alert('发布失败：' + (error.message || '未知错误'));
            publishBtn.disabled = false;
            publishBtn.textContent = '发布';
        }
    }

    // 暴露全局函数
    window.MobileEditor = {
        open: openMobileEditor,
        close: closeMobileEditor,
        publishPost
    };

})();
