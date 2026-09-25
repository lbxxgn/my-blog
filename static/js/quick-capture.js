/**
 * 快捷捕捉页 + 可复用语音输入（Web Speech API）
 *
 * window.VoiceInput.attach(button, textarea) 可挂载到任何
 * 「按钮 + textarea」组合上（移动端快速发布面板复用）。
 */
(function () {
    'use strict';

    function toast(message, type) {
        if (window.showAppToast) {
            window.showAppToast(message, type || 'success');
        }
    }

    const stateMap = new WeakMap();

    function attach(button, textarea) {
        if (!button || !textarea) return null;

        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!Recognition) {
            button.classList.add('disabled');
            button.title = '当前浏览器不支持语音输入，可换 Chrome/Edge';
            button.addEventListener('click', function () {
                toast('当前浏览器不支持语音输入，可换 Chrome/Edge', 'error');
            });
            return null;
        }

        let recognition = null;
        let listening = false;
        let committedText = '';      // 已确认的文本（本会话追加到光标处）
        let interimText = '';        // 识别中的临时文本

        function render() {
            button.classList.toggle('recording', listening);
        }

        function commitInterim() {
            if (!interimText) return;
            const start = textarea.selectionStart != null ? textarea.selectionStart : textarea.value.length;
            const end = textarea.selectionEnd != null ? textarea.selectionEnd : start;
            const insert = committedText + interimText;
            textarea.value = textarea.value.slice(0, start) + insert + textarea.value.slice(end);
            textarea.selectionStart = textarea.selectionEnd = start + insert.length;
            committedText = '';
            interimText = '';
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }

        function start() {
            recognition = new Recognition();
            recognition.lang = 'zh-CN';
            recognition.interimResults = true;
            recognition.continuous = true;

            recognition.onresult = function (event) {
                let interim = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const result = event.results[i];
                    if (result.isFinal) {
                        committedText += result[0].transcript;
                    } else {
                        interim += result[0].transcript;
                    }
                }
                interimText = interim;
                // 实时上屏：确认文本在光标处累计，临时文本用透明度覆盖显示
                const start = textarea.selectionStart != null ? textarea.selectionStart : textarea.value.length;
                const end = textarea.selectionEnd != null ? textarea.selectionEnd : start;
                const confirmed = committedText;
                const preview = confirmed + interimText;
                const before = textarea.value.slice(0, start);
                const after = textarea.value.slice(end);
                // 用 span 不可行（textarea），改用 overlay 预览层
                renderPreview(before, preview, after, Boolean(interimText));
                if (!interimText && committedText) {
                    commitInterim();
                }
            };

            recognition.onerror = function (event) {
                if (event.error === 'not-allowed') {
                    toast('请允许使用麦克风后再试', 'error');
                } else if (event.error !== 'aborted' && event.error !== 'no-speech') {
                    toast('语音识别出错：' + event.error, 'error');
                }
            };

            recognition.onend = function () {
                commitInterim();
                removePreview();
                listening = false;
                render();
            };

            try {
                recognition.start();
                listening = true;
                render();
            } catch (e) {
                listening = false;
                render();
            }
        }

        function stop() {
            if (recognition && listening) {
                try { recognition.stop(); } catch (e) { /* ignore */ }
            }
        }

        // ---- 临时结果预览层（textarea 上方，半透明显示识别中文字） ----
        let previewEl = null;
        function renderPreview(before, preview, after, isInterim) {
            if (!isInterim) { removePreview(); return; }
            if (!previewEl) {
                previewEl = document.createElement('div');
                previewEl.style.cssText = 'position:fixed;z-index:9999;pointer-events:none;' +
                    'background:var(--card-bg,#fff);border:1px solid var(--border-color,#e0e0e0);' +
                    'border-radius:8px;padding:6px 10px;font-size:14px;color:var(--text-color,#333);' +
                    'opacity:0.55;max-width:80vw;box-shadow:0 4px 12px rgba(0,0,0,0.12);';
                document.body.appendChild(previewEl);
            }
            previewEl.textContent = preview || '...';
            const rect = textarea.getBoundingClientRect();
            previewEl.style.left = Math.min(rect.left, window.innerWidth - 200) + 'px';
            previewEl.style.top = Math.max(8, rect.top - 44) + 'px';
            previewEl.style.display = 'block';
        }
        function removePreview() {
            if (previewEl) previewEl.style.display = 'none';
        }

        button.addEventListener('click', function () {
            if (listening) {
                stop();
            } else {
                start();
            }
        });

        const api = {
            stop: stop,
            isListening: function () { return listening; }
        };
        stateMap.set(textarea, api);
        return api;
    }

    window.VoiceInput = { attach: attach };

    // ---- 快捷捕捉页逻辑 ----
    document.addEventListener('DOMContentLoaded', function () {
        const titleEl = document.getElementById('qcTitle');
        const contentEl = document.getElementById('qcContent');
        if (!contentEl) return;

        const voiceBtn = document.getElementById('qcVoiceBtn');
        const voiceApi = attach(voiceBtn, contentEl);

        function getCsrf() {
            return window.getCsrfToken ? window.getCsrfToken() : '';
        }

        function postJSON(url, body) {
            return fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrf(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(body)
            });
        }

        function resetForm() {
            if (titleEl) titleEl.value = '';
            contentEl.value = '';
        }

        document.getElementById('qcSaveCard').addEventListener('click', function () {
            const content = contentEl.value.trim();
            if (!content) {
                toast('内容不能为空', 'error');
                contentEl.focus();
                return;
            }
            if (voiceApi && voiceApi.isListening()) voiceApi.stop();
            const btn = this;
            btn.disabled = true;
            postJSON('/knowledge_base/api/cards', {
                title: titleEl ? titleEl.value.trim() : '',
                content: content
            }).then(function (resp) {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            }).then(function () {
                toast('已存为卡片，可到知识库查看');
                resetForm();
            }).catch(function () {
                toast('保存失败，请重试', 'error');
            }).finally(function () {
                btn.disabled = false;
            });
        });

        document.getElementById('qcSaveNote').addEventListener('click', function () {
            const content = contentEl.value.trim();
            if (!content) {
                toast('内容不能为空', 'error');
                contentEl.focus();
                return;
            }
            if (voiceApi && voiceApi.isListening()) voiceApi.stop();
            const btn = this;
            btn.disabled = true;
            postJSON('/knowledge_base/quick-note', {
                title: titleEl ? titleEl.value.trim() : '',
                content: content
            }).then(function (resp) {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            }).then(function () {
                toast('已存为快速记事');
                resetForm();
            }).catch(function () {
                toast('保存失败，请重试', 'error');
            }).finally(function () {
                btn.disabled = false;
            });
        });
    });
})();
