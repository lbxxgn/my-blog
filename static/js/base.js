// base.html 全局脚本（由模板内联 JS 外置而来）
// 包含：导航下拉菜单、主题切换、全局工具函数（getCsrfToken/showAppToast/showAppConfirm/showAppPrompt）
    // Dropdown Menu Click Handler
    document.addEventListener('DOMContentLoaded', function() {
        // Prevent dropdowns from closing when moving mouse inside
        document.querySelectorAll('.dropdown').forEach(dropdown => {
            dropdown.addEventListener('mouseleave', function(e) {
                // Don't close on mouseleave, only on outside click
                e.stopPropagation();
            });

            dropdown.addEventListener('mouseenter', function(e) {
                e.stopPropagation();
            });
        });

        // Handle all dropdown toggles
        const dropdownToggles = document.querySelectorAll('.dropdown-toggle');

        dropdownToggles.forEach(toggle => {
            toggle.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                const dropdown = this.closest('.dropdown');
                const menu = dropdown.querySelector('.dropdown-menu');

                // Close all other dropdowns
                document.querySelectorAll('.dropdown').forEach(d => {
                    if (d !== dropdown) {
                        const m = d.querySelector('.dropdown-menu');
                        if (m) m.classList.remove('show');
                    }
                });

                // Toggle current dropdown
                menu.classList.toggle('show');
            });
        });

        // Close dropdowns when clicking outside (not on navigation)
        document.addEventListener('click', function(e) {
            const nav = document.querySelector('nav');
            if (nav && !nav.contains(e.target)) {
                document.querySelectorAll('.dropdown-menu').forEach(menu => {
                    menu.classList.remove('show');
                });
            }
        });

        // Keep dropdown open when hovering over menu items
        document.querySelectorAll('.dropdown-menu').forEach(menu => {
            menu.addEventListener('mouseenter', function(e) {
                e.stopPropagation();
            });

            menu.addEventListener('mouseleave', function(e) {
                e.stopPropagation();
            });
        });

        // Nav theme toggle (desktop)
        const themeToggleNav = document.getElementById('themeToggleNav');
        if (themeToggleNav) {
            themeToggleNav.addEventListener('click', function() {
                const isDark = document.body.classList.contains('dark-theme');
                const newTheme = isDark ? 'light' : 'dark';
                if (newTheme === 'dark') {
                    document.body.classList.add('dark-theme');
                } else {
                    document.body.classList.remove('dark-theme');
                }
                localStorage.setItem('theme', newTheme);
                // Sync icon on nav toggle
                this.querySelector('.theme-toggle-nav-icon').textContent = newTheme === 'dark' ? '☀️' : '🌙';
                // Sync dropdown toggle if visible
                const innerIcon = document.querySelector('.theme-toggle-icon');
                const innerText = document.querySelector('.theme-toggle-text');
                if (innerIcon) innerIcon.textContent = newTheme === 'dark' ? '☀️' : '🌙';
                if (innerText) innerText.textContent = newTheme === 'dark' ? '亮色' : '暗色';
            });
            // Set initial icon from the actual applied theme (inline script may follow system preference)
            const isDarkNow = document.body.classList.contains('dark-theme');
            themeToggleNav.querySelector('.theme-toggle-nav-icon').textContent = isDarkNow ? '☀️' : '🌙';
        }
    });


window.getCsrfToken = function() {
    return document.querySelector('meta[name="csrf_token"]')?.content || '';
};
window.showAppToast = function(message, type = 'success') {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.style.position = 'fixed';
    toast.style.left = '50%';
    toast.style.bottom = '32px';
    toast.style.transform = 'translateX(-50%) translateY(14px)';
    toast.style.padding = '12px 18px';
    toast.style.borderRadius = '999px';
    toast.style.fontSize = '14px';
    toast.style.fontWeight = '600';
    toast.style.color = '#fff';
    toast.style.background = type === 'error'
        ? 'linear-gradient(135deg, rgba(232, 93, 117, 0.96), rgba(201, 61, 86, 0.96))'
        : 'linear-gradient(135deg, rgba(26, 188, 156, 0.96), rgba(22, 160, 137, 0.96))';
    toast.style.boxShadow = type === 'error'
        ? '0 8px 24px rgba(201, 61, 86, 0.28)'
        : '0 8px 24px rgba(22, 160, 137, 0.24)';
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.22s ease, transform 0.22s ease';
    toast.style.zIndex = '10000';
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(-50%) translateY(0)';
    });

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(10px)';
        setTimeout(() => toast.remove(), 220);
    }, 2200);
};
window.showAppConfirm = function(message, options = {}) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        const dialog = document.createElement('div');
        const text = document.createElement('div');
        const actions = document.createElement('div');
        const cancelBtn = document.createElement('button');
        const confirmBtn = document.createElement('button');

        overlay.style.position = 'fixed';
        overlay.style.inset = '0';
        overlay.style.background = 'rgba(15, 23, 42, 0.32)';
        overlay.style.backdropFilter = 'blur(10px)';
        overlay.style.zIndex = '10001';
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.padding = '20px';

        dialog.style.width = 'min(92vw, 420px)';
        dialog.style.borderRadius = '18px';
        dialog.style.background = 'var(--card-bg, #fff)';
        dialog.style.color = 'var(--text-color, #111827)';
        dialog.style.border = '1px solid var(--border-color, rgba(15, 23, 42, 0.08))';
        dialog.style.boxShadow = '0 24px 64px rgba(15, 23, 42, 0.18)';
        dialog.style.padding = '20px';

        text.textContent = message;
        text.style.whiteSpace = 'pre-wrap';
        text.style.lineHeight = '1.6';
        text.style.fontSize = '15px';

        actions.style.display = 'flex';
        actions.style.justifyContent = 'flex-end';
        actions.style.gap = '10px';
        actions.style.marginTop = '18px';

        cancelBtn.type = 'button';
        cancelBtn.textContent = options.cancelText || '取消';
        cancelBtn.style.padding = '9px 16px';
        cancelBtn.style.borderRadius = '10px';
        cancelBtn.style.border = '1px solid var(--border-color, #d1d5db)';
        cancelBtn.style.background = 'transparent';
        cancelBtn.style.color = 'inherit';
        cancelBtn.style.cursor = 'pointer';

        confirmBtn.type = 'button';
        confirmBtn.textContent = options.confirmText || '确认';
        confirmBtn.style.padding = '9px 16px';
        confirmBtn.style.borderRadius = '10px';
        confirmBtn.style.border = 'none';
        confirmBtn.style.background = options.destructive
            ? 'linear-gradient(135deg, #ef4444, #dc2626)'
            : 'linear-gradient(135deg, #10b981, #059669)';
        confirmBtn.style.color = '#fff';
        confirmBtn.style.cursor = 'pointer';

        const cleanup = (result) => {
            overlay.remove();
            resolve(result);
        };

        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                cleanup(false);
            }
        });
        cancelBtn.addEventListener('click', () => cleanup(false));
        confirmBtn.addEventListener('click', () => cleanup(true));

        actions.appendChild(cancelBtn);
        actions.appendChild(confirmBtn);
        dialog.appendChild(text);
        dialog.appendChild(actions);
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        confirmBtn.focus();
    });
};
window.showAppPrompt = function(message, defaultValue = '', options = {}) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        const dialog = document.createElement('div');
        const text = document.createElement('div');
        const input = document.createElement('input');
        const actions = document.createElement('div');
        const cancelBtn = document.createElement('button');
        const confirmBtn = document.createElement('button');

        overlay.style.position = 'fixed';
        overlay.style.inset = '0';
        overlay.style.background = 'rgba(15, 23, 42, 0.32)';
        overlay.style.backdropFilter = 'blur(10px)';
        overlay.style.zIndex = '10001';
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.padding = '20px';

        dialog.style.width = 'min(92vw, 420px)';
        dialog.style.borderRadius = '18px';
        dialog.style.background = 'var(--card-bg, #fff)';
        dialog.style.color = 'var(--text-color, #111827)';
        dialog.style.border = '1px solid var(--border-color, rgba(15, 23, 42, 0.08))';
        dialog.style.boxShadow = '0 24px 64px rgba(15, 23, 42, 0.18)';
        dialog.style.padding = '20px';

        text.textContent = message;
        text.style.whiteSpace = 'pre-wrap';
        text.style.lineHeight = '1.6';
        text.style.fontSize = '15px';

        input.type = 'text';
        input.value = defaultValue || '';
        input.placeholder = options.placeholder || '';
        input.style.width = '100%';
        input.style.marginTop = '14px';
        input.style.padding = '11px 12px';
        input.style.borderRadius = '10px';
        input.style.border = '1px solid var(--border-color, #d1d5db)';
        input.style.background = 'transparent';
        input.style.color = 'inherit';

        actions.style.display = 'flex';
        actions.style.justifyContent = 'flex-end';
        actions.style.gap = '10px';
        actions.style.marginTop = '18px';

        cancelBtn.type = 'button';
        cancelBtn.textContent = options.cancelText || '取消';
        cancelBtn.style.padding = '9px 16px';
        cancelBtn.style.borderRadius = '10px';
        cancelBtn.style.border = '1px solid var(--border-color, #d1d5db)';
        cancelBtn.style.background = 'transparent';
        cancelBtn.style.color = 'inherit';
        cancelBtn.style.cursor = 'pointer';

        confirmBtn.type = 'button';
        confirmBtn.textContent = options.confirmText || '确认';
        confirmBtn.style.padding = '9px 16px';
        confirmBtn.style.borderRadius = '10px';
        confirmBtn.style.border = 'none';
        confirmBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        confirmBtn.style.color = '#fff';
        confirmBtn.style.cursor = 'pointer';

        const cleanup = (result) => {
            overlay.remove();
            resolve(result);
        };

        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                cleanup(null);
            }
        });
        cancelBtn.addEventListener('click', () => cleanup(null));
        confirmBtn.addEventListener('click', () => cleanup(input.value));
        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                cleanup(input.value);
            } else if (event.key === 'Escape') {
                event.preventDefault();
                cleanup(null);
            }
        });

        actions.appendChild(cancelBtn);
        actions.appendChild(confirmBtn);
        dialog.appendChild(text);
        dialog.appendChild(input);
        dialog.appendChild(actions);
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        input.focus();
        input.select();
    });
};

document.addEventListener('submit', async function(event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.dataset.confirm) {
        return;
    }
    if (form.dataset.confirmed === 'true') {
        delete form.dataset.confirmed;
        return;
    }

    event.preventDefault();
    const confirmed = await window.showAppConfirm(form.dataset.confirm, {
        destructive: form.dataset.confirmDestructive === 'true',
        confirmText: form.dataset.confirmText || '确认'
    });
    if (confirmed) {
        form.dataset.confirmed = 'true';
        form.requestSubmit ? form.requestSubmit() : form.submit();
    }
}, true);

document.addEventListener('click', async function(event) {
    const trigger = event.target.closest('a[data-confirm]');
    if (!trigger) {
        return;
    }
    if (trigger.dataset.confirmed === 'true') {
        delete trigger.dataset.confirmed;
        return;
    }

    event.preventDefault();
    const confirmed = await window.showAppConfirm(trigger.dataset.confirm, {
        destructive: trigger.dataset.confirmDestructive === 'true',
        confirmText: trigger.dataset.confirmText || '确认'
    });
    if (confirmed) {
        trigger.dataset.confirmed = 'true';
        window.location.href = trigger.href;
    }
}, true);

// Flash 消息：5 秒后自动淡出移除
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('main .alert').forEach(function(el) {
        el.setAttribute('role', 'alert');
        setTimeout(function() {
            el.style.transition = 'opacity 0.4s ease';
            el.style.opacity = '0';
            setTimeout(function() { el.remove(); }, 400);
        }, 5000);
    });
});
