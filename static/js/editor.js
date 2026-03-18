// Quill Rich Text Editor
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Quill] DOMContentLoaded fired');
    console.log('[Quill] Quill is available:', typeof Quill !== 'undefined');

    const textarea = document.getElementById('content');
    console.log('[Quill] Textarea found:', !!textarea);

    if (textarea) {
        console.log('[Quill] Initializing Quill editor...');

        // Hide the original textarea
        textarea.style.display = 'none';
        console.log('[Quill] Original textarea hidden');

        // Create a container for Quill editor
        const editorContainer = document.createElement('div');
        editorContainer.id = 'quill-editor';
        editorContainer.style.minHeight = '400px';
        textarea.parentNode.insertBefore(editorContainer, textarea.nextSibling);
        console.log('[Quill] Editor container created');

        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf_token"]')
            ? document.querySelector('meta[name="csrf_token"]').getAttribute('content')
            : '';

        // Initialize Quill
        console.log('[Quill] Creating Quill instance...');
        let quill;

        try {
            quill = new Quill('#quill-editor', {
                theme: 'snow',
                placeholder: '开始写作...\n\n支持富文本粘贴，可直接从其他网站复制文章内容',
                modules: {
                    toolbar: {
                        container: [
                            [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
                            ['bold', 'italic', 'underline', 'strike'],
                            [{ 'color': [] }, { 'background': [] }],
                            [{ 'align': [] }],
                            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                            [{ 'indent': '-1'}, { 'indent': '+1' }],
                            ['link', 'image', 'video'],
                            ['blockquote', 'code-block'],
                            ['clean']
                        ],
                        handlers: {
                            image: function() {
                                // Trigger image upload
                                document.getElementById('imageUpload').click();
                            }
                        }
                    },
                    clipboard: {
                        // Allow pasting HTML content
                        matchVisual: false
                    }
                }
            });
            console.log('[Quill] Quill instance created successfully!');
        } catch (e) {
            console.error('[Quill] Error creating Quill:', e);
            return;
        }

        // Load existing content if editing
        if (textarea.value) {
            quill.root.innerHTML = textarea.value;
        }

        // Sync content to textarea on change
        quill.on('text-change', function() {
            textarea.value = quill.root.innerHTML;
            window.dispatchEvent(new CustomEvent('editor:content-change', {
                detail: {
                    html: quill.root.innerHTML,
                    text: quill.getText().trim()
                }
            }));
        });

        const saveStatus = document.getElementById('saveStatus');

        // Handle form submission
        const form = document.getElementById('editorForm');
        if (form) {
            form.addEventListener('submit', function() {
                // Ensure Quill content is synced to textarea
                textarea.value = quill.root.innerHTML;
                if (window.draftSync) {
                    window.draftSync.clearDraftCache();
                    window.draftSync.cleanupServerDraft();
                }
            });
        }

        // Custom image upload handler
        const imageUpload = document.getElementById('imageUpload');
        if (imageUpload) {
            imageUpload.addEventListener('change', async function(e) {
                const files = Array.from(e.target.files);
                if (!files.length) return;

                const totalFiles = files.length;
                let uploadedCount = 0;
                let successCount = 0;
                let failedCount = 0;
                const failedFiles = [];

                // Get current cursor position to insert images at
                const range = quill.getSelection();
                let insertIndex = range ? range.index : 0;

                for (let i = 0; i < totalFiles; i++) {
                    const file = files[i];
                    uploadedCount++;

                    try {
                        // Show progress
                        if (saveStatus) {
                            saveStatus.textContent = `正在上传第 ${uploadedCount}/${totalFiles} 张图片...`;
                            saveStatus.className = 'save-status saving';
                        }

                        const formData = new FormData();
                        formData.append('file', file);
                        formData.append('csrf_token', csrfToken);

                        const response = await fetch('/admin/upload', {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrfToken
                            },
                            body: formData
                        });

                        const data = await response.json();

                        if (data.success) {
                            // Insert image into Quill editor
                            quill.insertEmbed(insertIndex, 'image', data.url);
                            // Insert a line break after each image
                            quill.insertText(insertIndex + 1, '\n');
                            // Move insert index forward
                            insertIndex += 2;
                            successCount++;
                            window.dispatchEvent(new CustomEvent('editor:images-updated'));

                            // Start polling for optimization if optimization_id is provided
                            if (data.optimization_id) {
                                pollImageOptimization(data.optimization_id, data.url, insertIndex - 2);
                            }
                        } else {
                            failedCount++;
                            failedFiles.push(`${file.name}: ${data.error}`);
                        }

                        // Show progress update
                        if (saveStatus) {
                            saveStatus.textContent = `上传中 ${uploadedCount}/${totalFiles} (成功: ${successCount}, 失败: ${failedCount})`;
                        }

                    } catch (error) {
                        failedCount++;
                        failedFiles.push(`${file.name}: ${error.message}`);
                        console.error('Upload error:', error);
                    }
                }

                // Show final result
                if (saveStatus) {
                    if (failedCount === 0) {
                        saveStatus.textContent = `✅ 成功上传 ${successCount} 张图片！`;
                        saveStatus.className = 'save-status saved';
                        setTimeout(() => {
                            saveStatus.textContent = '';
                            saveStatus.className = 'save-status';
                        }, 3000);
                    } else if (successCount === 0) {
                        saveStatus.textContent = `❌ 上传失败: ${failedFiles[0]}`;
                        saveStatus.className = 'save-status error';
                        setTimeout(() => {
                            saveStatus.textContent = '';
                            saveStatus.className = 'save-status';
                        }, 5000);
                    } else {
                        saveStatus.textContent = `⚠️ 部分成功: ${successCount}张成功, ${failedCount}张失败`;
                        saveStatus.className = 'save-status saved';
                        setTimeout(() => {
                            saveStatus.textContent = '';
                            saveStatus.className = 'save-status';
                        }, 4000);
                    }
                }

                // Reset file input
                e.target.value = '';
                window.dispatchEvent(new CustomEvent('editor:images-updated'));
            });
        }

        // Custom button handlers
        const publishToggle = document.getElementById('publishToggle');
        const isPublishedCheckbox = document.getElementById('is_published');

        window.togglePublish = function() {
            if (publishToggle && isPublishedCheckbox) {
                // Sync content before submit
                textarea.value = quill.root.innerHTML;
                isPublishedCheckbox.checked = true;
                // Submit form after a short delay to allow checkbox to be set
                setTimeout(() => {
                    form.submit();
                }, 100);
            }
        };

        // Handle paste events to clean up HTML
        quill.clipboard.addMatcher(Node.ELEMENT_NODE, function(node, delta) {
            // Remove unwanted styles and attributes from pasted content
            const removed = [];
            delta.ops.forEach(function(op) {
                if (op.insert && typeof op.insert === 'string') {
                    // Clean up extra whitespace
                    op.insert = op.insert.replace(/\n{3,}/g, '\n\n');
                }
            });
            return delta;
        });

        // Expose quill instance globally for debugging
        window.quill = quill;
        window.insertEditorHtml = function(html, index = null) {
            const range = quill.getSelection(true);
            const insertIndex = Number.isInteger(index) ? index : (range ? range.index : quill.getLength());
            quill.clipboard.dangerouslyPasteHTML(insertIndex, html);
            textarea.value = quill.root.innerHTML;
            window.dispatchEvent(new CustomEvent('editor:content-change', {
                detail: {
                    html: quill.root.innerHTML,
                    text: quill.getText().trim()
                }
            }));
            window.dispatchEvent(new CustomEvent('editor:images-updated'));
        };
    }

    // AI Tag Generation Function
    window.generateAITags = async function() {
        const title = document.getElementById('title')?.value?.trim();
        const tagsInput = document.getElementById('tags');
        const aiGenerateBtn = document.getElementById('aiTagAssistBtn');

        // Validate inputs
        if (!title) {
            showAIStatus('error', '请先输入文章标题');
            return;
        }

        if (!window.quill) {
            showAIStatus('error', '编辑器未初始化');
            return;
        }

        // Get content from Quill editor
        const content = window.quill.getText().trim();

        if (content.length < 50) {
            showAIStatus('error', '文章内容太少，请至少输入50个字符');
            return;
        }

        // Get post_id from URL (if editing)
        const pathParts = window.location.pathname.split('/');
        let postId = pathParts[pathParts.length - 1];
        // If the last part is not a number, set postId to null
        if (isNaN(parseInt(postId))) {
            postId = null;
        }

        // Show loading state
        showAIStatus('loading', '🤖 AI正在分析文章内容...');
        if (aiGenerateBtn) {
            aiGenerateBtn.disabled = true;
            aiGenerateBtn.style.opacity = '0.6';
        }

        try {
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf_token"]')
                ? document.querySelector('meta[name="csrf_token"]').getAttribute('content')
                : '';

            const response = await fetch('/admin/ai/generate-tags', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    title: title,
                    content: content,
                    post_id: postId
                })
            });

            // Check if response is OK
            if (!response.ok) {
                const responseText = await response.text();
                console.error('Server returned error:', response.status, responseText);
                showAIStatus('error', `❌ 服务器错误 (${response.status}): ${responseText.substring(0, 200)}...`);
                return;
            }

            // Try to parse as JSON
            let data;
            try {
                data = await response.json();
            } catch (e) {
                const responseText = await response.text();
                console.error('Failed to parse JSON:', responseText);
                showAIStatus('error', `❌ 响应格式错误: ${responseText.substring(0, 200)}...`);
                return;
            }

            if (data.success) {
                // Update tags input with generated tags
                const newTags = data.tags.join(', ');
                if (tagsInput) {
                    // Append to existing tags or replace
                    const existingTags = tagsInput.value.trim();
                    tagsInput.value = existingTags
                        ? existingTags + ', ' + newTags
                        : newTags;
                }

                // Show success message
                showAIStatus(
                    'success',
                    `✅ 已生成标签: ${data.tags.join(', ')} (${data.tokens_used} tokens, 约$${data.cost.toFixed(4)})`
                );
                if (window.EditorWorkbench?.updateAiSuggestionState) {
                    window.EditorWorkbench.updateAiSuggestionState('标签已更新');
                }
                if (window.EditorWorkbench?.openPanel) {
                    window.EditorWorkbench.openPanel('ai');
                }

                // Auto-hide success message after 5 seconds
                setTimeout(() => {
                    const aiStatus = document.getElementById('aiStatus') || document.getElementById('aiToolsStatus') || document.getElementById('aiOrganizeStatus');
                    if (aiStatus) aiStatus.style.display = 'none';
                }, 5000);
            } else {
                showAIStatus('error', '❌ ' + data.error);
            }
        } catch (error) {
            showAIStatus('error', '❌ 生成失败: ' + error.message);
        } finally {
            if (aiGenerateBtn) {
                aiGenerateBtn.disabled = false;
                aiGenerateBtn.style.opacity = '1';
            }
        }
    };

    // Helper function to show AI status messages
    function showAIStatus(type, message) {
        const aiStatus = document.getElementById('aiStatus') || document.getElementById('aiToolsStatus') || document.getElementById('aiOrganizeStatus');
        if (!aiStatus) return;

        aiStatus.className = 'ai-status ' + type;
        aiStatus.innerHTML = type === 'loading'
            ? '<span class="ai-spinner"></span><span>' + message + '</span>'
            : message;
        aiStatus.style.display = 'flex';
    }

    // 轮询图片优化状态
    function pollImageOptimization(optimizationId, originalUrl, insertIndex) {
        const maxAttempts = 10;
        let attempts = 0;

        const poll = setInterval(async () => {
            attempts++;

            try {
                const response = await fetch(`/admin/image-status/${optimizationId}`);
                const result = await response.json();

                if (result.status === 'completed') {
                    clearInterval(poll);
                    updateImageToOptimized(originalUrl, result.sizes, result.compression_ratio, insertIndex);
                    console.log(`✓ 图片已优化，大小减少${result.compression_ratio.toFixed(0)}%`);

                } else if (result.status === 'failed') {
                    clearInterval(poll);
                    console.warn('图片优化失败，继续使用原图');
                }

            } catch (error) {
                console.error('查询优化状态失败:', error);
            }

            if (attempts >= maxAttempts) {
                clearInterval(poll);
            }
        }, 2000); // 每2秒查询一次
    }

    // 更新为优化后的图片
    function updateImageToOptimized(originalUrl, sizes, compressionRatio, insertIndex) {
        if (!window.quill) return;

        const editor = window.quill.root;

        // 找到刚插入的图片
        const images = editor.querySelectorAll('img');
        let targetImage = null;

        for (let img of images) {
            if (img.src.includes(originalUrl) || img.src === originalUrl) {
                targetImage = img;
                break;
            }
        }

        if (targetImage && sizes) {
            // 创建响应式图片
            targetImage.srcset = `
                ${sizes.thumbnail} 150w,
                ${sizes.medium} 600w,
                ${sizes.large} 1200w
            `.trim().replace(/\s+/g, ' ');

            targetImage.sizes = '(max-width: 600px) 150px, (max-width: 1200px) 600px, 1200w';
            targetImage.src = sizes.medium; // 默认使用中等尺寸

            // 显示优化徽章
            showOptimizationBadge(targetImage, compressionRatio);
        }
    }

    // 显示优化徽章
    function showOptimizationBadge(imgElement, compressionRatio) {
        const badge = document.createElement('div');
        badge.className = 'image-optimized-badge';
        badge.textContent = `✓ 已优化 ${compressionRatio.toFixed(0)}%`;
        badge.style.cssText = `
            position: absolute;
            top: 5px;
            right: 5px;
            background: rgba(0, 200, 0, 0.9);
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 10;
            pointer-events: none;
        `;

        imgElement.style.position = imgElement.style.position || 'relative';

        // 插入徽章到图片的父元素
        if (imgElement.parentNode) {
            imgElement.parentNode.style.position = 'relative';
            imgElement.parentNode.appendChild(badge);
        }

        // 3秒后移除
        setTimeout(() => badge.remove(), 3000);
    }
});
