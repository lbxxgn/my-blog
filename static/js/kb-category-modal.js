/**
 * 知识库「新建目录」弹窗（原 templates/knowledge/index.html 内联脚本）
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var modal = document.getElementById('kb-cat-modal');
        var form = document.getElementById('kb-cat-form');
        var parentInput = document.getElementById('kb-cat-parent');
        var titleEl = document.getElementById('kb-cat-modal-title');
        if (!modal || !form || !parentInput || !titleEl) return;

        // 后端地址由模板写进 data-action-url，脚本不再依赖 Jinja
        var action = form.getAttribute('data-action-url') || form.getAttribute('action') || '';

        function openModal(parentId, parentName) {
            parentInput.value = parentId || '';
            titleEl.textContent = parentId ? '在「' + (parentName || '') + '」下新建目录' : '新建顶层目录';
            modal.style.display = 'flex';
            setTimeout(function () {
                var input = document.getElementById('kb-cat-name');
                if (input) input.focus();
            }, 50);
        }

        function closeModal() {
            modal.style.display = 'none';
            form.reset();
            parentInput.value = '';
        }

        document.querySelectorAll('.kb-add-root').forEach(function (btn) {
            btn.addEventListener('click', function () { openModal('', ''); });
        });

        document.addEventListener('click', function (e) {
            var btn = e.target.closest('.kb-add-sub');
            if (!btn) return;
            var parentId = btn.getAttribute('data-parent-id') || '';
            var parentName = btn.getAttribute('data-parent-name') || '';
            if (!parentName && parentId) {
                var item = btn.closest('.kb-tree-item');
                var link = item ? item.querySelector('a') : null;
                parentName = link ? link.textContent.trim() : '';
            }
            openModal(parentId, parentName);
        });

        var cancelBtn = document.getElementById('kb-cat-cancel');
        if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var fd = new FormData(form);
            AppHttp.json(action, {
                method: 'POST',
                body: fd,
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                silent: true
            }).then(function (data) {
                if (data && data.success) {
                    closeModal();
                    location.reload();
                } else {
                    alert((data && data.error) || '创建失败');
                }
            }).catch(function (error) {
                alert(AppHttp.describe(error));
            });
        });
    });
})();
