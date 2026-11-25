/**
 * AI 设置页（原 templates/admin/ai_settings.html 内联脚本）
 *
 * 供应商与当前配置通过 <script type="application/json" id="ai-settings-data"> 传入。
 */
(function () {
    'use strict';

    var providerModels = [];
    var currentConfig = {};

    function readData() {
        var el = document.getElementById('ai-settings-data');
        if (!el) return;
        try {
            var data = JSON.parse(el.textContent) || {};
            providerModels = data.providerModels || [];
            currentConfig = data.currentConfig || {};
        } catch (error) {
            console.error('Failed to parse AI settings data:', error);
        }
    }

    function setResult(resultDiv, text, state) {
        resultDiv.style.display = 'block';
        resultDiv.className = 'ai-test-result' + (state ? ' ' + state : '');
        resultDiv.textContent = text;
    }

    function selectedModel() {
        var custom = document.getElementById('aiModelCustom');
        if (custom && custom.value.trim()) return custom.value.trim();
        var select = document.getElementById('aiModel');
        return select ? select.value : '';
    }

    function updateModelOptions() {
        var provider = document.getElementById('aiProvider').value;
        var modelSelect = document.getElementById('aiModel');
        var customModelInput = document.getElementById('aiModelCustom');
        var baseUrlItem = document.getElementById('baseUrlItem');

        modelSelect.innerHTML = '';

        var providerInfo = providerModels.find(function (p) { return p.id === provider; });
        if (!providerInfo) return;

        var sameProvider = currentConfig.ai_provider === provider;
        var currentModel = sameProvider ? (currentConfig.ai_model || '') : '';
        var details = providerInfo.model_details || [];
        var visibleModels = details.filter(function (model) {
            return model.enabled || (currentModel && model.model_id === currentModel);
        });

        var selected = currentModel;
        if (!visibleModels.some(function (m) { return m.model_id === selected; })) {
            selected = providerInfo.default_model || '';
        }
        if (!selected || !visibleModels.some(function (m) { return m.model_id === selected; })) {
            var firstEnabled = visibleModels.find(function (m) { return m.enabled; });
            selected = firstEnabled ? firstEnabled.model_id : '';
        }

        visibleModels.forEach(function (model) {
            var option = document.createElement('option');
            option.value = model.model_id;
            var label = model.display_name && model.display_name !== model.model_id
                ? model.display_name + ' (' + model.model_id + ')'
                : model.model_id;
            option.textContent = label + (model.enabled ? '' : '（已停用）');
            option.disabled = !model.enabled && model.model_id !== currentModel;
            if (model.model_id === selected) option.selected = true;
            modelSelect.appendChild(option);
        });

        var hasEnabledCurrentModel = visibleModels.some(function (m) {
            return m.enabled && m.model_id === currentModel;
        });
        customModelInput.value = sameProvider && currentModel && !hasEnabledCurrentModel
            ? currentModel
            : '';

        if (providerInfo.allow_custom_model) {
            customModelInput.style.display = 'block';
        } else {
            customModelInput.style.display = 'none';
            customModelInput.value = '';
        }

        // 没有预设模型时（例如内置 custom），必须手填模型 ID
        if (visibleModels.length === 0) {
            modelSelect.style.display = 'none';
            customModelInput.placeholder = '必填：填写模型 ID，例如 gpt-4o-mini';
        } else {
            modelSelect.style.display = 'block';
            customModelInput.placeholder = '可选：填写控制台中的实际模型 ID，优先级高于下拉框';
        }

        // 仅需要用户自填 Base URL 的供应商展示该输入框
        baseUrlItem.style.display = providerInfo.requires_base_url ? 'block' : 'none';
    }

    async function testConfig() {
        var resultDiv = document.getElementById('testResult');
        setResult(resultDiv, '正在测试连接...', '');

        var config = {
            ai_provider: document.getElementById('aiProvider').value,
            ai_model: selectedModel(),
            ai_api_key: document.getElementById('apiKey').value,
            ai_base_url: document.getElementById('aiBaseUrl').value.trim()
        };

        try {
            var data = await AppHttp.postJSON('/admin/ai/test', config, { silent: true });
            if (data && data.success) {
                setResult(resultDiv, '✅ ' + data.message, 'success');
            } else {
                setResult(resultDiv, '❌ ' + ((data && data.message) || '测试失败'), 'error');
            }
        } catch (error) {
            setResult(resultDiv, '❌ 测试失败: ' + AppHttp.describe(error), 'error');
        }
    }

    async function saveConfig() {
        var resultDiv = document.getElementById('testResult');
        setResult(resultDiv, '正在保存配置...', '');

        var config = {
            ai_tag_generation_enabled: document.getElementById('aiEnabled').checked,
            ai_provider: document.getElementById('aiProvider').value,
            ai_model: selectedModel(),
            ai_api_key: document.getElementById('apiKey').value,
            ai_base_url: document.getElementById('aiBaseUrl').value.trim(),
            ai_embedding_enabled: document.getElementById('aiEmbeddingEnabled').checked,
            ai_embedding_base_url: document.getElementById('aiEmbeddingBaseUrl').value.trim(),
            ai_embedding_api_key: document.getElementById('aiEmbeddingApiKey').value,
            ai_embedding_model: document.getElementById('aiEmbeddingModel').value.trim()
        };

        try {
            var data = await AppHttp.postJSON('/admin/ai/configure', config, {
                acceptErrors: true,
                silent: true
            });
            if (data && data.success) {
                setResult(resultDiv, '✅ 配置已保存！', 'success');
                setTimeout(function () { resultDiv.style.display = 'none'; }, 3000);
            } else {
                setResult(resultDiv, '❌ 保存失败: ' + ((data && data.error) || '未知错误'), 'error');
            }
        } catch (error) {
            var message = error && error.status
                ? '服务器错误 (' + error.status + ')'
                : AppHttp.describe(error);
            setResult(resultDiv, '❌ 保存失败: ' + message, 'error');
        }
    }

    async function testEmbeddingConnection() {
        var resultDiv = document.getElementById('embeddingTestResult');
        setResult(resultDiv, '正在测试 Embedding 连接...', '');

        var config = {
            ai_embedding_base_url: document.getElementById('aiEmbeddingBaseUrl').value.trim(),
            ai_embedding_api_key: document.getElementById('aiEmbeddingApiKey').value,
            ai_embedding_model: document.getElementById('aiEmbeddingModel').value.trim()
        };

        try {
            var data = await AppHttp.postJSON('/admin/ai/embedding/test', config, { silent: true });
            if (data && data.success) {
                setResult(resultDiv, '✅ ' + data.message, 'success');
            } else {
                setResult(resultDiv, '❌ ' + ((data && data.message) || '测试失败'), 'error');
            }
        } catch (error) {
            setResult(resultDiv, '❌ 测试失败: ' + AppHttp.describe(error), 'error');
        }
    }

    async function rebuildEmbeddings() {
        var resultDiv = document.getElementById('embeddingTestResult');
        setResult(resultDiv, '正在入队回填任务...', '');

        try {
            var data = await AppHttp.postJSON('/admin/ai/embeddings/rebuild', {}, { silent: true });
            if (data && data.success) {
                setResult(resultDiv, '✅ ' + data.message, 'success');
            } else {
                setResult(resultDiv, '❌ ' + ((data && (data.error || data.message)) || '重建失败'), 'error');
            }
        } catch (error) {
            setResult(resultDiv, '❌ 重建失败: ' + AppHttp.describe(error), 'error');
        }
    }

    function init() {
        readData();
        updateModelOptions();

        var providerSelect = document.getElementById('aiProvider');
        if (providerSelect) providerSelect.addEventListener('change', updateModelOptions);

        document.addEventListener('click', function (event) {
            var btn = event.target.closest('[data-action]');
            if (!btn) return;
            var action = btn.dataset.action;
            if (action === 'test-config') testConfig();
            else if (action === 'save-config') saveConfig();
            else if (action === 'test-embedding') testEmbeddingConnection();
            else if (action === 'rebuild-embeddings') rebuildEmbeddings();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
