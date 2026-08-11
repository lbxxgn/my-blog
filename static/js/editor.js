document.addEventListener('DOMContentLoaded', function () {
    console.log('[Quill] DOMContentLoaded fired');
    console.log('[Quill] Quill is available:', typeof Quill !== 'undefined');
    const textarea = document.getElementById('content');
    console.log('[Quill] Textarea found:', !!textarea);
    if (textarea) {
        console.log('[Quill] Initializing Quill editor...');
        textarea.style.display = 'none';
        console.log('[Quill] Original textarea hidden');
        const editorContainer = document.createElement('div');
        editorContainer.id = 'quill-editor';
        editorContainer.style.minHeight = '400px';
        textarea.parentNode.insertBefore(editorContainer, textarea.nextSibling);
        console.log('[Quill] Editor container created');
        const csrfToken = document.querySelector('meta[name="csrf_token"]')
            ? document.querySelector('meta[name="csrf_token"]').getAttribute('content')
            : '';
        console.log('[Quill] Creating Quill instance...');
        let quill;
        try {
            // Custom indent format: use inline style so mobile/desktop readers respect it.
            const IndentStyle = Quill.import('formats/indent');
            if (IndentStyle && typeof IndentStyle.tagName !== 'undefined') {
                IndentStyle.whitelist = [1, 2, 3, 4, 5, 6, 7, 8];
            }
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
                            [{ 'list': 'ordered' }, { 'list': 'bullet' }],
                            [{ 'indent': '-1' }, { 'indent': '+1' }],
                            ['link', 'image', 'video'],
                            ['blockquote', 'code-block'],
                            ['clean']
                        ],
                        handlers: {
                            image: function () {
                                document.getElementById('imageUpload').click();
                            }
                        }
                    },
                    clipboard: { matchVisual: false }
                }
            });
            console.log('[Quill] Quill instance created successfully!');
        } catch (e) {
            console.error('[Quill] Error creating Quill:', e);
            return;
        }
        if (textarea.value) {
            quill.root.innerHTML = textarea.value;
        }
        quill.root.addEventListener('paste', function (e) {
            var html = e.clipboardData.getData('text/html');
            if (html && html.length > 100000) {
                e.preventDefault();
                var range = quill.getSelection(true);
                if (range) {
                    quill.insertText(range.index, e.clipboardData.getData('text/plain') || '');
                }
            }
        });
        var textChangeTimer;
        quill.on('text-change', function () {
            clearTimeout(textChangeTimer);
            textChangeTimer = setTimeout(function () {
                textarea.value = quill.root.innerHTML;
                window.dispatchEvent(new CustomEvent('editor:content-change', {
                    detail: { html: quill.root.innerHTML, text: quill.getText().trim() }
                }));
            }, 50);
        });
        const saveStatus = document.getElementById('saveStatus');
        const form = document.getElementById('editorForm');
        if (form) {
            form.addEventListener('submit', function () {
                textarea.value = quill.root.innerHTML;
                if (window.draftSync) {
                    window.draftSync.clearDraftCache();
                    window.draftSync.cleanupServerDraft();
                }
            });
        }
        const imageUpload = document.getElementById('imageUpload');
        if (imageUpload) {
            imageUpload.addEventListener('change', async function (e) {
                const files = Array.from(e.target.files);
                if (!files.length) return;
                const totalFiles = files.length;
                let uploadedCount = 0;
                let successCount = 0;
                let failedCount = 0;
                const failedFiles = [];
                const range = quill.getSelection();
                let insertIndex = range ? range.index : 0;
                for (let i = 0; i < totalFiles; i++) {
                    const file = files[i];
                    uploadedCount++;
                    try {
                        if (saveStatus) {
                            saveStatus.textContent = `正在上传第 ${uploadedCount}/${totalFiles}张图片...`;
                            saveStatus.className = 'save-status saving';
                        }
                        const formData = new FormData();
                        formData.append('file', file);
                        formData.append('csrf_token', csrfToken);
                        const response = await fetch('/admin/upload', {
                            method: 'POST',
                            headers: { 'X-CSRFToken': csrfToken },
                            body: formData
                        });
                        const data = await response.json();
                        if (data.success) {
                            quill.insertEmbed(insertIndex, 'image', data.url);
                            quill.insertText(insertIndex + 1, '\n');
                            insertIndex += 2;
                            successCount++;
                            window.dispatchEvent(new CustomEvent('editor:images-updated'));
                            if (data.optimization_id) {
                                pollImageOptimization(data.optimization_id, data.url, insertIndex - 2);
                            }
                        } else {
                            failedCount++;
                            failedFiles.push(`${file.name}:${data.error}`);
                        }
                        if (saveStatus) {
                            saveStatus.textContent = `上传中 ${uploadedCount}/${totalFiles}(成功:${successCount},失败:${failedCount})`;
                        }
                    } catch (error) {
                        failedCount++;
                        failedFiles.push(`${file.name}:${error.message}`);
                        console.error('Upload error:', error);
                    }
                }
                if (saveStatus) {
                    if (failedCount === 0) {
                        saveStatus.textContent = `✅ 成功上传 ${successCount}张图片！`;
                        saveStatus.className = 'save-status saved';
                        setTimeout(() => { saveStatus.textContent = ''; saveStatus.className = 'save-status'; }, 3000);
                    } else if (successCount === 0) {
                        saveStatus.textContent = `❌ 上传失败:${failedFiles[0]}`;
                        saveStatus.className = 'save-status error';
                        setTimeout(() => { saveStatus.textContent = ''; saveStatus.className = 'save-status'; }, 5000);
                    } else {
                        saveStatus.textContent = `⚠️ 部分成功:${successCount}张成功,${failedCount}张失败`;
                        saveStatus.className = 'save-status saved';
                        setTimeout(() => { saveStatus.textContent = ''; saveStatus.className = 'save-status'; }, 4000);
                    }
                }
                e.target.value = '';
                window.dispatchEvent(new CustomEvent('editor:images-updated'));
            });
        }
        const publishToggle = document.getElementById('publishToggle');
        const isPublishedCheckbox = document.getElementById('is_published');
        window.togglePublish = function () {
            if (publishToggle && isPublishedCheckbox) {
                textarea.value = quill.root.innerHTML;
                isPublishedCheckbox.checked = true;
                setTimeout(function () {
                    if (form.requestSubmit) {
                        form.requestSubmit();
                    } else {
                        var saveBtn = form.querySelector('button[type="submit"]');
                        if (saveBtn) {
                            saveBtn.click();
                        } else {
                            form.submit();
                        }
                    }
                }, 100);
            }
        };
        window.quill = quill;
        window.insertEditorHtml = function (html, index = null) {
            const range = quill.getSelection(true);
            const insertIndex = Number.isInteger(index) ? index : (range ? range.index : quill.getLength());
            quill.clipboard.dangerouslyPasteHTML(insertIndex, html);
            textarea.value = quill.root.innerHTML;
            window.dispatchEvent(new CustomEvent('editor:content-change', {
                detail: { html: quill.root.innerHTML, text: quill.getText().trim() }
            }));
            window.dispatchEvent(new CustomEvent('editor:images-updated'));
        };

        // ---- Quick first-line indent helper ----
        // On mobile it's hard to type multiple leading spaces; provide a toolbar button
        // and a Tab shortcut that inserts an inline text-indent style on the current paragraph.
        function applyFirstLineIndent() {
            const range = quill.getSelection(true);
            if (!range) return;
            const [line, offset] = quill.getLine(range.index);
            if (!line) return;
            const lineIndex = quill.getIndex(line);
            const length = line.length();
            // Quill paragraph format is called 'indent'; prefer CSS text-indent via custom format.
            // Instead, wrap the paragraph content in a styled span if not already indented.
            const existingFormat = quill.getFormat(lineIndex, length);
            const currentIndent = existingFormat && existingFormat.indent ? parseInt(existingFormat.indent, 10) : 0;
            const nextIndent = currentIndent + 1;
            // Cap at a reasonable max (each step = 2em)
            if (nextIndent > 4) return;
            quill.formatLine(lineIndex, length, 'indent', nextIndent);
            // Also add inline text-indent for readers/mobile renderers that strip Quill classes.
            const indentStyle = `text-indent:${nextIndent * 2}em`;
            const leafFormats = quill.getFormat(lineIndex, 1);
            if (!leafFormats['indent-style']) {
                // Use a custom blot registered below; fallback to attribute format.
                quill.formatText(lineIndex, Math.max(1, length - 1), 'indent-style', indentStyle, 'user');
            } else {
                quill.formatText(lineIndex, Math.max(1, length - 1), 'indent-style', indentStyle, 'user');
            }
            textarea.value = quill.root.innerHTML;
            window.dispatchEvent(new CustomEvent('editor:content-change', {
                detail: { html: quill.root.innerHTML, text: quill.getText().trim() }
            }));
        }

        // Register a custom inline format that emits text-indent via style attribute.
        const Inline = Quill.import('blots/inline');
        class IndentStyleBlot extends Inline {
            static create(value) {
                const node = super.create();
                node.setAttribute('style', value);
                return node;
            }
            static formats(node) {
                return node.getAttribute('style');
            }
        }
        IndentStyleBlot.blotName = 'indent-style';
        IndentStyleBlot.tagName = 'span';
        Quill.register(IndentStyleBlot);

        // Add a toolbar button after Quill renders
        const toolbar = quill.getModule('toolbar');
        if (toolbar && toolbar.container) {
            const indentBtn = document.createElement('button');
            indentBtn.type = 'button';
            indentBtn.className = 'ql-indent-firstline';
            indentBtn.title = '首行缩进';
            indentBtn.innerHTML = '↹';
            indentBtn.addEventListener('click', applyFirstLineIndent);
            toolbar.container.appendChild(indentBtn);
        }

        // Keyboard shortcut: Tab / Shift+Tab to indent/outdent first line at paragraph start.
        quill.keyboard.addBinding({ key: 'Tab' }, function (range) {
            const [line, offset] = quill.getLine(range.index);
            if (line && offset === 0) {
                applyFirstLineIndent();
                return false;
            }
            return true;
        });
    }

    window.generateAITags = async function () {
        const title = document.getElementById('title')?.value?.trim();
        const tagsInput = document.getElementById('tags');
        const aiGenerateBtn = document.getElementById('aiTagAssistBtn');
        if (!title) {
            showAIStatus('error', '请先输入文章标题');
            return;
        }
        if (!window.quill) {
            showAIStatus('error', '编辑器未初始化');
            return;
        }
        const content = window.quill.getText().trim();
        if (content.length < 50) {
            showAIStatus('error', '文章内容太少，请至少输入50个字符');
            return;
        }
        const pathParts = window.location.pathname.split('/');
        let postId = pathParts[pathParts.length - 1];
        if (isNaN(parseInt(postId))) {
            postId = null;
        }
        showAIStatus('loading', '🤖 AI正在分析文章内容...');
        if (aiGenerateBtn) {
            aiGenerateBtn.disabled = true;
            aiGenerateBtn.style.opacity = '0.6';
        }
        try {
            const csrfToken = document.querySelector('meta[name="csrf_token"]')
                ? document.querySelector('meta[name="csrf_token"]').getAttribute('content')
                : '';
            const response = await fetch('/admin/ai/generate-tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ title: title, content: content, post_id: postId })
            });
            if (!response.ok) {
                const responseText = await response.text();
                console.error('Server returned error:', response.status, responseText);
                showAIStatus('error', `❌ 服务器错误(${response.status}):${responseText.substring(0, 200)}...`);
                return;
            }
            let data;
            try {
                data = await response.json();
            } catch (e) {
                const responseText = await response.text();
                console.error('Failed to parse JSON:', responseText);
                showAIStatus('error', `❌ 响应格式错误:${responseText.substring(0, 200)}...`);
                return;
            }
            if (data.success) {
                const newTags = data.tags.join(', ');
                if (tagsInput) {
                    const existingTags = tagsInput.value.trim();
                    tagsInput.value = existingTags ? existingTags + ', ' + newTags : newTags;
                }
                showAIStatus('success', `✅ 已生成标签:${data.tags.join(', ')}(${data.tokens_used}tokens,约$${data.cost.toFixed(4)})`);
                if (window.EditorWorkbench?.updateAiSuggestionState) {
                    window.EditorWorkbench.updateAiSuggestionState('标签已更新');
                }
                if (window.EditorWorkbench?.openPanel) {
                    window.EditorWorkbench.openPanel('ai');
                }
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

    function showAIStatus(type, message) {
        const aiStatus = document.getElementById('aiStatus') || document.getElementById('aiToolsStatus') || document.getElementById('aiOrganizeStatus');
        if (!aiStatus) return;
        aiStatus.className = 'ai-status ' + type;
        aiStatus.innerHTML = type === 'loading' ? '<span class="ai-spinner"></span><span>' + message + '</span>' : message;
        aiStatus.style.display = 'flex';
    }

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
        }, 2000);
    }

    function updateImageToOptimized(originalUrl, sizes, compressionRatio, insertIndex) {
        if (!window.quill) return;
        const editor = window.quill.root;
        const images = editor.querySelectorAll('img');
        let targetImage = null;
        for (let img of images) {
            if (img.src.includes(originalUrl) || img.src === originalUrl) {
                targetImage = img;
                break;
            }
        }
        if (targetImage && sizes) {
            targetImage.srcset = `${sizes.thumbnail} 150w, ${sizes.medium} 600w, ${sizes.large} 1200w`;
            targetImage.sizes = '(max-width: 600px) 150px, (max-width: 1200px) 600px, 1200px';
            targetImage.src = sizes.medium;
            showOptimizationBadge(targetImage, compressionRatio);
        }
    }

    function showOptimizationBadge(imgElement, compressionRatio) {
        const badge = document.createElement('div');
        badge.className = 'image-optimized-badge';
        badge.textContent = `✓ 已优化 ${compressionRatio.toFixed(0)}%`;
        badge.style.cssText = `position:absolute;top:5px;right:5px;background:rgba(0,200,0,0.9);color:white;padding:4px 8px;border-radius:4px;font-size:12px;z-index:10;pointer-events:none;`;
        imgElement.style.position = imgElement.style.position || 'relative';
        if (imgElement.parentNode) {
            imgElement.parentNode.style.position = 'relative';
            imgElement.parentNode.appendChild(badge);
        }
        setTimeout(() => badge.remove(), 3000);
    }
});
