/**
 * 代码复制功能
 *
 * 功能说明:
 *   - 为文章中的所有代码块添加复制按钮
 *   - 支持现代浏览器的 Clipboard API
 *   - 提供回退方案兼容旧浏览器（document.execCommand）
 *   - 显示复制成功/失败的 Toast 提示
 *
 * 兼容性:
 *   - Chrome 66+, Firefox 63+, Safari 13.1+, Edge 79+
 *   - 旧浏览器回退到 execCommand 方案
 *
 * 依赖: 无（原生 JavaScript）
 */

// Code copy functionality
document.addEventListener('DOMContentLoaded', function() {
    const codeBlocks = document.querySelectorAll('.post-content pre > code');

    // 创建复制成功提示
    const toast = document.createElement('div');
    toast.className = 'code-copy-toast';
    toast.textContent = '代码已复制！';
    document.body.appendChild(toast);

    codeBlocks.forEach(function(codeBlock) {
        const pre = codeBlock.parentElement;

        // 创建复制按钮
        const copyBtn = document.createElement('button');
        copyBtn.className = 'code-copy-btn';
        copyBtn.innerHTML = '<span>📋</span><span>复制</span>';
        copyBtn.setAttribute('aria-label', '复制代码');
        copyBtn.type = 'button';

        // 复制功能
        copyBtn.addEventListener('click', async function() {
            const code = codeBlock.textContent;

            try {
                // 优先使用现代 Clipboard API
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(code);
                } else {
                    // 回退方案（兼容旧浏览器）
                    const textArea = document.createElement('textarea');
                    textArea.value = code;
                    textArea.style.position = 'fixed';
                    textArea.style.left = '-999999px';
                    document.body.appendChild(textArea);
                    textArea.select();
                    try {
                        document.execCommand('copy');
                    } catch (err) {
                        console.error('复制失败:', err);
                        throw err;
                    }
                    document.body.removeChild(textArea);
                }

                // 显示成功提示
                toast.classList.add('show');
                copyBtn.innerHTML = '<span>✓</span><span>已复制</span>';

                // 2秒后恢复按钮
                setTimeout(() => {
                    toast.classList.remove('show');
                    copyBtn.innerHTML = '<span>📋</span><span>复制</span>';
                }, 2000);

            } catch (error) {
                console.error('复制失败:', error);
                toast.textContent = '复制失败，请手动选择';
                toast.style.backgroundColor = 'var(--error-color, #ef4444)';
                toast.classList.add('show');

                setTimeout(() => {
                    toast.classList.remove('show');
                    toast.textContent = '代码已复制！';
                    toast.style.backgroundColor = 'var(--success-color, #10b981)';
                }, 2000);
            }
        });

        // 将按钮添加到代码块
        pre.appendChild(copyBtn);

        // 初始显示按钮（提升可见性）
        setTimeout(() => {
            copyBtn.classList.add('visible');
        }, 100);
    });
});
