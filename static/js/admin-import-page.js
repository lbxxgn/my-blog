/**
 * 导入页文件选择反馈（原 templates/admin/import.html 内联脚本）
 */
(function () {
    'use strict';

    function init() {
        document.querySelectorAll('input[type="file"]').forEach(function (input) {
            input.addEventListener('change', function (e) {
                var label = input.nextElementSibling;
                if (!label) return;
                var file = e.target.files && e.target.files[0];
                if (!file) return;
                label.textContent = '已选择: ' + file.name;
                label.classList.add('is-selected');
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
