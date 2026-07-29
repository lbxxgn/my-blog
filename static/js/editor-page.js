// 后台文章编辑器页面脚本（由模板内联 JS 外置而来）
// Publish and save article
function togglePublish() {
    const contentInput = document.getElementById('content');
    let content = '';
    if (window.quill) {
        content = window.quill.getText().trim();
    } else {
        content = contentInput.value.trim();
    }

    if (!content) {
        (window.showAppToast || alert)('请填写文章内容', 'error');
        contentInput.focus();
        return;
    }

    const checkbox = document.getElementById('is_published');
    const form = document.getElementById('editorForm');

    // Set publish status to true
    checkbox.checked = true;

    // Submit the form (title will be auto-generated if empty)
    form.submit();
}

// Toggle password field visibility
function togglePasswordField() {
    const accessLevel = document.getElementById('access_level').value;
    const passwordInput = document.getElementById('access_password');

    if (accessLevel === 'password') {
        passwordInput.style.display = 'inline-block';
    } else {
        passwordInput.style.display = 'none';
        passwordInput.value = '';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    togglePasswordField();

    // Check AI features status and show/hide accordingly
    checkAIFeaturesStatus();
});

// Check AI features status from server
async function checkAIFeaturesStatus() {
    try {
        const response = await fetch('/admin/ai/status');
        if (response.ok) {
            const data = await response.json();
            const aiEnabled = data.ai_enabled || false;

            console.log('[AI Features] Status:', aiEnabled ? 'enabled' : 'disabled');

            // Hide all AI features if disabled
            if (!aiEnabled) {
                const aiFeatures = document.querySelectorAll('.ai-feature');
                aiFeatures.forEach(element => {
                    element.style.display = 'none';
                });
                console.log('[AI Features] Hidden all AI features');
            }
        }
    } catch (error) {
        console.error('[AI Features] Failed to check status:', error);
        // On error, show features by default
    }
}

// Show AI tools status message
function showAiToolsStatus(type, message) {
    const statusDiv = document.getElementById('aiToolsStatus');
    if (!statusDiv) return;
    statusDiv.className = 'ai-status ' + type;
    statusDiv.style.display = 'flex';
    statusDiv.innerHTML = message;

    // Auto hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

function showEditorToast(message, type = 'success') {
    if (window.showAppToast) {
        window.showAppToast(message, type);
    }
}

function escapeInlineHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function openAiAssistPanel() {
    if (window.EditorWorkbench?.openPanel) {
        window.EditorWorkbench.openPanel('ai');
    }
}

function setAiResultCardVisibility(cardId, visible) {
    const card = document.getElementById(cardId);
    if (card) {
        card.hidden = !visible;
    }
}

function renderAiResultText(targetId, text) {
    const node = document.getElementById(targetId);
    if (node) {
        node.textContent = text || '';
    }
}

function renderAiRecommendationList(recommendations) {
    const body = document.getElementById('aiRecommendationResultBody');
    if (!body) return;

    if (!recommendations || !recommendations.length) {
        body.innerHTML = '<div class="workbench-empty">暂无相关文章推荐。</div>';
        return;
    }

    body.innerHTML = `
        <div class="ai-result-list">
            ${recommendations.map((rec) => {
                if (rec && typeof rec === 'object' && !Array.isArray(rec) && rec.title && rec.url) {
                    return `<a href="${rec.url}" target="_blank" rel="noopener noreferrer">${escapeInlineHtml(rec.title)}</a>`;
                }
                if (typeof rec === 'number' || (typeof rec === 'string' && !isNaN(parseInt(rec, 10)))) {
                    return `<span>文章 #${escapeInlineHtml(String(rec))}</span>`;
                }
                return `<span>${escapeInlineHtml(JSON.stringify(rec))}</span>`;
            }).join('')}
        </div>
    `;
}

function prependHtmlToEditor(html) {
    if (typeof window.insertEditorHtml === 'function') {
        window.insertEditorHtml(html, 0);
    }
}

function appendHtmlToEditor(html) {
    if (typeof window.insertEditorHtml === 'function') {
        window.insertEditorHtml(html);
    }
}

// Generate AI summary
async function generateAISummary() {
    const title = document.getElementById('title').value.trim();

    // Get content from Quill editor if available, otherwise from textarea
    let content;
    if (window.quill) {
        content = window.quill.getText().trim();
    } else {
        content = document.getElementById('content').value.trim();
    }

    if (!title) {
        showAiToolsStatus('error', '❌ 请先输入文章标题');
        return;
    }

    if (!content) {
        showAiToolsStatus('error', '❌ 请先输入文章内容');
        return;
    }

    // Get post ID from URL if editing
    const pathParts = window.location.pathname.split('/');
    let postId = pathParts[pathParts.length - 1];
    // If postId is not a number, we're creating a new post
    if (isNaN(parseInt(postId))) {
        postId = null;
    }

    showAiToolsStatus('loading', '🤖 AI正在生成摘要...');

    const csrfToken = document.querySelector('meta[name="csrf_token"]').content;

    try {
        const response = await fetch('/admin/ai/generate-summary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                post_id: postId,
                title: title,
                content: content
            })
        });

        const data = await response.json();

        if (data.success) {
            const summary = data.summary;
            renderAiResultText('aiSummaryResultBody', summary);
            setAiResultCardVisibility('aiSummaryResultCard', true);
            const applyButton = document.getElementById('applyGeneratedSummary');
            if (applyButton) {
                applyButton.onclick = () => {
                    prependHtmlToEditor(`<p><strong>摘要：</strong>${escapeInlineHtml(summary)}</p><p><br></p>`);
                    showAiToolsStatus('success', '摘要已插入到正文开头。');
                    showEditorToast('摘要已插入正文');
                };
            }
            openAiAssistPanel();
            showAiToolsStatus('success', `✅ 摘要已生成 (${data.tokens_used} tokens, ${data.model})`);
        } else {
            showAiToolsStatus('error', `❌ ${data.error || '生成失败'}`);
        }
    } catch (error) {
        showAiToolsStatus('error', `❌ 网络错误: ${error.message}`);
    }
}

// Generate AI recommendations
async function generateAIRecommendations() {
    const title = document.getElementById('title').value.trim();

    // Get content from Quill editor if available, otherwise from textarea
    let content;
    if (window.quill) {
        content = window.quill.getText().trim();
    } else {
        content = document.getElementById('content').value.trim();
    }

    // Get post ID from URL if editing
    const pathParts = window.location.pathname.split('/');
    let postId = pathParts[pathParts.length - 1];
    if (isNaN(parseInt(postId))) {
        postId = null;
    }

    if (!postId) {
        showAiToolsStatus('error', '❌ 请先保存文章，然后再生成推荐');
        return;
    }

    if (!title || !content) {
        showAiToolsStatus('error', '❌ 请先输入文章标题和内容');
        return;
    }

    showAiToolsStatus('loading', '🤖 AI正在分析并推荐相关文章...');

    const csrfToken = document.querySelector('meta[name="csrf_token"]').content;

    try {
        const response = await fetch('/admin/ai/recommend-posts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                post_id: postId,
                title: title,
                content: content
            })
        });

        const data = await response.json();

        if (data.success && data.recommendations.length > 0) {
            renderAiRecommendationList(data.recommendations);
            setAiResultCardVisibility('aiRecommendationResultCard', true);
            openAiAssistPanel();
            showAiToolsStatus('success', `✅ 已生成 ${data.recommendations.length} 条相关文章推荐 (${data.tokens_used} tokens)`);
        } else if (data.success && data.recommendations.length === 0) {
            renderAiRecommendationList([]);
            setAiResultCardVisibility('aiRecommendationResultCard', true);
            openAiAssistPanel();
            showAiToolsStatus('success', '✅ 暂无相关文章推荐');
        } else {
            showAiToolsStatus('error', `❌ ${data.error || '生成失败'}`);
        }
    } catch (error) {
        showAiToolsStatus('error', `❌ 网络错误: ${error.message}`);
    }
}

// Continue writing with AI
async function continueAIWriting() {
    const title = document.getElementById('title').value.trim();

    // Get content from Quill editor if available, otherwise from textarea
    let content;
    if (window.quill) {
        content = window.quill.getText().trim();
    } else {
        content = document.getElementById('content').value.trim();
    }

    if (!title) {
        showAiToolsStatus('error', '❌ 请先输入文章标题');
        return;
    }

    if (!content || content.length < 100) {
        showAiToolsStatus('error', '❌ 文章内容太短，请至少写100字后再使用AI续写');
        return;
    }

    // Get post ID from URL if editing
    const pathParts = window.location.pathname.split('/');
    let postId = pathParts[pathParts.length - 1];
    // If postId is not a number, we're creating a new post
    if (isNaN(parseInt(postId))) {
        postId = null;
    }

    showAiToolsStatus('loading', '🤖 AI正在续写内容...');

    const csrfToken = document.querySelector('meta[name="csrf_token"]').content;

    try {
        const response = await fetch('/admin/ai/continue-writing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                post_id: postId,
                title: title,
                content: content
            })
        });

        const data = await response.json();

        if (data.success) {
            const continuation = data.continuation;
            renderAiResultText('aiContinuationResultBody', continuation);
            setAiResultCardVisibility('aiContinuationResultCard', true);
            const applyButton = document.getElementById('applyGeneratedContinuation');
            if (applyButton) {
                applyButton.onclick = () => {
                    appendHtmlToEditor(`<p>${escapeInlineHtml(continuation)}</p>`);
                    showAiToolsStatus('success', '续写内容已插入到正文末尾。');
                    showEditorToast('续写内容已插入正文');
                };
            }
            openAiAssistPanel();
            showAiToolsStatus('success', `✅ 续写完成 (${data.tokens_used} tokens, ${data.model})`);
        } else {
            showAiToolsStatus('error', `❌ ${data.error || '生成失败'}`);
        }
    } catch (error) {
        showAiToolsStatus('error', `❌ 网络错误: ${error.message}`);
    }
}

// Restructure full article with AI (language + formatting)
async function restructureAIContent() {
    const title = document.getElementById('title').value.trim();

    // Send raw HTML so image/link tags can be preserved by the AI
    let content;
    if (window.quill) {
        content = window.quill.root.innerHTML;
    } else {
        content = document.getElementById('content').value.trim();
    }

    if (!title) {
        showAiToolsStatus('error', '❌ 请先输入文章标题');
        return;
    }

    if (!content || content.replace(/<[^>]*>/g, '').trim().length < 100) {
        showAiToolsStatus('error', '❌ 文章内容太短，请至少写100字后再使用重组');
        return;
    }

    // Get post ID from URL if editing
    const pathParts = window.location.pathname.split('/');
    let postId = pathParts[pathParts.length - 1];
    if (isNaN(parseInt(postId))) {
        postId = null;
    }

    showAiToolsStatus('loading', '🤖 AI正在重组全文语言与格式...');

    const csrfToken = document.querySelector('meta[name="csrf_token"]').content;

    try {
        const response = await fetch('/admin/ai/restructure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                post_id: postId,
                title: title,
                content: content
            })
        });

        const data = await response.json();

        if (data.success) {
            const restructured = data.content;
            const body = document.getElementById('aiRestructureResultBody');
            if (body) {
                body.innerHTML = restructured;
            }
            setAiResultCardVisibility('aiRestructureResultCard', true);

            const applyButton = document.getElementById('applyRestructure');
            if (applyButton) {
                applyButton.textContent = '替换全文';
                applyButton.onclick = async () => {
                    if (!window.quill) {
                        showAiToolsStatus('error', '❌ 编辑器未初始化');
                        return;
                    }
                    // Second click after applying = undo
                    if (applyButton.dataset.applied === '1') {
                        if (window.__restructureBackup != null) {
                            replaceEditorContent(window.__restructureBackup);
                            window.__restructureBackup = null;
                        }
                        applyButton.dataset.applied = '';
                        applyButton.textContent = '替换全文';
                        showAiToolsStatus('success', '已恢复替换前的内容。');
                        return;
                    }
                    const confirmFn = window.showAppConfirm || ((msg) => Promise.resolve(window.confirm(msg)));
                    const ok = await confirmFn('将用 AI 重组后的版本替换全文，替换后可再点一次按钮恢复原内容。继续吗？');
                    if (!ok) return;
                    window.__restructureBackup = window.quill.root.innerHTML;
                    replaceEditorContent(restructured);
                    applyButton.dataset.applied = '1';
                    applyButton.textContent = '撤销替换';
                    showAiToolsStatus('success', '已用 AI 重组版本替换全文，可再次点击按钮撤销。');
                    showEditorToast('全文已替换为 AI 重组版本');
                };
            }
            openAiAssistPanel();
            showAiToolsStatus('success', `✅ 重组完成，预览无误后点击"替换全文" (${data.tokens_used} tokens, ${data.model})`);
        } else {
            showAiToolsStatus('error', `❌ ${data.error || '生成失败'}`);
        }
    } catch (error) {
        showAiToolsStatus('error', `❌ 网络错误: ${error.message}`);
    }
}

function replaceEditorContent(html) {
    if (!window.quill) return;
    const textarea = document.getElementById('content');
    window.quill.root.innerHTML = html;
    if (textarea) {
        textarea.value = window.quill.root.innerHTML;
    }
    window.dispatchEvent(new CustomEvent('editor:content-change', {
        detail: { html: window.quill.root.innerHTML, text: window.quill.getText().trim() }
    }));
}
