/**
 * 站点设置 - 图标裁剪
 *
 * 上传图片后通过拖动选框选择图片中的一块正方形区域，提交时在本地裁切出
 * 正方形 PNG 一并上传；未选择新图片时，则基于服务端保留的原图重新裁剪。
 */
(function () {
    'use strict';

    var form = document.getElementById('siteIconForm');
    if (!form) {
        return;
    }

    var fileInput = document.getElementById('icon');
    var croppedInput = document.getElementById('siteIconCropped');
    var cropField = document.getElementById('siteIconCrop');
    var editor = document.getElementById('iconCropEditor');
    var stage = document.getElementById('iconCropStage');
    var image = document.getElementById('iconCropImage');
    var box = document.getElementById('iconCropBox');
    var sizeLabel = document.getElementById('iconCropSizeLabel');
    var centerBtn = document.getElementById('iconCropCenter');
    var submitBtn = document.getElementById('siteIconSubmit');
    var fileHint = document.getElementById('siteIconFileHint');

    var hasSource = form.dataset.hasSource === '1';
    var sourceUrl = form.dataset.sourceUrl || '';
    // 显示层选区最小边长（px）
    var MIN_DISPLAY_SIDE = 24;
    // 提交给服务端的裁切图最大边长
    var OUTPUT_MAX = 1024;
    // 选区实际像素下限，与服务端校验保持一致
    var MIN_OUTPUT_SIDE = 64;
    // 裁剪区显示尺寸限制
    var MAX_DISPLAY_HEIGHT = 460;
    var MAX_UPSCALE = 3;

    var state = {
        loaded: false,
        naturalW: 0,
        naturalH: 0,
        crop: null, // 归一化到 0~1 的 {x, y, w, h}
        drag: null,
        objectUrl: null,
        isNewFile: false
    };

    function stageSize() {
        return { w: image.clientWidth, h: image.clientHeight };
    }

    function layout() {
        if (!state.loaded) {
            return;
        }
        var stageWidth = stage.clientWidth;
        if (!stageWidth) {
            return;
        }
        // 按可用宽度和最大高度等比缩放，小图允许适度放大便于选点
        var scale = Math.min(
            stageWidth / state.naturalW,
            MAX_DISPLAY_HEIGHT / state.naturalH,
            MAX_UPSCALE
        );
        image.style.width = Math.max(1, Math.floor(state.naturalW * scale)) + 'px';
        image.style.height = Math.max(1, Math.floor(state.naturalH * scale)) + 'px';
        render();
    }

    function cropToPx(crop) {
        var s = stageSize();
        return {
            x: crop.x * s.w,
            y: crop.y * s.h,
            w: crop.w * s.w,
            h: crop.h * s.h
        };
    }

    function pxToCrop(rect) {
        var s = stageSize();
        return {
            x: rect.x / s.w,
            y: rect.y / s.h,
            w: rect.w / s.w,
            h: rect.h / s.h
        };
    }

    function defaultCrop() {
        var nw = state.naturalW || 1;
        var nh = state.naturalH || 1;
        // 默认留出边距，方便在选区外拖动重新框选
        var side = Math.min(nw, nh) * 0.9;
        var w = side / nw;
        var h = side / nh;
        return { x: (1 - w) / 2, y: (1 - h) / 2, w: w, h: h };
    }

    function normalizeCrop(raw) {
        if (!raw || typeof raw !== 'object') {
            return null;
        }
        var rect = {
            x: Number(raw.x),
            y: Number(raw.y),
            w: Number(raw.w),
            h: Number(raw.h)
        };
        if (!isFinite(rect.x) || !isFinite(rect.y) || !isFinite(rect.w) || !isFinite(rect.h)) {
            return null;
        }
        if (rect.w <= 0 || rect.h <= 0 || rect.x < 0 || rect.y < 0) {
            return null;
        }
        if (rect.x + rect.w > 1.0001 || rect.y + rect.h > 1.0001) {
            return null;
        }
        // 归一化后宽高比例应等于图片宽高比，否则说明选区不是正方形
        var nw = state.naturalW;
        var nh = state.naturalH;
        if (nw && nh) {
            var sideX = rect.w * nw;
            var sideY = rect.h * nh;
            if (Math.abs(sideX - sideY) > Math.max(2, sideX * 0.02)) {
                return null;
            }
        }
        return rect;
    }

    function render() {
        if (!state.loaded || !state.crop) {
            return;
        }
        var s = stageSize();
        if (!s.w || !s.h) {
            return;
        }
        var rect = cropToPx(state.crop);
        box.style.left = rect.x + 'px';
        box.style.top = rect.y + 'px';
        box.style.width = rect.w + 'px';
        box.style.height = rect.h + 'px';

        var sidePx = Math.round(Math.min(rect.w * (state.naturalW / s.w), rect.h * (state.naturalH / s.h)));
        sizeLabel.textContent = sidePx > 0
            ? '选区 ' + sidePx + ' × ' + sidePx + ' px'
            : '拖动选框选择区域';
        cropField.value = JSON.stringify(state.crop);
    }

    function applyPx(x, y, side) {
        var s = stageSize();
        if (!s.w || !s.h) {
            return;
        }
        side = Math.min(Math.max(side, MIN_DISPLAY_SIDE), Math.min(s.w, s.h));
        x = Math.min(Math.max(x, 0), s.w - side);
        y = Math.min(Math.max(y, 0), s.h - side);
        state.crop = pxToCrop({ x: x, y: y, w: side, h: side });
        render();
    }

    function imagePoint(event) {
        var rect = image.getBoundingClientRect();
        return {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
        };
    }

    function clampPoint(point) {
        var s = stageSize();
        return {
            x: Math.min(Math.max(point.x, 0), s.w),
            y: Math.min(Math.max(point.y, 0), s.h)
        };
    }

    function startDrag(event, mode, handle) {
        if (!state.loaded) {
            return;
        }
        var rawPoint = imagePoint(event);
        var s = stageSize();
        if (mode === 'draw' &&
            (rawPoint.x < 0 || rawPoint.y < 0 || rawPoint.x > s.w || rawPoint.y > s.h)) {
            return;
        }
        event.preventDefault();
        var point = clampPoint(rawPoint);
        state.drag = {
            pointerId: event.pointerId,
            mode: mode,
            handle: handle,
            startPoint: point,
            startRect: cropToPx(state.crop),
            anchor: null
        };

        if (mode === 'resize') {
            var r = state.drag.startRect;
            state.drag.anchor = {
                nw: { x: r.x + r.w, y: r.y + r.h },
                ne: { x: r.x, y: r.y + r.h },
                sw: { x: r.x + r.w, y: r.y },
                se: { x: r.x, y: r.y }
            }[handle];
        }
        if (mode === 'draw') {
            state.drag.anchor = point;
        }

        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
        window.addEventListener('pointercancel', onPointerUp);
    }

    function onPointerMove(event) {
        var drag = state.drag;
        if (!drag || (drag.pointerId !== undefined && event.pointerId !== drag.pointerId)) {
            return;
        }
        event.preventDefault();
        var point = clampPoint(imagePoint(event));
        var s = stageSize();

        if (drag.mode === 'move') {
            var dx = point.x - drag.startPoint.x;
            var dy = point.y - drag.startPoint.y;
            applyPx(drag.startRect.x + dx, drag.startRect.y + dy, drag.startRect.w);
            return;
        }

        if (drag.mode === 'resize') {
            var anchor = drag.anchor;
            var horizontal = drag.handle === 'ne' || drag.handle === 'se'
                ? point.x - anchor.x
                : anchor.x - point.x;
            var vertical = drag.handle === 'sw' || drag.handle === 'se'
                ? point.y - anchor.y
                : anchor.y - point.y;
            var side = Math.max(horizontal, vertical);
            var maxSide;
            var left;
            var top;
            switch (drag.handle) {
                case 'nw':
                    maxSide = Math.min(anchor.x, anchor.y);
                    break;
                case 'ne':
                    maxSide = Math.min(s.w - anchor.x, anchor.y);
                    break;
                case 'sw':
                    maxSide = Math.min(anchor.x, s.h - anchor.y);
                    break;
                default: // se
                    maxSide = Math.min(s.w - anchor.x, s.h - anchor.y);
                    break;
            }
            side = Math.min(side, maxSide);
            if (drag.handle === 'nw' || drag.handle === 'sw') {
                left = anchor.x - side;
            } else {
                left = anchor.x;
            }
            if (drag.handle === 'nw' || drag.handle === 'ne') {
                top = anchor.y - side;
            } else {
                top = anchor.y;
            }
            applyPx(left, top, side);
            return;
        }

        if (drag.mode === 'draw') {
            var anchorPt = drag.anchor;
            var drawSide = Math.max(
                Math.abs(point.x - anchorPt.x),
                Math.abs(point.y - anchorPt.y)
            );
            drawSide = Math.min(drawSide, s.w - anchorPt.x, s.h - anchorPt.y);
            applyPx(anchorPt.x, anchorPt.y, drawSide);
        }
    }

    function onPointerUp() {
        state.drag = null;
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('pointerup', onPointerUp);
        window.removeEventListener('pointercancel', onPointerUp);
    }

    function bindStage() {
        stage.addEventListener('pointerdown', function (event) {
            if (event.target === box || box.contains(event.target)) {
                return;
            }
            startDrag(event, 'draw');
        });

        box.addEventListener('pointerdown', function (event) {
            var handle = event.target.getAttribute && event.target.getAttribute('data-handle');
            if (handle) {
                startDrag(event, 'resize', handle);
            } else {
                startDrag(event, 'move');
            }
        });
    }

    function loadImage(url, initialCrop) {
        editor.hidden = false;
        state.loaded = false;
        image.onload = function () {
            state.naturalW = image.naturalWidth;
            state.naturalH = image.naturalHeight;
            state.loaded = true;
            state.crop = normalizeCrop(initialCrop) || defaultCrop();
            layout();
        };
        image.onerror = function () {
            state.loaded = false;
            editor.hidden = true;
            if (fileHint) {
                fileHint.textContent = '图片加载失败，请重新选择一张图片。';
            }
        };
        image.src = url;
    }

    function dataUrlToBlob(dataUrl) {
        var parts = dataUrl.split(',');
        var mime = (parts[0].match(/:(.*?);/) || [])[1] || 'image/png';
        var binary = atob(parts[1]);
        var length = binary.length;
        var bytes = new Uint8Array(length);
        for (var i = 0; i < length; i += 1) {
            bytes[i] = binary.charCodeAt(i);
        }
        return new Blob([bytes], { type: mime });
    }

    function buildCroppedBlob() {
        if (!state.loaded || !state.crop || !state.naturalW || !state.naturalH) {
            return null;
        }
        var rect = state.crop;
        var sx = Math.round(rect.x * state.naturalW);
        var sy = Math.round(rect.y * state.naturalH);
        var side = Math.round(Math.min(rect.w * state.naturalW, rect.h * state.naturalH));
        side = Math.min(side, state.naturalW - sx, state.naturalH - sy);
        if (side < MIN_OUTPUT_SIDE) {
            return null;
        }
        var output = Math.min(OUTPUT_MAX, side);
        var canvas = document.createElement('canvas');
        canvas.width = output;
        canvas.height = output;
        var ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(image, sx, sy, side, side, 0, 0, output, output);
        return dataUrlToBlob(canvas.toDataURL('image/png'));
    }

    function attachCroppedFile(blob) {
        var file = new File([blob], 'site-icon-crop.png', { type: 'image/png' });
        var transfer = new DataTransfer();
        transfer.items.add(file);
        croppedInput.files = transfer.files;
    }

    bindStage();

    if (centerBtn) {
        centerBtn.addEventListener('click', function () {
            if (!state.loaded) {
                return;
            }
            state.crop = defaultCrop();
            render();
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', function () {
            var file = fileInput.files && fileInput.files[0];
            if (!file) {
                return;
            }
            if (file.type && file.type.indexOf('image/') !== 0) {
                if (fileHint) {
                    fileHint.textContent = '请选择图片文件。';
                }
                return;
            }
            state.isNewFile = true;
            if (state.objectUrl) {
                URL.revokeObjectURL(state.objectUrl);
            }
            state.objectUrl = URL.createObjectURL(file);
            if (fileHint) {
                fileHint.textContent = '拖动选框选择要作为图标的一块区域，然后点击上传。';
            }
            if (submitBtn) {
                submitBtn.textContent = '上传并应用';
            }
            // 新图片默认取居中的最大正方形
            loadImage(state.objectUrl, null);
        });
    }

    form.addEventListener('submit', function (event) {
        if (!state.loaded || !state.crop) {
            // 没有可裁剪的图片：若也未选择新文件，交给服务端按原图居中裁切
            return;
        }
        var blob = buildCroppedBlob();
        if (!blob) {
            event.preventDefault();
            if (fileHint) {
                fileHint.textContent = '选区太小（至少 ' + MIN_OUTPUT_SIDE + ' 像素），请重新选择区域。';
            }
            return;
        }
        try {
            attachCroppedFile(blob);
        } catch (err) {
            event.preventDefault();
            if (fileHint) {
                fileHint.textContent = '当前浏览器不支持本地裁剪，请更换浏览器后重试。';
            }
            return;
        }
        cropField.value = JSON.stringify(state.crop);
    });

    window.addEventListener('resize', layout);

    if (hasSource && sourceUrl) {
        var savedCrop = null;
        try {
            savedCrop = JSON.parse(cropField.value || 'null');
        } catch (err) {
            savedCrop = null;
        }
        loadImage(sourceUrl, savedCrop);
    }
})();
