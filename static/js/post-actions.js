/**
 * 文章页的三个交互（原 templates/post.html 内联脚本）
 *
 * 1. 「沉淀到知识库」弹窗
 * 2. 「导师点评」弹窗（生成 → 复制 / 发表为评论）
 * 3. 评论区 AJAX 提交
 *
 * 需要页面提供 `#post-client-config`（data-* 里放 URL、文章 id/title），
 * 这样脚本本身不再依赖 Jinja 渲染，可以走 CSP 的 script-src 'self'。
 */
(function () {
    'use strict';

    function config() {
        var el = document.getElementById('post-client-config');
        return el ? el.dataset : {};
    }

    function toast(message, type) {
        if (typeof window.showAppToast === 'function') {
            window.showAppToast(message, type || 'success');
        }
    }

    // ---------------------------------------------------------------- 沉淀到知识库

    function initPrecipitate(cfg) {
        var btn = document.getElementById('precipitate-btn');
        if (!btn) return;
        var modal = document.getElementById('precipitate-modal');
        var cancelBtn = document.getElementById('precipitate-cancel');
        var confirmBtn = document.getElementById('precipitate-confirm');
        var catSelect = document.getElementById('precipitate-category');

        btn.addEventListener('click', function () { modal.style.display = 'flex'; });
        cancelBtn.addEventListener('click', function () { modal.style.display = 'none'; });
        modal.addEventListener('click', function (e) { if (e.target === modal) modal.style.display = 'none'; });

        confirmBtn.addEventListener('click', function () {
            var catId = catSelect.value;
            if (!catId) { toast('请选择目标目录', 'error'); return; }
            confirmBtn.disabled = true;
            confirmBtn.textContent = '沉淀中...';
            AppHttp.postJSON(cfg.precipitateUrl, { category_id: parseInt(catId, 10) }, { silent: true })
                .then(function (data) {
                    if (data.success) {
                        toast('已沉淀为知识库文档');
                        window.open(data.redirect, '_blank');
                        modal.style.display = 'none';
                    } else {
                        toast('失败: ' + (data.error || '未知错误'), 'error');
                    }
                })
                .catch(function (error) {
                    toast('沉淀失败：' + AppHttp.describe(error), 'error');
                })
                .finally(function () {
                    confirmBtn.disabled = false;
                    confirmBtn.textContent = '确认沉淀';
                });
        });
    }

    // ---------------------------------------------------------------- 导师点评

    function initMentor(cfg) {
        var btn = document.getElementById('mentor-btn');
        if (!btn) return;
        var modal = document.getElementById('mentor-modal');
        var resultEl = document.getElementById('mentor-result');
        var publishBtn = document.getElementById('mentor-publish');
        var copyBtn = document.getElementById('mentor-copy');
        var closeBtn = document.getElementById('mentor-close');
        var currentComment = '';
        var loaded = false;

        closeBtn.addEventListener('click', function () { modal.style.display = 'none'; });
        modal.addEventListener('click', function (e) { if (e.target === modal) modal.style.display = 'none'; });

        btn.addEventListener('click', function () {
            modal.style.display = 'flex';
            if (loaded) return;
            resultEl.textContent = '导师正在阅读你的文章...';
            btn.disabled = true;
            var postContent = document.querySelector('.post-content');
            AppHttp.postJSON(cfg.mentorUrl, {
                title: cfg.postTitle || '',
                content: postContent ? postContent.innerText.slice(0, 6000) : '',
                post_id: parseInt(cfg.postId, 10) || null
            }, { silent: true })
                .then(function (data) {
                    if (data.success) {
                        currentComment = data.comment;
                        loaded = true;
                        resultEl.textContent = data.comment;
                        publishBtn.disabled = false;
                        copyBtn.disabled = false;
                    } else {
                        resultEl.textContent = '生成失败：' + (data.error || '未知错误');
                    }
                })
                .catch(function (error) {
                    resultEl.textContent = '生成失败：' + AppHttp.describe(error);
                })
                .finally(function () { btn.disabled = false; });
        });

        copyBtn.addEventListener('click', function () {
            if (!currentComment) return;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(currentComment)
                    .then(function () { toast('已复制'); })
                    .catch(function () { toast('复制失败，请手动选择文本', 'error'); });
            } else {
                toast('当前浏览器不支持一键复制', 'error');
            }
        });

        publishBtn.addEventListener('click', function () {
            if (!currentComment) return;
            var content = currentComment.length > 990 ? currentComment.slice(0, 990) + '……' : currentComment;
            publishBtn.disabled = true;
            publishBtn.textContent = '发表中...';
            AppHttp.postForm(cfg.commentUrl, {
                author_name: 'AI 导师',
                author_email: '',
                content: content
            }, { silent: true })
                .then(function () {
                    toast('点评已发表到评论区');
                    window.location.reload();
                })
                .catch(function (error) {
                    toast('发表失败：' + AppHttp.describe(error), 'error');
                    publishBtn.disabled = false;
                    publishBtn.textContent = '发表为评论';
                });
        });
    }

    // ---------------------------------------------------------------- 评论区

    function initComments() {
        var section = document.getElementById('comments');
        var form = document.querySelector('.comment-form');
        if (!form) return;

        var trigger = section ? section.querySelector('.comments-trigger') : null;
        var countEl = section ? section.querySelector('.comments-count') : null;
        var body = document.getElementById('comments-body');

        function setExpanded(expanded) {
            if (!section) return;
            section.classList.toggle('collapsed', !expanded);
            if (trigger) trigger.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        }

        if (trigger && body) {
            var toggle = function () { setExpanded(section.classList.contains('collapsed')); };
            trigger.addEventListener('click', toggle);
            trigger.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
            });
        }

        function nowLabel() {
            var d = new Date();
            function p(n) { return n < 10 ? '0' + n : '' + n; }
            return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
        }

        function ensureList() {
            var list = body.querySelector('.comments-list');
            if (!list) {
                list = document.createElement('div');
                list.className = 'comments-list';
                body.insertBefore(list, body.firstChild);
            }
            return list;
        }

        function appendComment(name, content) {
            var head = document.createElement('div');
            head.className = 'comment-header';
            var author = document.createElement('strong');
            author.textContent = name;
            var date = document.createElement('span');
            date.className = 'comment-date';
            date.textContent = nowLabel();
            head.appendChild(author);
            head.appendChild(date);

            var text = document.createElement('div');
            text.className = 'comment-content';
            text.textContent = content;

            var wrap = document.createElement('div');
            wrap.className = 'comment';
            wrap.appendChild(head);
            wrap.appendChild(text);
            ensureList().appendChild(wrap);

            var count = Number((section && section.dataset.count) || 0) + 1;
            if (section) section.dataset.count = String(count);
            if (countEl) countEl.textContent = ' (' + count + ')';
            return wrap;
        }

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var submitBtn = form.querySelector('button[type="submit"]');
            var originalText = submitBtn ? submitBtn.textContent : '';
            var contentField = form.querySelector('textarea[name="content"]');
            var nameField = form.querySelector('input[name="author_name"]');
            var content = contentField ? contentField.value.trim() : '';

            if (!content) {
                toast('评论内容不能为空', 'error');
                if (contentField) contentField.focus();
                return;
            }

            if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = '发送中...'; }
            AppHttp.request(form.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
                body: new FormData(form),
                // 失败时要读取服务端返回的 error 文案
                acceptErrors: true,
                silent: true
            })
                .then(function (response) {
                    return response.json().catch(function () { return {}; })
                        .then(function (data) { return { ok: response.ok, data: data }; });
                })
                .then(function (res) {
                    if (res.ok && res.data.success) {
                        var name = (nameField && nameField.value.trim()) || form.dataset.authorName || '我';
                        var node = appendComment(name, content);
                        setExpanded(true);
                        if (contentField) contentField.value = '';
                        if (node.scrollIntoView) node.scrollIntoView({ block: 'nearest' });
                        toast('评论已发布');
                        return;
                    }
                    toast(res.data.error || '评论提交失败，请稍后重试', 'error');
                })
                .catch(function (error) {
                    toast('网络错误，评论未发送，内容已保留（' + AppHttp.describe(error) + '）', 'error');
                })
                .finally(function () {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = originalText;
                    }
                });
        });
    }

    function init() {
        var cfg = config();
        initPrecipitate(cfg);
        initMentor(cfg);
        initComments();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
