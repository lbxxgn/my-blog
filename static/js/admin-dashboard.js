// 管理后台仪表盘页面脚本（由模板内联 JS 外置而来）
let selectedPosts = new Set();

function notifyDashboard(message, type = 'success') {
    if (window.showAppToast) {
        window.showAppToast(message, type);
        return;
    }
    console[type === 'error' ? 'error' : 'log'](message);
}

function reloadAfterToast(delay = 650) {
    setTimeout(() => window.location.reload(), delay);
}

function getSelectedPostRows() {
    return Array.from(selectedPosts)
        .map(postId => document.querySelector(`tr[data-post-id="${postId}"]`))
        .filter(Boolean);
}

function updateRowCategory(row, categoryName) {
    const statusSpan = row?.querySelector('.status');
    if (!statusSpan) return;

    statusSpan.setAttribute('data-category', categoryName || '未分类');
}

function updateRowStatus(row, isPublished) {
    const cell = row?.children?.[2];
    if (!cell) return;

    const statusSpan = cell.querySelector('.status');
    const typeLabel = statusSpan?.getAttribute('data-type') || '文章';
    const categoryLabel = statusSpan?.getAttribute('data-category') || '未分类';

    cell.innerHTML = isPublished
        ? `<span class="status published" data-type="${typeLabel}" data-category="${categoryLabel}">已发布</span>`
        : `<span class="status draft" data-type="${typeLabel}" data-category="${categoryLabel}">草稿</span>`;
}

function removeSelectedRows() {
    getSelectedPostRows().forEach(row => row.remove());
    clearSelection();
}

document.addEventListener('DOMContentLoaded', function() {
    // Batch category form
    document.getElementById('batchCategoryForm').addEventListener('submit', function(e) {
        e.preventDefault();

        const categoryId = document.getElementById('batchCategorySelect').value;
        const postIds = Array.from(selectedPosts);

        if (postIds.length === 0) {
            notifyDashboard('请先选择文章', 'error');
            return;
        }

        // Send to backend
        const csrfToken = document.querySelector('meta[name="csrf_token"]').getAttribute('content');
        fetch('/admin/batch-update-category', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                post_ids: postIds,
                category_id: categoryId === '' ? null : parseInt(categoryId),
                csrf_token: csrfToken
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                notifyDashboard(data.message);
                const selectedOption = document.getElementById('batchCategorySelect').selectedOptions[0];
                const categoryName = categoryId === '' ? '' : (selectedOption?.textContent || '');
                getSelectedPostRows().forEach(row => updateRowCategory(row, categoryName));
                closeBatchCategoryModal();
                clearSelection();
            } else {
                notifyDashboard('操作失败：' + data.message, 'error');
            }
        })
        .catch(error => {
            notifyDashboard('操作失败：' + error, 'error');
        });
    });
});

function filterByType() {
    const type = document.getElementById('typeFilter').value;
    const url = new URL(window.location.href);
    if (type) {
        url.searchParams.set('type', type);
    } else {
        url.searchParams.delete('type');
    }
    url.searchParams.set('page', '1');
    window.location.href = url.toString();
}

function filterByCategory() {
    const categoryFilter = document.getElementById('categoryFilter');
    const selectedCategory = categoryFilter.value;

    // Build URL with parameters
    const url = new URL(window.location);
    if (selectedCategory === '') {
        url.searchParams.delete('category_id');
    } else {
        url.searchParams.set('category_id', selectedCategory);
    }
    url.searchParams.set('page', '1'); // Reset to first page when changing category
    url.searchParams.set('per_page', document.getElementById('perPageSelect').value);

    window.location = url.toString();
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('.post-checkbox');

    checkboxes.forEach(checkbox => {
        const postId = parseInt(checkbox.value);
        const row = checkbox.closest('tr');

        // Only toggle visible rows
        if (row.style.display !== 'none') {
            checkbox.checked = selectAllCheckbox.checked;
            if (checkbox.checked) {
                selectedPosts.add(postId);
            } else {
                selectedPosts.delete(postId);
            }
        }
    });

    updateBatchActions();
}

function changePerPage() {
    const perPage = document.getElementById('perPageSelect').value;
    const categoryFilter = document.getElementById('categoryFilter');
    const url = new URL(window.location);
    url.searchParams.set('per_page', perPage);
    url.searchParams.set('page', '1'); // Reset to first page

    // Keep category filter
    const selectedCategory = categoryFilter.value;
    if (selectedCategory !== '') {
        url.searchParams.set('category_id', selectedCategory);
    }

    window.location = url.toString();
}

function updateBatchActions() {
    const checkboxes = document.querySelectorAll('.post-checkbox:checked');
    selectedPosts.clear();

    checkboxes.forEach(checkbox => {
        selectedPosts.add(parseInt(checkbox.value));
    });

    const batchActionsBar = document.getElementById('batchActionsBar');
    const selectedCount = document.getElementById('selectedCount');

    if (selectedPosts.size > 0) {
        batchActionsBar.style.display = 'flex';
        selectedCount.textContent = selectedPosts.size;
    } else {
        batchActionsBar.style.display = 'none';
    }
}

function clearSelection() {
    const checkboxes = document.querySelectorAll('.post-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });

    document.getElementById('selectAll').checked = false;
    selectedPosts.clear();
    updateBatchActions();
}

function showBatchCategoryModal() {
    if (selectedPosts.size === 0) {
        notifyDashboard('请先选择文章', 'error');
        return;
    }

    document.getElementById('batchCategoryModal').style.display = 'flex';
}

function closeBatchCategoryModal() {
    document.getElementById('batchCategoryModal').style.display = 'none';
}

function showBatchDeleteModal() {
    if (selectedPosts.size === 0) {
        notifyDashboard('请先选择文章', 'error');
        return;
    }

    document.getElementById('deleteCount').textContent = selectedPosts.size;
    document.getElementById('batchDeleteModal').style.display = 'flex';
}

function closeBatchDeleteModal() {
    document.getElementById('batchDeleteModal').style.display = 'none';
}

function confirmBatchDelete() {
    const postIds = Array.from(selectedPosts);

    if (postIds.length === 0) {
        notifyDashboard('请先选择文章', 'error');
        return;
    }

    // Send to backend
    const csrfToken = document.querySelector('meta[name="csrf_token"]').getAttribute('content');
    fetch('/admin/batch-delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            post_ids: postIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeBatchDeleteModal();
            notifyDashboard(data.message);
            removeSelectedRows();
        } else {
            notifyDashboard('操作失败：' + data.message, 'error');
        }
    })
    .catch(error => {
        notifyDashboard('操作失败：' + error, 'error');
    });
}

// Batch publish/unpublish functions
async function showBatchPublishModal() {
    if (selectedPosts.size === 0) {
        notifyDashboard('请先选择文章', 'error');
        return;
    }

    const confirmed = await window.showAppConfirm(`确定要发布 ${selectedPosts.size} 篇文章吗？`);
    if (confirmed) {
        performBatchPublish(true);
    }
}

async function showBatchUnpublishModal() {
    if (selectedPosts.size === 0) {
        notifyDashboard('请先选择文章', 'error');
        return;
    }

    const confirmed = await window.showAppConfirm(`确定要取消发布 ${selectedPosts.size} 篇文章吗？`);
    if (confirmed) {
        performBatchPublish(false);
    }
}

function performBatchPublish(publish) {
    const postIds = Array.from(selectedPosts);

    const csrfToken = document.querySelector('meta[name="csrf_token"]').getAttribute('content');
    fetch('/admin/batch-publish', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            post_ids: postIds,
            publish: publish
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            notifyDashboard(data.message);
            getSelectedPostRows().forEach(row => updateRowStatus(row, publish));
            clearSelection();
        } else {
            notifyDashboard('操作失败：' + data.message, 'error');
        }
    })
    .catch(error => {
        notifyDashboard('操作失败：' + error, 'error');
    });
}

// Batch tags functions
function showBatchTagsModal() {
    if (selectedPosts.size === 0) {
        notifyDashboard('请先选择文章', 'error');
        return;
    }

    document.getElementById('batchTagsModal').style.display = 'flex';
}

function closeBatchTagsModal() {
    document.getElementById('batchTagsModal').style.display = 'none';
}

// Batch access functions
function showBatchAccessModal() {
    if (selectedPosts.size === 0) {
        notifyDashboard('请先选择文章', 'error');
        return;
    }

    document.getElementById('batchAccessModal').style.display = 'flex';
}

function closeBatchAccessModal() {
    document.getElementById('batchAccessModal').style.display = 'none';
}

function togglePasswordField() {
    const accessLevel = document.getElementById('batchAccessLevel').value;
    const passwordField = document.getElementById('passwordFieldGroup');

    if (accessLevel === 'password') {
        passwordField.style.display = 'block';
    } else {
        passwordField.style.display = 'none';
    }
}

// Add event listeners for new forms
document.addEventListener('DOMContentLoaded', function() {
    // Batch tags form
    const batchTagsForm = document.getElementById('batchTagsForm');
    if (batchTagsForm) {
        batchTagsForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const tagsInput = document.getElementById('batchTagsInput').value;
            const tags = tagsInput.split(',').map(t => t.trim()).filter(t => t);
            const postIds = Array.from(selectedPosts);

            if (postIds.length === 0) {
                notifyDashboard('请先选择文章', 'error');
                return;
            }

            if (tags.length === 0) {
                notifyDashboard('请输入至少一个标签', 'error');
                return;
            }

            const csrfToken = document.querySelector('meta[name="csrf_token"]').getAttribute('content');
            fetch('/admin/batch-add-tags', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    post_ids: postIds,
                    tags: tags
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    notifyDashboard(data.message);
                    closeBatchTagsModal();
                    document.getElementById('batchTagsInput').value = '';
                    clearSelection();
                } else {
                    notifyDashboard('操作失败：' + data.message, 'error');
                }
            })
            .catch(error => {
                notifyDashboard('操作失败：' + error, 'error');
            });
        });
    }

    // Batch access form
    const batchAccessForm = document.getElementById('batchAccessForm');
    if (batchAccessForm) {
        batchAccessForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const accessLevel = document.getElementById('batchAccessLevel').value;
            const accessPassword = document.getElementById('batchAccessPassword').value;
            const postIds = Array.from(selectedPosts);

            if (postIds.length === 0) {
                notifyDashboard('请先选择文章', 'error');
                return;
            }

            if (accessLevel === 'password' && !accessPassword) {
                notifyDashboard('请输入访问密码', 'error');
                return;
            }

            const csrfToken = document.querySelector('meta[name="csrf_token"]').getAttribute('content');
            fetch('/admin/batch-update-access', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    post_ids: postIds,
                    access_level: accessLevel,
                    access_password: accessPassword
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    notifyDashboard(data.message);
                    closeBatchAccessModal();
                    document.getElementById('batchAccessPassword').value = '';
                    clearSelection();
                } else {
                    notifyDashboard('操作失败：' + data.message, 'error');
                }
            })
            .catch(error => {
                notifyDashboard('操作失败：' + error, 'error');
            });
        });
    }
});
