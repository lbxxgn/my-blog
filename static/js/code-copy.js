/* 代码块复制按钮
   注意：提示节点改为「首次复制时才创建」。此前是在 DOMContentLoaded 无条件插入 body，
   而它靠 style.css 的 opacity:0 隐藏；主样式表尚未生效时会以纯文本形式闪现
   （每次刷新页面都能看到「代码已复制！」字样）。 */
document.addEventListener('DOMContentLoaded', function () {
    // 兼容三种代码块来源：
    //   Markdown → <pre><code>
    //   Quill 1.x → <pre class="prettyprint">
    //   Quill 2.x → <div class="ql-code-block-container"><div class="ql-code-block">
    // 旧实现只匹配 pre > code，Quill 产出的代码块根本没有复制按钮。
    var codeBlocks = Array.prototype.filter.call(
        document.querySelectorAll('.post-content pre, .post-content .ql-code-block-container'),
        function (block) {
            return !block.parentElement.closest('.ql-code-block-container') || block.classList.contains('ql-code-block-container');
        }
    );
    if (!codeBlocks.length) return;

    var toastTimer = null;

    // 懒创建：加载期 DOM 中不存在这个节点
    function getToast() {
        var toast = document.getElementById('codeCopyToast');
        if (toast) return toast;
        toast = document.createElement('div');
        toast.id = 'codeCopyToast';
        toast.className = 'code-copy-toast';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        document.body.appendChild(toast);
        return toast;
    }

    function flashToast(text, isError) {
        var toast = getToast();
        toast.textContent = text;
        toast.classList.toggle('is-error', !!isError);
        toast.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(function () {
            toast.classList.remove('show');
        }, 2000);
    }

    var ICON_COPY = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<rect x="9" y="9" width="11" height="11" rx="2"></rect>' +
        '<path d="M15 5.5A2.5 2.5 0 0 0 12.5 3h-6A2.5 2.5 0 0 0 4 5.5v6A2.5 2.5 0 0 0 6.5 14"></path></svg>';
    var ICON_DONE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="m5 12.5 4.5 4.5L19 7.5"></path></svg>';

    codeBlocks.forEach(function (codeBlock) {
        var pre = codeBlock;
        var copyBtn = document.createElement('button');
        copyBtn.className = 'code-copy-btn';
        copyBtn.type = 'button';
        copyBtn.setAttribute('aria-label', '复制代码');
        copyBtn.innerHTML = '<span class="code-copy-icon">' + ICON_COPY + '</span><span>复制</span>';

        copyBtn.addEventListener('click', async function () {
            var codeSource = codeBlock.querySelector('code') || codeBlock;
            var code = codeSource.textContent;
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(code);
                } else {
                    var textArea = document.createElement('textarea');
                    textArea.value = code;
                    textArea.style.position = 'fixed';
                    textArea.style.left = '-999999px';
                    document.body.appendChild(textArea);
                    textArea.select();
                    try {
                        document.execCommand('copy');
                    } catch (err) {
                        document.body.removeChild(textArea);
                        throw err;
                    }
                    document.body.removeChild(textArea);
                }
                flashToast('代码已复制', false);
                copyBtn.innerHTML = '<span class="code-copy-icon">' + ICON_DONE + '</span><span>已复制</span>';
                copyBtn.classList.add('is-done');
                setTimeout(function () {
                    copyBtn.innerHTML = '<span class="code-copy-icon">' + ICON_COPY + '</span><span>复制</span>';
                    copyBtn.classList.remove('is-done');
                }, 2000);
            } catch (error) {
                console.error('复制失败:', error);
                flashToast('复制失败，请手动选择', true);
            }
        });

        pre.appendChild(copyBtn);
        setTimeout(function () {
            copyBtn.classList.add('visible');
        }, 100);
    });
});
