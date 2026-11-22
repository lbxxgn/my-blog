/**
 * AI 供应商列表页（原 templates/admin/ai_catalog.html 内联脚本）
 *
 * 供应商数据通过 <script type="application/json" id="ai-catalog-data"> 传入，
 * 操作按钮统一用 data-action + 事件委托，模板里不再有 onclick。
 */
(function () {
    'use strict';

    var catalog = [];

    var esc = function () { return ''; };
    var api = null;
    var showMessage = null;
    var closeDialog = null;
    var clearDialogError = null;
    var showDialogError = null;

    function bindCommon() {
        esc = AiCatalog.esc;
        api = AiCatalog.api;
        showMessage = AiCatalog.showMessage;
        closeDialog = AiCatalog.closeDialog;
        clearDialogError = AiCatalog.clearDialogError;
        showDialogError = AiCatalog.showDialogError;
    }

    function renderProviders() {
        var tbody = document.getElementById('providerRows');
        if (!tbody) return;

        if (!catalog.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-row">暂无供应商，请先新增</td></tr>';
            return;
        }

        tbody.innerHTML = catalog.map(function (provider) {
            var modelCount = (provider.model_details || []).length;
            var detailUrl = AiCatalog.PROVIDERS_URL + '/' + provider.provider_pk;
            return '' +
                '<tr>' +
                    '<td>' +
                        '<div class="name-cell">' +
                            '<a href="' + esc(detailUrl) + '" class="catalog-name-link">' + esc(provider.name) + '</a>' +
                            '<span class="model-id">' + esc(provider.slug) + '</span>' +
                        '</div>' +
                    '</td>' +
                    '<td>' + esc(provider.driver) + '</td>' +
                    '<td><span class="model-id">' + esc(provider.base_url || '—') + '</span></td>' +
                    '<td>' + esc(provider.currency) + '</td>' +
                    '<td>' + modelCount + '</td>' +
                    '<td>' +
                        '<div class="badge-stack">' +
                            '<span class="badge ' + (provider.enabled ? 'badge-on' : 'badge-off') + '">' +
                                (provider.enabled ? '启用' : '停用') +
                            '</span>' +
                            (provider.is_builtin ? '<span class="badge badge-builtin">内置</span>' : '') +
                            '<span class="badge">' + esc(provider.usage_count) + ' 用户</span>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div class="actions">' +
                            '<a href="' + esc(detailUrl) + '" class="btn">进入配置</a>' +
                            (provider.is_builtin ? '' :
                                '<button type="button" class="btn btn-danger" data-action="remove-provider" ' +
                                'data-provider-pk="' + esc(provider.provider_pk) + '">删除</button>') +
                        '</div>' +
                    '</td>' +
                '</tr>';
        }).join('');
    }

    function openProviderDialog() {
        var form = document.getElementById('providerForm');
        if (!form) return;
        form.reset();
        clearDialogError('providerDialogError');

        document.getElementById('providerCurrency').value = 'CNY';
        document.getElementById('providerSort').value = '50';
        document.getElementById('providerEnabled').checked = true;

        var driverSelect = document.getElementById('providerDriver');
        driverSelect.value = 'openai_compatible';
        Array.from(driverSelect.options).forEach(function (option) {
            option.disabled = option.value !== 'openai_compatible';
        });

        document.getElementById('providerDialog').showModal();
    }

    async function submitProvider(event) {
        event.preventDefault();
        var button = document.getElementById('providerSubmitBtn');

        var payload = {
            slug: document.getElementById('providerSlug').value.trim(),
            name: document.getElementById('providerName').value.trim(),
            driver: document.getElementById('providerDriver').value,
            description: document.getElementById('providerDescription').value.trim(),
            base_url: document.getElementById('providerBaseUrl').value.trim(),
            currency: document.getElementById('providerCurrency').value.trim(),
            sort_order: document.getElementById('providerSort').value,
            enabled: document.getElementById('providerEnabled').checked,
            allow_custom_model: document.getElementById('providerAllowCustom').checked,
            requires_base_url: document.getElementById('providerRequiresBaseUrl').checked
        };

        button.disabled = true;
        try {
            var result = await api(AiCatalog.PROVIDERS_URL, 'POST', payload);
            closeDialog('providerDialog');
            window.location.href = AiCatalog.PROVIDERS_URL + '/' + result.id;
        } catch (error) {
            button.disabled = false;
            showDialogError('providerDialogError', error.message);
        }
    }

    async function removeProvider(pk) {
        var provider = catalog.find(function (item) {
            return String(item.provider_pk) === String(pk);
        });
        if (!provider) return;
        if (!confirm('确定删除供应商「' + provider.name + '」？被用户引用时无法删除。')) return;

        try {
            await api(AiCatalog.PROVIDERS_URL + '/' + pk, 'DELETE');
            showMessage('供应商已删除', 'success');
            setTimeout(function () { window.location.reload(); }, 400);
        } catch (error) {
            showMessage(error.message, 'error');
        }
    }

    function init() {
        bindCommon();
        catalog = AiCatalog.readJSON('ai-catalog-data') || [];
        renderProviders();

        var form = document.getElementById('providerForm');
        if (form) form.addEventListener('submit', submitProvider);
        AiCatalog.bindDialogBackdrop();

        document.addEventListener('click', function (event) {
            var btn = event.target.closest('[data-action]');
            if (!btn) return;
            var action = btn.dataset.action;

            if (action === 'open-provider-dialog') {
                openProviderDialog();
            } else if (action === 'close-dialog') {
                closeDialog(btn.dataset.dialog);
            } else if (action === 'remove-provider') {
                removeProvider(btn.dataset.providerPk);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
