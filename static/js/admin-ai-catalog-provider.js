/**
 * AI 供应商详情页（原 templates/admin/ai_catalog_provider.html 内联脚本）
 *
 * 供应商数据通过 <script type="application/json" id="ai-provider-data"> 传入。
 */
(function () {
    'use strict';

    var provider = {};
    var editingModelPk = null;

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

    function providerUrl() {
        return AiCatalog.PROVIDERS_URL + '/' + provider.provider_pk;
    }

    function modelByPk(pk) {
        return (provider.model_details || []).find(function (model) {
            return String(model.id) === String(pk);
        });
    }

    function priceText(value) {
        if (value === null || value === undefined || value === '') return '默认';
        return (provider.currency_symbol || '') + value;
    }

    function renderModels() {
        var tbody = document.getElementById('modelRows');
        if (!tbody) return;
        var models = provider.model_details || [];
        var countEl = document.getElementById('modelCount');
        if (countEl) countEl.textContent = models.length + ' 个模型';

        if (!models.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-row">该供应商暂无模型，请先新增</td></tr>';
            return;
        }

        tbody.innerHTML = models.map(function (model) {
            return '' +
                '<tr>' +
                    '<td>' +
                        '<div class="name-cell">' +
                            '<strong>' + esc(model.display_name || model.model_id) + '</strong>' +
                            '<span class="model-id">' + esc(model.model_id) + '</span>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div class="name-cell">' +
                            '<span>输入：' + esc(priceText(model.input_price)) + '</span>' +
                            '<span class="muted">输出：' + esc(priceText(model.output_price)) + '</span>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div class="badge-stack">' +
                            '<span class="badge ' + (model.enabled ? 'badge-on' : 'badge-off') + '">' +
                                (model.enabled ? '启用' : '停用') +
                            '</span>' +
                            (model.is_default ? '<span class="badge badge-default">默认</span>' : '') +
                            '<span class="badge">' + (model.usage_count || 0) + ' 用户</span>' +
                        '</div>' +
                    '</td>' +
                    '<td>' +
                        '<div class="actions">' +
                            '<button type="button" class="btn" data-action="edit-model" ' +
                                'data-model-id="' + esc(model.id) + '">编辑</button>' +
                            '<button type="button" class="btn btn-danger" data-action="remove-model" ' +
                                'data-model-id="' + esc(model.id) + '">删除</button>' +
                        '</div>' +
                    '</td>' +
                '</tr>';
        }).join('');
    }

    function updateModelPriceHints() {
        var currency = provider.currency || '';
        var symbol = provider.currency_symbol || '';
        var text = '留空表示沿用驱动默认价；当前币种：' + currency + ' ' + symbol;
        document.getElementById('modelInputPriceHint').textContent = text;
        document.getElementById('modelOutputPriceHint').textContent = text;
    }

    function openProviderDialog() {
        clearDialogError('providerDialogError');

        document.getElementById('providerSlug').value = provider.slug;
        document.getElementById('providerName').value = provider.name;
        document.getElementById('providerDescription').value = provider.description || '';
        document.getElementById('providerBaseUrl').value = provider.base_url || '';
        document.getElementById('providerCurrency').value = provider.currency || 'CNY';
        document.getElementById('providerSort').value = provider.sort_order || 0;
        document.getElementById('providerEnabled').checked = !!provider.enabled;
        document.getElementById('providerAllowCustom').checked = !!provider.allow_custom_model;
        document.getElementById('providerRequiresBaseUrl').checked = !!provider.requires_base_url;
        document.getElementById('providerDriver').value = provider.driver;

        document.getElementById('providerDialog').showModal();
    }

    async function submitProvider(event) {
        event.preventDefault();
        var button = document.getElementById('providerSubmitBtn');

        var payload = {
            name: document.getElementById('providerName').value.trim(),
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
            await api(providerUrl(), 'PUT', payload);
            closeDialog('providerDialog');
            showMessage('供应商信息已更新', 'success');
            setTimeout(function () { window.location.reload(); }, 400);
        } catch (error) {
            button.disabled = false;
            showDialogError('providerDialogError', error.message);
        }
    }

    function openModelDialog(pk) {
        var form = document.getElementById('modelForm');
        if (!form) return;
        form.reset();
        clearDialogError('modelDialogError');

        var pkValue = pk === undefined || pk === null || pk === '' ? null : pk;
        editingModelPk = pkValue;

        var modelIdInput = document.getElementById('modelId');
        var title = document.getElementById('modelDialogTitle');
        var subtitle = document.getElementById('modelDialogSubtitle');
        var submitBtn = document.getElementById('modelSubmitBtn');

        if (pkValue !== null) {
            var model = modelByPk(pkValue);
            if (!model) {
                showMessage('模型不存在，请刷新页面后重试', 'error');
                return;
            }
            title.textContent = '编辑模型：' + model.model_id;
            subtitle.textContent = '供应商：' + provider.name + ' · 币种：' + provider.currency + ' · 模型 ID 创建后不可修改';
            submitBtn.textContent = '保存模型';

            modelIdInput.value = model.model_id;
            modelIdInput.readOnly = true;
            document.getElementById('modelDisplayName').value = model.display_name || '';
            document.getElementById('modelDescription').value = model.description || '';
            document.getElementById('modelInputPrice').value =
                model.input_price === null || model.input_price === undefined ? '' : model.input_price;
            document.getElementById('modelOutputPrice').value =
                model.output_price === null || model.output_price === undefined ? '' : model.output_price;
            document.getElementById('modelSort').value = model.sort_order || 0;
            document.getElementById('modelEnabled').checked = !!model.enabled;
            document.getElementById('modelDefault').checked = !!model.is_default;
        } else {
            title.textContent = '新增模型';
            subtitle.textContent = '将添加到：' + provider.name + '（' + provider.slug + '）';
            submitBtn.textContent = '创建模型';

            modelIdInput.readOnly = false;
            document.getElementById('modelSort').value = '10';
            document.getElementById('modelEnabled').checked = true;
            document.getElementById('modelDefault').checked = false;
        }

        updateModelPriceHints();
        document.getElementById('modelDialog').showModal();
    }

    async function submitModel(event) {
        event.preventDefault();
        var button = document.getElementById('modelSubmitBtn');
        var pk = editingModelPk;

        var payload = {
            display_name: document.getElementById('modelDisplayName').value.trim(),
            description: document.getElementById('modelDescription').value.trim(),
            input_price: document.getElementById('modelInputPrice').value,
            output_price: document.getElementById('modelOutputPrice').value,
            sort_order: document.getElementById('modelSort').value,
            enabled: document.getElementById('modelEnabled').checked,
            is_default: document.getElementById('modelDefault').checked
        };

        button.disabled = true;
        try {
            if (pk !== null) {
                await api(AiCatalog.MODELS_URL + '/' + pk, 'PUT', payload);
                showMessage('模型已更新', 'success');
            } else {
                payload.provider_id = provider.provider_pk;
                payload.model_id = document.getElementById('modelId').value.trim();
                await api(AiCatalog.MODELS_URL, 'POST', payload);
                showMessage('模型已新增', 'success');
            }
            closeDialog('modelDialog');
            setTimeout(function () { window.location.reload(); }, 400);
        } catch (error) {
            button.disabled = false;
            showDialogError('modelDialogError', error.message);
        }
    }

    async function removeModel(pk) {
        var model = modelByPk(pk);
        if (!model) return;
        if (!confirm('确定删除模型「' + model.model_id + '」？被用户引用时无法删除。')) return;

        try {
            await api(AiCatalog.MODELS_URL + '/' + pk, 'DELETE');
            showMessage('模型已删除', 'success');
            setTimeout(function () { window.location.reload(); }, 400);
        } catch (error) {
            showMessage(error.message, 'error');
        }
    }

    function init() {
        bindCommon();
        provider = AiCatalog.readJSON('ai-provider-data') || {};
        renderModels();

        var providerForm = document.getElementById('providerForm');
        if (providerForm) providerForm.addEventListener('submit', submitProvider);
        var modelForm = document.getElementById('modelForm');
        if (modelForm) modelForm.addEventListener('submit', submitModel);
        AiCatalog.bindDialogBackdrop();

        document.addEventListener('click', function (event) {
            var btn = event.target.closest('[data-action]');
            if (!btn) return;
            var action = btn.dataset.action;

            if (action === 'open-provider-dialog') {
                openProviderDialog();
            } else if (action === 'open-model-dialog') {
                openModelDialog(btn.dataset.modelId);
            } else if (action === 'close-dialog') {
                closeDialog(btn.dataset.dialog);
            } else if (action === 'edit-model') {
                openModelDialog(btn.dataset.modelId);
            } else if (action === 'remove-model') {
                removeModel(btn.dataset.modelId);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
