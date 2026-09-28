/**
 * 知识库首页「＋ 记想法」：弹窗输入 → 创建卡片（idea）。
 * 卡片可在回顾页「随机漫步」中随机遇见。
 */
(function () {
    'use strict';

    function csrfToken() {
        return window.getCsrfToken ? window.getCsrfToken() : '';
    }

    function toast(msg, type) {
        if (window.showAppToast) window.showAppToast(msg, type || 'success');
    }

    function openModal() {
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,.32);' +
            'backdrop-filter:blur(10px);z-index:10001;display:flex;align-items:center;' +
            'justify-content:center;padding:20px;';
        overlay.innerHTML = `
            <div style="width:min(94vw,520px);border-radius:18px;background:var(--card-bg,#fff);color:var(--text-color,#111827);border:1px solid var(--border-color,rgba(15,23,42,.08));box-shadow:0 24px 64px rgba(15,23,42,.18);padding:20px;">
                <div style="font-size:16px;font-weight:600;margin-bottom:12px;">⚡ 记想法</div>
                <input id="ideaTitle" type="text" placeholder="标题（可选）"
                       style="width:100%;padding:10px 12px;margin-bottom:10px;border-radius:10px;border:1px solid var(--border-color,#d1d5db);background:transparent;color:inherit;box-sizing:border-box;">
                <textarea id="ideaContent" rows="6" placeholder="想到什么就写下来..."
                          style="width:100%;padding:12px;border-radius:10px;border:1px solid var(--border-color,#d1d5db);background:transparent;color:inherit;resize:vertical;box-sizing:border-box;font-size:15px;line-height:1.6;"></textarea>
                <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:16px;">
                    <button type="button" data-act="cancel" style="padding:9px 16px;border-radius:10px;border:1px solid var(--border-color,#d1d5db);background:transparent;color:inherit;cursor:pointer;">取消</button>
                    <button type="button" data-act="save" style="padding:9px 18px;border-radius:10px;border:none;background:linear-gradient(135deg,#1abc9c,#16a089);color:#fff;font-weight:600;cursor:pointer;">存为卡片</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);

        const titleEl = overlay.querySelector('#ideaTitle');
        const contentEl = overlay.querySelector('#ideaContent');
        titleEl.focus();
        const close = () => overlay.remove();

        overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
        overlay.querySelector('[data-act="cancel"]').addEventListener('click', close);

        const saveBtn = overlay.querySelector('[data-act="save"]');
        saveBtn.addEventListener('click', async function () {
            const content = contentEl.value.trim();
            if (!content) {
                toast('内容不能为空', 'error');
                contentEl.focus();
                return;
            }
            saveBtn.disabled = true;
            try {
                const resp = await fetch('/knowledge_base/api/cards', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({ title: titleEl.value.trim(), content: content })
                });
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                close();
                toast('已存为卡片，可在回顾页随机遇见');
            } catch (e) {
                saveBtn.disabled = false;
                toast('保存失败，请重试', 'error');
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        const btn = document.getElementById('kbNewIdeaBtn');
        if (btn) btn.addEventListener('click', openModal);
    });
})();
