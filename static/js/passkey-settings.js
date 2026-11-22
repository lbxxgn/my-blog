/**
 * 修改密码页的 Passkey 设备管理（原 templates/change_password.html 内联脚本）
 *
 * 后端地址由 #passkey-settings-config 的 data-* 提供。
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var cfgEl = document.getElementById('passkey-settings-config');
        var cfg = cfgEl ? cfgEl.dataset : {};
        var registerButton = document.getElementById('registerPasskeyButton');
        var status = document.getElementById('passkeyRegisterStatus');
        var hint = document.getElementById('passkeyRegisterHint');
        var list = document.getElementById('passkeyList');
        if (!registerButton || !status || !list) return;

        var csrfToken = AppHttp.getCsrfToken();
        var hostAdvice = window.PasskeyAuth ? window.PasskeyAuth.getHostAdvice() : { valid: true };

        function setHint(message, type) {
            if (!hint) return;
            hint.classList.toggle('is-visible', Boolean(message));
            hint.classList.toggle('is-success', type === 'success');
            hint.textContent = message || '';
        }

        function escapeHtml(value) {
            var div = document.createElement('div');
            div.textContent = value == null ? '' : String(value);
            return div.innerHTML;
        }

        function passkeyItemHtml(passkey) {
            var labels = Array.isArray(passkey.transport_labels) && passkey.transport_labels.length
                ? ' · ' + escapeHtml(passkey.transport_labels.join(' / '))
                : '';
            var synced = passkey.backup_state
                ? '<span class="passkey-badge passkey-badge-synced">已同步</span>'
                : '';
            return '' +
                '<div class="passkey-item" data-passkey-id="' + escapeHtml(passkey.id) + '">' +
                    '<div>' +
                        '<div class="passkey-item-header">' +
                            '<div class="passkey-device-name">' + escapeHtml(passkey.device_name || '未命名设备') + '</div>' +
                            '<span class="passkey-badge">' + escapeHtml(passkey.credential_device_type_label || '单设备') + '</span>' +
                            synced +
                        '</div>' +
                        '<div class="passkey-meta">绑定于 ' + escapeHtml(passkey.created_at || '') +
                            (passkey.last_used_at ? ' · 最近使用 ' + escapeHtml(passkey.last_used_at) : '') +
                            labels +
                        '</div>' +
                    '</div>' +
                    '<button type="button" class="btn btn-danger passkey-delete-button" data-passkey-id="' +
                        escapeHtml(passkey.id) + '">移除</button>' +
                '</div>';
        }

        function renderPasskeys(passkeys) {
            if (!Array.isArray(passkeys) || passkeys.length === 0) {
                list.innerHTML = '<p id="emptyPasskeysState" class="passkey-empty">还没有绑定任何快捷登录设备。</p>';
                return;
            }
            list.innerHTML = passkeys.map(passkeyItemHtml).join('');
            bindDeleteButtons();
        }

        async function refreshPasskeys() {
            var data = await AppHttp.json(cfg.listUrl, {
                credentials: 'same-origin'
            });
            if (!data || data.success === false) {
                throw new Error((data && data.error) || '刷新 Passkey 列表失败');
            }
            renderPasskeys(data.passkeys || []);
        }

        function bindDeleteButtons() {
            list.querySelectorAll('.passkey-delete-button').forEach(function (button) {
                button.addEventListener('click', async function () {
                    var passkeyId = button.dataset.passkeyId;
                    var confirmed = await window.showAppConfirm('确定要移除这台设备的快捷登录吗？', {
                        destructive: true,
                        confirmText: '移除'
                    });
                    if (!confirmed) return;

                    try {
                        var data = await AppHttp.json(cfg.listUrl + '/' + passkeyId, {
                            method: 'DELETE',
                            credentials: 'same-origin',
                            headers: { 'X-CSRFToken': csrfToken }
                        });
                        if (!data || data.success === false) {
                            throw new Error((data && data.error) || '移除失败');
                        }
                        await refreshPasskeys();
                        window.PasskeyAuth.showToast(data.message || '已移除快捷登录设备');
                    } catch (error) {
                        window.PasskeyAuth.showToast(error.message || AppHttp.describe(error), 'error');
                    }
                });
            });
        }

        bindDeleteButtons();

        if (!window.PasskeyAuth || !window.PasskeyAuth.isSupported()) {
            registerButton.disabled = true;
            status.textContent = '当前浏览器暂不支持 Passkey';
            return;
        }

        if (!hostAdvice.valid) {
            registerButton.disabled = true;
            status.textContent = hostAdvice.message;
            return;
        }

        window.PasskeyAuth.getCapabilitySummary().then(function (summary) {
            if (summary.platformAuthenticator && summary.remembered) {
                setHint('这台设备已经完成过快捷登录设置。如果你想重绑，可以继续点按钮重新添加。', 'success');
                return;
            }
            if (summary.platformAuthenticator) {
                setHint('这台设备支持本机生物识别。绑定完成后，登录页通常会直接调用 Touch ID / Face ID。');
                return;
            }
            setHint('如果当前浏览器没有本机生物识别能力，也仍可能通过 iCloud 钥匙串或跨设备方式使用 Passkey。');
        });

        registerButton.addEventListener('click', async function () {
            registerButton.disabled = true;
            status.textContent = '正在调用系统验证...';

            try {
                var deviceName = window.showAppPrompt
                    ? (await window.showAppPrompt('给这台设备起个名字（可选）', '', {
                        placeholder: '例如：我的 MacBook'
                    })) || ''
                    : '';
                var result = await window.PasskeyAuth.registerPasskey({
                    beginUrl: cfg.beginUrl,
                    finishUrl: cfg.finishUrl,
                    csrfToken: csrfToken,
                    deviceName: deviceName
                });
                status.textContent = '绑定成功，正在刷新设备列表...';
                window.PasskeyAuth.showToast(result.message || '快捷登录已启用');
                await refreshPasskeys();
                setHint('这台设备已经可以优先使用快捷登录了。下次到登录页时，通常会更直接地调起生物识别。', 'success');
            } catch (error) {
                status.textContent = error.message || '绑定失败';
                window.PasskeyAuth.showToast(status.textContent, 'error');
            } finally {
                registerButton.disabled = false;
            }
        });
    });
})();
