/**
 * 可复用语音输入（Web Speech API）
 * window.VoiceInput.attach(button, textarea) 挂载到「按钮 + textarea」组合。
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
            const message = '当前浏览器不支持语音输入，请用 Safari 打开，或使用 iPhone 键盘上的麦克风';
            button.classList.add('disabled');
            button.title = message;
            button.setAttribute('aria-label', message);
            button.addEventListener('click', function () {
                toast(message, 'error');
            });
            return null;
        }

        let recognition = null;
        let listening = false;
        let committedText = '';
        let interimText = '';
        let originalValue = '';
        let insertStart = 0;
        let insertEnd = 0;

        function render() {
            button.classList.toggle('recording', listening);
            button.setAttribute('aria-pressed', String(listening));
            button.setAttribute('aria-label', listening ? '停止语音输入' : '开始语音输入');
            button.title = listening ? '停止语音输入' : '语音输入：边说边写入正文';
            textarea.dispatchEvent(new CustomEvent('voiceinputstatechange', {
                detail: { listening: listening }
            }));
        }

        function updateText() {
            const transcript = committedText + interimText;
            textarea.value = originalValue.slice(0, insertStart) + transcript + originalValue.slice(insertEnd);
            const caret = insertStart + transcript.length;
            textarea.selectionStart = textarea.selectionEnd = caret;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }

        function start() {
            originalValue = textarea.value;
            insertStart = textarea.selectionStart != null ? textarea.selectionStart : originalValue.length;
            insertEnd = textarea.selectionEnd != null ? textarea.selectionEnd : insertStart;
            committedText = '';
            interimText = '';

            recognition = new Recognition();
            recognition.lang = 'zh-CN';
            recognition.interimResults = true;
            recognition.continuous = true;

            recognition.onresult = function (event) {
                let confirmed = '';
                let interim = '';
                for (let i = 0; i < event.results.length; i++) {
                    const result = event.results[i];
                    if (result.isFinal) {
                        confirmed += result[0].transcript;
                    } else {
                        interim += result[0].transcript;
                    }
                }
                committedText = confirmed;
                interimText = interim;
                updateText();
            };

            recognition.onerror = function (event) {
                if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                    toast('请允许 Safari 使用麦克风，或改用 iPhone 键盘上的麦克风', 'error');
                } else if (event.error === 'no-speech') {
                    toast('没有听到声音，请靠近麦克风后再试', 'error');
                } else if (event.error !== 'aborted') {
                    toast('语音识别出错：' + event.error, 'error');
                }
            };

            recognition.onend = function () {
                listening = false;
                recognition = null;
                render();
            };

            try {
                recognition.start();
                listening = true;
                render();
            } catch (e) {
                recognition = null;
                listening = false;
                render();
                toast('语音输入启动失败，请使用 Safari 或 iPhone 键盘上的麦克风', 'error');
            }
        }

        function stop() {
            if (recognition && listening) {
                try { recognition.stop(); } catch (e) { /* 已停止时无需处理 */ }
            }
        }

        button.setAttribute('aria-pressed', 'false');
        button.setAttribute('aria-label', '开始语音输入');
        button.title = '语音输入：边说边写入正文';
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

    window.VoiceInput = {
        attach: attach,
        stop: function (textarea) {
            const api = stateMap.get(textarea);
            if (api) api.stop();
        }
    };
})();
