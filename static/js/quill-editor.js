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
        });

        // Auto-save functionality
        const saveStatus = document.getElementById('saveStatus');
        if (saveStatus) {
            let autoSaveTimeout;

            quill.on('text-change', function() {
                clearTimeout(autoSaveTimeout);
                saveStatus.textContent = '正在保存...';
                saveStatus.className = 'save-status saving';

                autoSaveTimeout = setTimeout(function() {
                    // Save to localStorage
                    localStorage.setItem('editor_content', quill.root.innerHTML);
                    saveStatus.textContent = '已自动保存 ' + new Date().toLocaleTimeString();
                    saveStatus.className = 'save-status saved';
                }, 1000);
            });

            // Load saved content on page load
            const savedContent = localStorage.getItem('editor_content');
            if (savedContent && !textarea.value) {
                // Create a custom modal for draft recovery
                const modal = document.createElement('div');
                modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center;';
                modal.innerHTML = `
                    <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 500px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);">
                        <h3 style="margin: 0 0 1rem 0; color: #333;">📝 发现未保存的草稿</h3>
                        <p style="color: #666; line-height: 1.6;">我们检测到您之前有未保存的内容，是否要恢复？</p>
                        <div style="display: flex; gap: 0.75rem; margin-top: 1.5rem;">
                            <button id="restoreDraft" style="flex: 1; padding: 0.75rem 1.5rem; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; font-weight: 500;">恢复草稿</button>
                            <button id="ignoreDraft" style="flex: 1; padding: 0.75rem 1.5rem; background: #6b7280; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1rem; font-weight: 500;">忽略并清除</button>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);

                // Handle restore button
                document.getElementById('restoreDraft').addEventListener('click', function() {
                    quill.root.innerHTML = savedContent;
                    textarea.value = savedContent;
                    document.body.removeChild(modal);
                });

                // Handle ignore button
                document.getElementById('ignoreDraft').addEventListener('click', function() {
                    localStorage.removeItem('editor_content');
                    document.body.removeChild(modal);
                });
            }
        }

        // Handle form submission
        const form = document.getElementById('editorForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                // Ensure Quill content is synced to textarea
                textarea.value = quill.root.innerHTML;
                // Clear draft after successful save
                localStorage.removeItem('editor_content');
            });
        }

        // Handle cancel button - clear draft cache
        const cancelButton = document.querySelector('a[href*="admin_dashboard"]');
        if (cancelButton) {
            cancelButton.addEventListener('click', function(e) {
                // Check if there's unsaved content
                const currentContent = quill.root.innerHTML;
                const savedContent = localStorage.getItem('editor_content');

                // Only show confirmation if there's content that hasn't been saved to database
                if (currentContent && currentContent !== '<p><br></p>' && !textarea.value) {
                    if (confirm('您有未保存的内容，确定要离开吗？点击"确定"将清除草稿缓存。')) {
                        localStorage.removeItem('editor_content');
                    } else {
                        e.preventDefault();
                        return false;
                    }
                } else {
                    // No unsaved content, just clear the draft cache
                    localStorage.removeItem('editor_content');
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
    }

    // AI Tag Generation Function
    window.generateAITags = async function() {
        const title = document.getElementById('title')?.value?.trim();
        const tagsInput = document.getElementById('tags');
        const aiStatus = document.getElementById('aiStatus');
        const aiGenerateBtn = document.getElementById('aiGenerateBtn');

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

                // Auto-hide success message after 5 seconds
                setTimeout(() => {
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
        const aiStatus = document.getElementById('aiStatus');
        if (!aiStatus) return;

        aiStatus.className = 'ai-status ' + type;
        aiStatus.innerHTML = type === 'loading'
            ? '<span class="ai-spinner"></span><span>' + message + '</span>'
            : message;
        aiStatus.style.display = 'flex';
    }
});
