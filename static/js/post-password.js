/**
 * 密码保护文章页的密码校验（原 templates/post_password.html 内联脚本）
 *
 * 校验地址由 form 的 data-verify-url 提供。
 */
(function () {
    'use strict';

    var form = document.getElementById('passwordForm');
    if (!form) return;

    var verifyUrl = form.getAttribute('data-verify-url') || '';
    var passwordInput = document.getElementById('password');
    var errorDiv = document.getElementById('errorMessage');
    var btn = form.querySelector('button[type="submit"]');
    var btnText = document.getElementById('btnText');
    var btnSpinner = document.getElementById('btnSpinner');

    function showError(message) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }

    function setBusy(busy) {
        btn.disabled = busy;
        btnText.style.display = busy ? 'none' : 'inline';
        btnSpinner.style.display = busy ? 'inline-flex' : 'none';
    }

    form.addEventListener('submit', async function (event) {
        event.preventDefault();
        errorDiv.style.display = 'none';
        setBusy(true);

        try {
            var data = await AppHttp.postJSON(verifyUrl, { password: passwordInput.value }, {
                silent: true
            });
            if (data && data.success) {
                window.location.href = data.redirect;
                return;
            }
            showError((data && data.message) || '密码验证失败');
            passwordInput.value = '';
            passwordInput.focus();
        } catch (error) {
            showError(error && error.status ? AppHttp.describe(error) : '网络错误，请重试');
        } finally {
            setBusy(false);
        }
    });

    // 刷新页面时不让浏览器重复提交上一次的表单
    if (window.history.replaceState) {
        window.history.replaceState(null, null, window.location.href);
    }
})();
