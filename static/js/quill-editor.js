// Quill Rich Text Editor
document.addEventListener('DOMContentLoaded', function() {
    const textarea = document.getElementById('content');

    if (textarea) {
        // Hide the original textarea
        textarea.style.display = 'none';

        // Create a container for Quill editor
        const editorContainer = document.createElement('div');
        editorContainer.id = 'quill-editor';
        editorContainer.style.minHeight = '400px';
        textarea.parentNode.insertBefore(editorContainer, textarea.nextSibling);

        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf_token"]')
            ? document.querySelector('meta[name="csrf_token"]').getAttribute('content')
            : '';

        // Initialize Quill
        const quill = new Quill('#quill-editor', {
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
                if (confirm('发现未保存的草稿，是否恢复？')) {
                    quill.root.innerHTML = savedContent;
                    textarea.value = savedContent;
                }
            }
        }

        // Handle form submission
        const form = document.getElementById('editorForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                // Ensure Quill content is synced to textarea
                textarea.value = quill.root.innerHTML;
            });
        }

        // Custom image upload handler
        const imageUpload = document.getElementById('imageUpload');
        if (imageUpload) {
            imageUpload.addEventListener('change', async function(e) {
                const file = e.target.files[0];
                if (!file) return;

                const formData = new FormData();
                formData.append('file', file);
                formData.append('csrf_token', csrfToken);

                try {
                    if (saveStatus) {
                        saveStatus.textContent = '正在上传图片...';
                        saveStatus.className = 'save-status saving';
                    }

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
                        const range = quill.getSelection();
                        quill.insertEmbed(range ? range.index : 0, 'image', data.url);

                        if (saveStatus) {
                            saveStatus.textContent = '图片上传成功！';
                            saveStatus.className = 'save-status saved';
                            setTimeout(() => {
                                saveStatus.textContent = '';
                                saveStatus.className = 'save-status';
                            }, 2000);
                        }
                    } else {
                        if (saveStatus) {
                            saveStatus.textContent = '上传失败: ' + data.error;
                            saveStatus.className = 'save-status error';
                            setTimeout(() => {
                                saveStatus.textContent = '';
                                saveStatus.className = 'save-status';
                            }, 3000);
                        } else {
                            alert('上传失败: ' + data.error);
                        }
                    }
                } catch (error) {
                    if (saveStatus) {
                        saveStatus.textContent = '上传失败: ' + error.message;
                        saveStatus.className = 'save-status error';
                        setTimeout(() => {
                            saveStatus.textContent = '';
                            saveStatus.className = 'save-status';
                        }, 3000);
                    } else {
                        alert('上传失败: ' + error.message);
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

        // Get post_id for AI generation (if editing)
        const postId = {% if post %}{{ post.id }}{% else %}null{% endif %};
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

        // Show loading state
        showAIStatus('loading', '🤖 AI正在分析文章内容...');
        if (aiGenerateBtn) {
            aiGenerateBtn.disabled = true;
            aiGenerateBtn.style.opacity = '0.6';
        }

        try {
            const response = await fetch('/admin/ai/generate-tags', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title,
                    content: content,
                    post_id: postId
                })
            });

            const data = await response.json();

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
