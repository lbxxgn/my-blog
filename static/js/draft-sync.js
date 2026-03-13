/**
 * 草稿同步管理器 - 多设备自动保存和冲突解决
 */
class DraftSyncManager {
    constructor() {
        this.autoSaveInterval = 30000; // 30秒
        this.autoSaveTimer = null;
        this.currentDraftId = null;
        this.lastSyncTime = null;
        this.deviceInfo = this.getDeviceInfo();
        this.postId = null;
    }

    init(postId = null) {
        this.postId = postId;
        this.loadLastSyncTime();
        this.observeContentChanges();
        this.checkForExistingDrafts();
    }

    // 监听内容变化
    observeContentChanges() {
        const titleInput = document.getElementById('title');
        const contentTextarea = document.getElementById('content');

        const debouncedSave = this.debounce(() => {
            this.saveDraft();
        }, this.autoSaveInterval);

        titleInput?.addEventListener('input', debouncedSave);
        contentTextarea?.addEventListener('input', debouncedSave);
    }

    // 保存草稿到服务器
    async saveDraft() {
        const saveStatus = document.getElementById('saveStatus');
        if (saveStatus) {
            saveStatus.textContent = '正在保存...';
            saveStatus.className = 'save-status saving';
        }

        try {
            const formData = this.getFormData();
            const response = await fetch('/api/drafts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCsrfToken()
                },
                body: JSON.stringify({
                    post_id: this.postId,
                    device_info: this.deviceInfo,
                    ...formData
                })
            });

            const result = await response.json();

            if (result.success) {
                this.currentDraftId = result.draft_id;
                this.lastSyncTime = result.updated_at;

                if (result.status === 'conflict_detected' && result.other_drafts?.length > 0) {
                    this.showConflictDialog(result.other_drafts);
                } else {
                    if (saveStatus) {
                        saveStatus.textContent = `已保存 ${this.getTimeAgo(result.updated_at)}`;
                        saveStatus.className = 'save-status saved';
                    }
                }

                this.saveToLocalStorage(formData);
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('草稿保存失败:', error);
            if (saveStatus) {
                saveStatus.textContent = '保存失败，已保存到本地';
                saveStatus.className = 'save-status error';
            }
            this.saveToLocalStorage(this.getFormData());
        }
    }

    // 检测现有草稿
    async checkForExistingDrafts() {
        if (!this.postId) return;

        try {
            const response = await fetch(`/api/drafts?post_id=${this.postId}`);
            const result = await response.json();

            if (result.success && result.drafts?.length > 0) {
                const localDraft = this.getFromLocalStorage();
                const serverDrafts = result.drafts;

                if (serverDrafts.length > 0 || localDraft) {
                    this.showDraftRecoveryDialog(serverDrafts, localDraft);
                }
            }
        } catch (error) {
            console.error('检测草稿失败:', error);
        }
    }

    // 显示草稿恢复对话框
    showDraftRecoveryDialog(serverDrafts, localDraft) {
        const modal = document.createElement('div');
        modal.className = 'draft-recovery-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>💾 检测到未保存的草稿</h2>
                </div>
                <div class="modal-body">
                    ${this.renderDraftOptions(serverDrafts, localDraft)}
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" id="discardAllDrafts">
                        放弃所有草稿
                    </button>
                </div>
            </div>
        `;

        // 绑定事件
        modal.querySelector('#discardAllDrafts').onclick = () => {
            localStorage.removeItem(`draft_${this.postId || 'new'}`);
            modal.remove();
        };

        document.body.appendChild(modal);
    }

    renderDraftOptions(serverDrafts, localDraft) {
        let html = '';

        if (serverDrafts?.length > 0) {
            serverDrafts.forEach(draft => {
                html += `
                    <div class="draft-option" data-draft-id="${draft.id}">
                        <h3>📱 ${draft.device_info} - ${this.getTimeAgo(draft.updated_at)}</h3>
                        <div class="draft-preview">${draft.title}</div>
                        <button class="btn btn-primary recover-draft">恢复此草稿</button>
                    </div>
                `;
            });
        }

        if (localDraft) {
            html += `
                <div class="draft-option local-draft">
                    <h3>💾 本地草稿</h3>
                    <div class="draft-preview">${localDraft.title}</div>
                    <button class="btn btn-primary recover-local">恢复本地草稿</button>
                </div>
            `;
        }

        return html;
    }

    // 显示草稿冲突对话框
    showConflictDialog(otherDrafts) {
        const modal = document.createElement('div');
        modal.className = 'draft-conflict-modal';

        const currentData = this.getFormData();

        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>⚠️ 检测到其他设备的草稿</h2>
                </div>
                <div class="modal-body">
                    <div class="conflict-version">
                        <h3>📱 ${otherDrafts[0].device_info} - ${this.getTimeAgo(otherDrafts[0].updated_at)}</h3>
                        <div class="draft-preview">${otherDrafts[0].title}</div>
                        <button class="btn btn-primary" data-action="keep-other">使用此版本</button>
                    </div>
                    <hr>
                    <div class="conflict-version current">
                        <h3>💻 ${this.deviceInfo} - 刚刚</h3>
                        <div class="draft-preview">${currentData.title}</div>
                        <button class="btn btn-primary" data-action="keep-current">保留当前编辑</button>
                    </div>
                    <hr>
                    <button class="btn btn-secondary" data-action="merge">🔄 合并两个版本</button>
                </div>
            </div>
        `;

        modal.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', async () => {
                await this.resolveConflict(otherDrafts[0].id, btn.dataset.action);
                modal.remove();
            });
        });

        document.body.appendChild(modal);
    }

    // 解决冲突
    async resolveConflict(otherDraftId, action) {
        try {
            const response = await fetch('/api/drafts/resolve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCsrfToken()
                },
                body: JSON.stringify({
                    conflict_draft_id: otherDraftId,
                    current_draft_id: this.currentDraftId,
                    action: action
                })
            });

            const result = await response.json();
            if (result.success) {
                this.showNotification(result.message, 'success');
                if (action === 'keep_other') {
                    location.reload();
                }
            }
        } catch (error) {
            this.showNotification('解决冲突失败: ' + error.message, 'error');
        }
    }

    // 获取设备信息
    getDeviceInfo() {
        const ua = navigator.userAgent;
        let browser = 'Unknown Browser';
        let os = 'Unknown OS';

        if (ua.includes('Chrome')) browser = 'Chrome';
        else if (ua.includes('Firefox')) browser = 'Firefox';
        else if (ua.includes('Safari')) browser = 'Safari';

        if (ua.includes('Windows')) os = 'Windows';
        else if (ua.includes('Mac')) os = 'macOS';
        else if (ua.includes('Linux')) os = 'Linux';
        else if (ua.includes('Android')) os = 'Android';
        else if (ua.includes('iOS')) os = 'iOS';

        return `${browser} on ${os}`;
    }

    // 工具方法
    debounce(func, wait) {
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

    getTimeAgo(timestamp) {
        const now = new Date();
        const past = new Date(timestamp);
        const diff = Math.floor((now - past) / 1000);

        if (diff < 60) return '刚刚';
        if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
        return `${Math.floor(diff / 86400)}天前`;
    }

    getFormData() {
        return {
            title: document.getElementById('title')?.value || '',
            content: document.getElementById('content')?.value || '',
            category_id: document.getElementById('category')?.value || null,
            tags: this.getTags()
        };
    }

    getTags() {
        const tagInput = document.getElementById('tags');
        if (tagInput) {
            return tagInput.value.split(',').map(t => t.trim()).filter(t => t);
        }
        return [];
    }

    getCsrfToken() {
        return document.querySelector('meta[name="csrf_token"]')?.getAttribute('content');
    }

    saveToLocalStorage(data) {
        localStorage.setItem(`draft_${this.postId || 'new'}`, JSON.stringify({
            ...data,
            saved_at: new Date().toISOString()
        }));
    }

    getFromLocalStorage() {
        const key = `draft_${this.postId || 'new'}`;
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    }

    loadLastSyncTime() {
        const key = `last_sync_${this.postId || 'new'}`;
        const time = localStorage.getItem(key);
        if (time) {
            this.lastSyncTime = time;
        }
    }

    showNotification(message, type = 'info') {
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    const pageType = document.body.dataset.page;
    if (pageType === 'editor' || pageType === 'admin') {
        const postIdElement = document.querySelector('[data-post-id]');
        const postId = postIdElement?.dataset.postId ?
                       parseInt(postIdElement.dataset.postId) : null;

        window.draftSync = new DraftSyncManager();
        window.draftSync.init(postId);
    }
});
