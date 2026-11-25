/**
 * 统一的 HTTP 请求封装（FE-7）
 *
 * 之前 45 处 `fetch()` 分散在 14 个脚本里：只有 1 处带超时、只有一半判断
 * `response.ok`、401/500 的处理各写各的。这里统一成三件事：
 *
 *   1. 默认 20s 超时，可用 `timeout: 0` 关闭；传入 `signal` 可与页面自身逻辑合并取消。
 *   2. `!response.ok` 一律抛 `AppHttp.HttpError`（带 `status`），不再靠调用方记得判断。
 *   3. 失败默认弹一次提示（网络异常 / 超时 / 401 未登录 / 403 / 404 / 429 / 5xx），
 *      调用方自己会提示时传 `silent: true`；需要自行读取错误响应正文时传 `acceptErrors: true`。
 *
 * 常用入口：
 *   AppHttp.request(url, options)          -> Response（需要 headers / status 时用）
 *   AppHttp.json(url, options)             -> 解析后的 JSON
 *   AppHttp.postJSON(url, data, options)   -> POST JSON（自动带 CSRF 头）
 *   AppHttp.postForm(url, data, options)   -> POST x-www-form-urlencoded（自动带 CSRF 头）
 *   AppHttp.getCsrfToken()                 -> 从 <meta name="csrf_token"> 读取
 *   AppHttp.describe(error)                -> 中文提示文案
 *   AppHttp.notify(error)                  -> 用 showAppToast 弹提示
 */
(function (global) {
    'use strict';

    var DEFAULT_TIMEOUT = 20000;

    class HttpError extends Error {
        constructor(message, details) {
            super(message);
            this.name = 'HttpError';
            details = details || {};
            this.status = details.status || 0;
            this.url = details.url || '';
            this.response = details.response || null;
            this.cancelled = Boolean(details.cancelled);
            if (details.cause) {
                this.cause = details.cause;
            }
        }
    }

    function anySignal(signals) {
        if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.any === 'function') {
            return AbortSignal.any(signals);
        }
        var controller = new AbortController();
        signals.forEach(function (signal) {
            if (signal.aborted) {
                controller.abort(signal.reason);
                return;
            }
            signal.addEventListener('abort', function () {
                controller.abort(signal.reason);
            }, { once: true });
        });
        return controller.signal;
    }

    function statusMessage(status) {
        if (status === 401) return '登录状态已失效，请重新登录';
        if (status === 403) return '没有权限执行该操作';
        if (status === 404) return '请求的内容不存在';
        if (status === 413) return '文件太大，超出了服务器限制';
        if (status === 429) return '操作太频繁，请稍后再试';
        if (status >= 500) return '服务器出错了，请稍后重试';
        return '请求失败（HTTP ' + status + '）';
    }

    function notify(error) {
        var message = describe(error);
        if (typeof global.showAppToast === 'function') {
            global.showAppToast(message, 'error');
        } else if (global.console) {
            global.console.warn('[http]', message, error);
        }
    }

    function describe(error) {
        if (!error) return '未知错误';
        if (error instanceof HttpError) return error.message;
        if (error.name === 'AbortError') return '请求已取消';
        return error.message || '请求失败';
    }

    async function request(url, options) {
        options = options || {};
        var timeout = options.timeout === undefined ? DEFAULT_TIMEOUT : options.timeout;
        var silent = Boolean(options.silent);
        // 少数调用方需要读取错误响应的正文（例如表单校验失败时返回 HTML 片段）
        var acceptErrors = Boolean(options.acceptErrors);
        var externalSignal = options.signal || null;
        var init = Object.assign({}, options);
        delete init.timeout;
        delete init.silent;
        delete init.acceptErrors;
        delete init.signal;

        var controller = new AbortController();
        init.signal = externalSignal
            ? anySignal([controller.signal, externalSignal])
            : controller.signal;

        var timer = null;
        if (timeout > 0) {
            timer = setTimeout(function () {
                controller.abort();
            }, timeout);
        }

        try {
            var response = await fetch(url, init);
            if (!response.ok && !acceptErrors) {
                throw new HttpError(statusMessage(response.status), {
                    status: response.status,
                    url: url,
                    response: response
                });
            }
            return response;
        } catch (error) {
            if (error instanceof HttpError) {
                if (!silent) notify(error);
                throw error;
            }
            var cancelled = Boolean(externalSignal && externalSignal.aborted);
            var wrapped = new HttpError(
                cancelled ? '请求已取消' : '网络异常，请检查连接后重试',
                { url: url, cause: error, cancelled: cancelled }
            );
            // 调用方主动取消（翻页、关闭弹窗）不该打扰用户
            if (!silent && !cancelled) notify(wrapped);
            throw wrapped;
        } finally {
            if (timer) clearTimeout(timer);
        }
    }

    async function json(url, options) {
        var response = await request(url, options);
        if (response.status === 204) return null;
        try {
            return await response.json();
        } catch (error) {
            var wrapped = new HttpError('服务器返回的不是有效 JSON', {
                url: url,
                response: response,
                cause: error
            });
            if (!options || options.silent !== true) notify(wrapped);
            throw wrapped;
        }
    }

    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf_token"]');
        return meta ? meta.getAttribute('content') || '' : '';
    }

    function withJsonHeaders(options) {
        var init = Object.assign({}, options);
        init.headers = Object.assign(
            { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            init.headers || {}
        );
        if (init.csrf !== false) init.headers['X-CSRFToken'] = getCsrfToken();
        delete init.csrf;
        return init;
    }

    function postJSON(url, data, options) {
        var init = withJsonHeaders(options);
        init.method = init.method || 'POST';
        init.body = JSON.stringify(data === undefined ? {} : data);
        return json(url, init);
    }

    function postForm(url, data, options) {
        var init = Object.assign({}, options);
        init.method = init.method || 'POST';
        init.headers = Object.assign({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }, init.headers || {});
        if (init.csrf !== false) init.headers['X-CSRFToken'] = getCsrfToken();
        delete init.csrf;
        init.body = data instanceof URLSearchParams ? data : new URLSearchParams(data || {});
        return json(url, init);
    }

    global.AppHttp = {
        request: request,
        json: json,
        postJSON: postJSON,
        postForm: postForm,
        getCsrfToken: getCsrfToken,
        describe: describe,
        notify: notify,
        HttpError: HttpError
    };
})(window);
