// 时间线页面脚本（由模板内联 JS 外置而来）
document.addEventListener('DOMContentLoaded', function() {
    console.log('Timeline page loaded');
    console.log('Filter buttons:', document.querySelectorAll('.filter-btn').length);
    console.log('Timeline items:', document.querySelectorAll('.timeline-item').length);
    // 直接从 meta 标签读取 CSRF token，不依赖 base.html 的脚本
    const csrfToken = document.querySelector('meta[name="csrf_token"]')?.content || '';

    // 兜底：如果 base.html 的 showAppConfirm 还没加载，用原生 confirm 代替
    if (!window.showAppConfirm) {
        window.showAppConfirm = function(message) {
            return Promise.resolve(confirm(message));
        };
    }

    function notifyTimeline(message, type = 'success') {
        if (window.showAppToast) {
            window.showAppToast(message, type);
            return;
        }
        console[type === 'error' ? 'error' : 'log'](message);
    }

    function redirectToLogin() {
        notifyTimeline('登录已过期，请重新登录后重试', 'error');
        setTimeout(() => {
            window.location.href = '/login';
        }, 600);
    }

    function getTimelineStatusLabel(status) {
        const labels = {
            idea: '想法',
            incubating: '孵化中',
            draft: '草稿',
            published: '已发布'
        };
        return labels[status] || status;
    }

    function updateTimelineItem(cardId, nextData) {
        const item = document.querySelector(`.edit-btn[data-id="${cardId}"]`)?.closest('.timeline-item');
        if (!item) {
            return;
        }

        item.dataset.status = nextData.status;

        const badge = item.querySelector('.badge');
        if (badge) {
            badge.className = `badge badge-${nextData.status}`;
            badge.textContent = getTimelineStatusLabel(nextData.status);
        }

        let titleEl = item.querySelector('.item-title');
        if (nextData.title) {
            if (!titleEl) {
                titleEl = document.createElement('h3');
                titleEl.className = 'item-title';
                const body = item.querySelector('.item-body');
                item.querySelector('.item-content').insertBefore(titleEl, body);
            }
            titleEl.textContent = nextData.title;
        } else if (titleEl) {
            titleEl.remove();
        }

        const body = item.querySelector('.item-body');
        if (body) {
            body.textContent = nextData.content.length > 200
                ? `${nextData.content.slice(0, 200)}...`
                : nextData.content;
        }
    }

    // ==================== 编辑卡片功能 ====================
    const modal = document.getElementById('editModal');
    const editForm = document.getElementById('editForm');
    const closeBtn = modal.querySelector('.close');
    const cancelBtn = document.getElementById('cancelEdit');

    // 打开编辑模态框
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const cardId = this.getAttribute('data-id');
            console.log('编辑卡片 ID:', cardId);

            // 获取卡片详情
            fetch(`/knowledge_base/api/cards/${cardId}`, {
                credentials: 'same-origin'  // 确保发送cookies
            })
                .then(response => {
                    // 检查是否被重定向到登录页
                    if (response.redirected || response.status === 302) {
                        throw new Error('请先登录');
                    }
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        const card = data.card;
                        document.getElementById('editCardId').value = card.id;
                        document.getElementById('editTitle').value = card.title || '';
                        document.getElementById('editContent').value = card.content || '';
                        document.getElementById('editTags').value = (card.tags || []).join(', ');
                        document.getElementById('editStatus').value = card.status || 'idea';
                        modal.style.display = 'block';
                    } else {
                        notifyTimeline('获取卡片详情失败: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (error.message === '请先登录') {
                        redirectToLogin();
                    } else {
                        notifyTimeline('获取卡片详情失败: ' + error.message, 'error');
                    }
                });
        });
    });

    // 关闭模态框
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    cancelBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // 点击模态框外部关闭
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // 保存编辑
    editForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const cardId = document.getElementById('editCardId').value;
        const data = {
            title: document.getElementById('editTitle').value,
            content: document.getElementById('editContent').value,
            tags: document.getElementById('editTags').value.split(',').map(t => t.trim()).filter(t => t),
            status: document.getElementById('editStatus').value
        };

        console.log('保存卡片:', cardId, data);

        fetch(`/knowledge_base/api/cards/${cardId}`, {
            method: 'PUT',
            credentials: 'same-origin',  // 确保发送cookies
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            // 检查是否被重定向到登录页
            if (response.redirected || response.status === 302) {
                throw new Error('请先登录');
            }
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                notifyTimeline('保存成功');
                updateTimelineItem(cardId, data ? {
                    title: document.getElementById('editTitle').value,
                    content: document.getElementById('editContent').value,
                    status: document.getElementById('editStatus').value
                } : null);
                modal.style.display = 'none';
            } else {
                notifyTimeline('保存失败: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (error.message === '请先登录') {
                redirectToLogin();
            } else {
                notifyTimeline('保存失败: ' + error.message, 'error');
            }
        });
    });

    // ==================== 转为文章功能 ====================
    document.querySelectorAll('.convert-to-post-btn').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            const cardId = this.getAttribute('data-id');
            const cardTitle = this.closest('.timeline-item').querySelector('.item-title')?.textContent || '此卡片';

            const confirmed = await window.showAppConfirm(`确定要将卡片 "${cardTitle}" 转换为文章吗？\n\n转换后卡片将被删除，内容将作为已发布的文章保存到"转载"分类下。`);
            if (confirmed) {
                console.log('转换卡片为文章 ID:', cardId);

                fetch(`/knowledge_base/api/card/${cardId}/convert-to-post`, {
                    method: 'POST',
                    credentials: 'same-origin',  // 确保发送cookies
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                })
                .then(response => {
                    // 检查是否被重定向到登录页
                    if (response.redirected || response.status === 302) {
                        throw new Error('请先登录');
                    }
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        notifyTimeline('转换成功，正在打开文章编辑页');
                        setTimeout(() => {
                            window.location.href = `/admin/edit/${data.post_id}`;
                        }, 450);
                    } else {
                        notifyTimeline('转换失败: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (error.message === '请先登录') {
                        redirectToLogin();
                    } else {
                        notifyTimeline('转换失败: ' + error.message, 'error');
                    }
                });
            }
        });
    });

    // ==================== 删除卡片功能 ====================
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();
            const cardId = this.getAttribute('data-id');
            const cardTitle = this.closest('.timeline-item').querySelector('.item-title')?.textContent || '此卡片';

            const confirmed = await window.showAppConfirm(`确定要删除卡片 "${cardTitle}" 吗？\n\n此操作不可恢复！`, {
                destructive: true,
                confirmText: '删除'
            });
            if (confirmed) {
                console.log('删除卡片 ID:', cardId);
                const timelineItem = this.closest('.timeline-item');

                fetch(`/knowledge_base/api/cards/${cardId}`, {
                    method: 'DELETE',
                    credentials: 'same-origin',  // 确保发送cookies
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                })
                .then(response => {
                    // 检查是否被重定向到登录页
                    if (response.redirected || response.status === 302) {
                        throw new Error('请先登录');
                    }
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        notifyTimeline('删除成功');
                        if (timelineItem) {
                            timelineItem.remove();
                        }
                    } else {
                        notifyTimeline('删除失败: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (error.message === '请先登录') {
                        redirectToLogin();
                    } else {
                        notifyTimeline('删除失败: ' + error.message, 'error');
                    }
                });
            }
        });
    });

    // ==================== 筛选按钮功能 ====================
    const typeBtns = document.querySelectorAll('.filter-type-btn');
    const statusBtns = document.querySelectorAll('.filter-status-btn');
    const timelineItems = document.querySelectorAll('.timeline-item');

    let currentTypeFilter = 'all';
    let currentStatusFilter = 'all';

    // 类型筛选按钮事件
    typeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // 移除所有类型按钮的 active 类
            typeBtns.forEach(b => b.classList.remove('active'));
            // 添加当前按钮的 active 类
            this.classList.add('active');

            currentTypeFilter = this.getAttribute('data-type');
            console.log('Type filter:', currentTypeFilter);

            applyFilters();
        });
    });

    // 状态筛选按钮事件
    statusBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // 移除所有状态按钮的 active 类
            statusBtns.forEach(b => b.classList.remove('active'));
            // 添加当前按钮的 active 类
            this.classList.add('active');

            currentStatusFilter = this.getAttribute('data-status');
            console.log('Status filter:', currentStatusFilter);

            applyFilters();
        });
    });

    // 应用筛选
    function applyFilters() {
        let visibleCount = 0;

        timelineItems.forEach(item => {
            const type = item.getAttribute('data-type');
            const status = item.getAttribute('data-status');

            // 类型筛选
            const typeMatch = currentTypeFilter === 'all' || type === currentTypeFilter;

            // 状态筛选
            const statusMatch = currentStatusFilter === 'all' || status === currentStatusFilter;

            // 同时满足类型和状态筛选
            if (typeMatch && statusMatch) {
                item.classList.remove('hidden');
                visibleCount++;
            } else {
                item.classList.add('hidden');
            }
        });

        console.log('Visible items:', visibleCount,
                   '(Type:', currentTypeFilter, ', Status:', currentStatusFilter + ')');
    }

    // 时区转换 - 将 UTC 时间转换为 UTC+8
    function convertToChinaTime(utcTimeString) {
        try {
            console.log('Converting time:', utcTimeString);

            // 解析 SQLite datetime 格式：YYYY-MM-DD HH:MM:SS
            const parts = utcTimeString.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);

            if (parts) {
                const [, year, month, day, hour, minute, second] = parts;
                // 创建日期对象（注意月份要减1）
                const date = new Date(year, month - 1, day, hour, minute, second);

                // 转换为 UTC+8（如果已经是本地时间，则不需要转换）
                // SQLite 存储的是 UTC，需要转换为本地时间
                const chinaTime = new Date(date.getTime() + (8 * 60 * 60 * 1000));

                const formatted = chinaTime.toLocaleString('zh-CN', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: false
                });

                console.log('Converted:', utcTimeString, '->', formatted);
                return formatted;
            }

            return utcTimeString;
        } catch (e) {
            console.error('Time conversion error:', e);
            return utcTimeString;
        }
    }

    // 更新所有时间显示
    document.querySelectorAll('.item-date').forEach(el => {
        const originalTime = el.textContent.trim();
        const convertedTime = convertToChinaTime(originalTime);
        el.textContent = convertedTime;
        el.title = '原始时间: ' + originalTime; // 鼠标悬停显示原始时间
        console.log('Time updated:', originalTime, '->', convertedTime);
    });

    console.log('Timeline initialization complete');
});
