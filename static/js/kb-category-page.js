/**
 * 分类页的批量移动（原 templates/knowledge/category.html 内联脚本）
 *
 * 目标目录下拉的 id 为 kbMoveTarget，移动按钮通过 data-url 提供后端地址。
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var selectAll = document.getElementById('kbSelectAllDocs');
        if (selectAll) {
            selectAll.addEventListener('change', function () {
                document.querySelectorAll('.kb-doc-select').forEach(function (cb) {
                    cb.checked = selectAll.checked;
                });
            });
        }

        var moveBtn = document.getElementById('kbBatchMove');
        if (!moveBtn) return;

        moveBtn.addEventListener('click', function () {
            var target = document.getElementById('kbMoveTarget').value;
            var ids = Array.from(document.querySelectorAll('.kb-doc-select:checked'))
                .map(function (cb) { return cb.value; });

            if (!target) return alert('请选择目标目录');
            if (!ids.length) return alert('请选择要移动的文档');

            var fd = new FormData();
            fd.append('category_id', target);
            fd.append('doc_ids', ids.join(','));
            fd.append('csrf_token', AppHttp.getCsrfToken());

            AppHttp.json(moveBtn.getAttribute('data-url'), {
                method: 'POST',
                body: fd,
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                silent: true
            }).then(function (data) {
                if (!data || !data.success) throw new Error((data && data.error) || '移动失败');
                location.reload();
            }).catch(function (error) {
                alert(error.message || AppHttp.describe(error));
            });
        });
    });
})();
