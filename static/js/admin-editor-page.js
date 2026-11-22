/**
 * 编辑器里「新建分类」（原 templates/admin/editor.html 内联脚本）
 *
 * 后端地址从 #newCategoryInline 的 data-url 读取。
 */
(function () {
    'use strict';

    function init() {
        var btn = document.getElementById('newCategoryInline');
        var select = document.getElementById('category_id');
        if (!btn || !select) return;

        var url = btn.getAttribute('data-url') || '';

        btn.addEventListener('click', function () {
            var name = window.prompt('新分类名称');
            if (!name || !name.trim()) return;

            var fd = new FormData();
            fd.append('name', name.trim());
            fd.append('csrf_token', AppHttp.getCsrfToken());

            AppHttp.json(url, {
                method: 'POST',
                body: fd,
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                silent: true
            }).then(function (data) {
                if (!data || !data.success) throw new Error((data && data.error) || '创建失败');
                var option = document.createElement('option');
                option.value = data.id;
                option.textContent = data.name;
                select.appendChild(option);
                select.value = String(data.id);
                select.dispatchEvent(new Event('change'));
            }).catch(function (e) {
                alert(e.message || AppHttp.describe(e));
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
