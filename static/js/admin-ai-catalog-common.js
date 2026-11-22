/**
 * AI 供应商管理页的公共工具（catalog 列表页 / 供应商详情页共用）
 *
 * 原先是两个模板里各复制一份 esc/api/closeDialog/showMessage，
 * 抽出来顺带把 fetch 换成 AppHttp。
 */
(function (global) {
    'use strict';

    var PROVIDERS_URL = '/admin/ai/catalog/providers';
    var MODELS_URL = '/admin/ai/catalog/models';

    // 模板把数据放在 <script type="application/json"> 里，避免内联可执行脚本
    function readJSON(id) {
        var el = document.getElementById(id);
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (error) {
            console.error('Failed to parse ' + id + ':', error);
            return null;
        }
    }

    function esc(value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function showMessage(text, type) {
        var box = document.getElementById('catalogMessage');
        if (!box) return;
        box.textContent = text;
        box.className = 'catalog-message ' + (type || 'success');
        box.hidden = false;
    }

    async function api(url, method, payload) {
        var options = {
            method: method,
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': global.AppHttp.getCsrfToken()
            },
            acceptErrors: true,
            silent: true
        };
        if (payload !== undefined) {
            options.body = JSON.stringify(payload);
        }

        var response = await global.AppHttp.request(url, options);
        var data = {};
        try {
            data = await response.json();
        } catch (error) {
            data = { success: false, error: '服务器返回异常 (' + response.status + ')' };
        }
        if (!response.ok || !data.success) {
            throw new Error(data.error || '请求失败 (' + response.status + ')');
        }
        return data;
    }

    function closeDialog(id) {
        var dialog = document.getElementById(id);
        if (dialog && dialog.open) dialog.close();
    }

    function clearDialogError(id) {
        var box = document.getElementById(id);
        if (!box) return;
        box.textContent = '';
        box.hidden = true;
    }

    function showDialogError(id, message) {
        var box = document.getElementById(id);
        if (!box) return;
        box.textContent = message;
        box.hidden = false;
        box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // 点击遮罩关闭 dialog（两个页面共用）
    function bindDialogBackdrop() {
        document.querySelectorAll('dialog').forEach(function (dialog) {
            dialog.addEventListener('click', function (event) {
                if (event.target === dialog) dialog.close();
            });
        });
    }

    global.AiCatalog = {
        PROVIDERS_URL: PROVIDERS_URL,
        MODELS_URL: MODELS_URL,
        readJSON: readJSON,
        esc: esc,
        api: api,
        showMessage: showMessage,
        closeDialog: closeDialog,
        clearDialogError: clearDialogError,
        showDialogError: showDialogError,
        bindDialogBackdrop: bindDialogBackdrop
    };
})(window);
