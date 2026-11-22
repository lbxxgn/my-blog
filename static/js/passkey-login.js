/**
 * 登录页的 Passkey 快捷登录（原 templates/login.html 内联脚本）
 *
 * 后端地址与默认跳转由 #passkey-login-config 的 data-* 提供。
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var cfgEl = document.getElementById('passkey-login-config');
        var cfg = cfgEl ? cfgEl.dataset : {};
        var button = document.getElementById('passkeyLoginButton');
        var status = document.getElementById('passkeyLoginStatus');
        var hint = document.getElementById('passkeyLoginHint');
        var rememberDevice = document.getElementById('rememberDevice');
        if (!button || !status) return;

        var next = new URLSearchParams(window.location.search).get('next') || '';
        var hostAdvice = window.PasskeyAuth ? window.PasskeyAuth.getHostAdvice() : { valid: true };
        var loginOptions = {
            beginUrl: cfg.beginUrl,
            finishUrl: cfg.finishUrl,
            csrfToken: AppHttp.getCsrfToken(),
            next: next,
            rememberDevice: Boolean(rememberDevice && rememberDevice.checked)
        };

        function setHint(message, type) {
            if (!hint) return;
            hint.classList.toggle('is-visible', Boolean(message));
            hint.classList.toggle('is-success', type === 'success');
            hint.textContent = message || '';
        }

        function redirect(result) {
            status.textContent = '验证成功，正在登录...';
            window.location.href = (result && result.redirect) || cfg.defaultRedirect || '/';
        }

        if (!window.PasskeyAuth || !window.PasskeyAuth.isSupported()) {
            button.disabled = true;
            status.textContent = '当前浏览器暂不支持 Passkey 快捷登录';
            return;
        }

        if (!hostAdvice.valid) {
            button.disabled = true;
            status.textContent = hostAdvice.message;
            return;
        }

        window.PasskeyAuth.getCapabilitySummary().then(function (summary) {
            if (summary.platformAuthenticator && summary.remembered) {
                setHint('这台设备之前已经成功使用过快捷登录，Safari 通常会直接调起 Touch ID / Face ID。', 'success');
                button.textContent = '继续使用快捷登录';
            } else if (summary.platformAuthenticator) {
                setHint('这台设备支持本机生物识别。绑定过一次后，后续登录会更顺。');
            } else if (summary.remembered) {
                setHint('这台设备之前使用过快捷登录，但当前浏览器可能不会直接调起本机生物识别。');
            } else {
                setHint('如果这是你第一次在这台设备上使用，请先密码登录并绑定一次快捷登录。');
            }

            if (!summary.conditionalMediation) return;
            status.textContent = '正在准备更顺滑的快捷登录体验...';
            window.PasskeyAuth.authenticateWithPasskey(
                Object.assign({}, loginOptions, { mediation: 'conditional' })
            ).then(function (result) {
                if (!result) {
                    status.textContent = '';
                    return;
                }
                redirect(result);
            }).catch(function (error) {
                status.textContent = '';
                if ((error.message || '').indexOf('未找到匹配的 Passkey') !== -1) {
                    setHint('这台设备还没有绑定当前网站的快捷登录。先用密码登录，再到“修改密码”页里启用一次。');
                }
            });
        });

        button.addEventListener('click', async function () {
            button.disabled = true;
            status.textContent = '正在调用系统验证...';

            try {
                loginOptions.rememberDevice = Boolean(rememberDevice && rememberDevice.checked);
                var result = await window.PasskeyAuth.authenticateWithPasskey(loginOptions);
                if (!result) {
                    status.textContent = '你还没有选择用于登录的 Passkey';
                    return;
                }
                redirect(result);
            } catch (error) {
                status.textContent = error.message || 'Passkey 登录失败';
                if (window.showAppToast) {
                    window.showAppToast(status.textContent, 'error');
                }
                if ((error.message || '').indexOf('未找到匹配的 Passkey') !== -1) {
                    setHint('这台设备还没有绑定当前网站的快捷登录。先用密码登录，再到“修改密码”页里启用一次。');
                }
            } finally {
                button.disabled = false;
            }
        });
    });
})();
