// 知识库页面：侧边栏折叠 + 分类树拖拽排序（由 base.html 内联 JS 外置而来）
(function() {
    var sidebar = document.querySelector('.kb-layout > .kb-sidebar');
    if (!sidebar) return;
    var layout = sidebar.closest('.kb-layout');
    var header = sidebar.querySelector('.kb-sidebar-header');
    if (!header || !layout) return;

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'kb-sidebar-toggle';
    toggle.title = '折叠目录';
    toggle.setAttribute('aria-label', '折叠目录');
    toggle.innerHTML = '◀';
    header.appendChild(toggle);

    function setCollapsed(collapsed) {
        sidebar.classList.toggle('collapsed', collapsed);
        layout.classList.toggle('sidebar-collapsed', collapsed);
        toggle.title = collapsed ? '展开目录' : '折叠目录';
        toggle.setAttribute('aria-label', collapsed ? '展开目录' : '折叠目录');
        try { localStorage.setItem('kb-sidebar-collapsed', collapsed ? '1' : '0'); } catch (e) {}
    }

    toggle.addEventListener('click', function() {
        setCollapsed(!sidebar.classList.contains('collapsed'));
    });

    try {
        var stored = localStorage.getItem('kb-sidebar-collapsed');
        if (stored === '1' || (stored === null && window.innerWidth <= 768)) {
            setCollapsed(true);
        }
    } catch (e) {}
})();

// 目录重命名
(function() {
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('.kb-rename-cat');
        if (!btn) return;
        var tree = document.querySelector('.kb-tree');
        var csrf = tree && tree.dataset.csrf;
        if (!csrf) return;
        var name = window.prompt('重命名目录', btn.dataset.catName || '');
        if (!name || !name.trim() || name.trim() === btn.dataset.catName) return;
        var fd = new FormData();
        fd.append('name', name.trim());
        fd.append('csrf_token', csrf);
        fetch('/knowledge/category/' + btn.dataset.catId + '/rename', {
            method: 'POST', body: fd, headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).then(function(r){ return r.json(); }).then(function(data) {
            if (!data.success) throw new Error(data.error || '重命名失败');
            location.reload();
        }).catch(function(err) { alert(err.message || '重命名失败'); });
    });
})();

(function() {
    var tree = document.querySelector('.kb-tree');
    if (!tree || !tree.dataset.csrf) return;
    var csrf = tree.dataset.csrf;
    var draggedEl = null;

    function closestItem(el) {
        return el && el.closest('.kb-tree-item');
    }

    function clearIndicators() {
        document.querySelectorAll('.kb-tree-item.drop-before, .kb-tree-item.drop-after, .kb-tree-item.drop-inside')
            .forEach(function(item) {
                item.classList.remove('drop-before', 'drop-after', 'drop-inside');
            });
    }

    function getDropPosition(evt, item) {
        var rect = item.getBoundingClientRect();
        var y = evt.clientY - rect.top;
        if (y < rect.height * 0.25) return 'before';
        if (y > rect.height * 0.75) return 'after';
        return 'inside';
    }

    function siblings(item) {
        var li = item.closest('.kb-tree-node');
        if (!li || !li.parentElement) return [];
        return Array.from(li.parentElement.children)
            .map(function(child) { return child.querySelector('.kb-tree-item'); })
            .filter(Boolean);
    }

    function computeMove(targetItem, position, draggedId) {
        var newParentId = null;
        var newSortOrder = 0;
        if (position === 'inside') {
            newParentId = targetItem.dataset.catId;
            var li = targetItem.closest('.kb-tree-node');
            var childrenUl = li && li.querySelector(':scope > .kb-tree-children');
            var childItems = childrenUl
                ? Array.from(childrenUl.children)
                    .map(function(c) { return c.querySelector('.kb-tree-item'); })
                    .filter(Boolean)
                : [];
            if (childItems.length) {
                var max = Math.max.apply(null, childItems.map(function(i) {
                    return Number(i.dataset.sortOrder) || 0;
                }));
                newSortOrder = max + 1000;
            } else {
                newSortOrder = 0;
            }
        } else {
            var sib = siblings(targetItem);
            var targetIdx = sib.indexOf(targetItem);
            var insertIdx = position === 'before' ? targetIdx : targetIdx + 1;
            var list = sib.filter(function(i) { return i.dataset.catId !== draggedId; });
            var prev = list[insertIdx - 1];
            var next = list[insertIdx];
            var prevOrder = prev ? (Number(prev.dataset.sortOrder) || 0) : null;
            var nextOrder = next ? (Number(next.dataset.sortOrder) || 0) : null;
            if (prevOrder === null && nextOrder === null) newSortOrder = 0;
            else if (prevOrder === null) newSortOrder = nextOrder - 1000;
            else if (nextOrder === null) newSortOrder = prevOrder + 1000;
            else newSortOrder = (prevOrder + nextOrder) / 2;
            newParentId = targetItem.dataset.parentId || null;
        }
        return { parentId: newParentId, sortOrder: Math.round(newSortOrder) };
    }

    tree.addEventListener('dragstart', function(e) {
        if (!e.target.closest('.kb-tree-drag-handle')) {
            e.preventDefault();
            return;
        }
        draggedEl = closestItem(e.target);
        if (!draggedEl) { e.preventDefault(); return; }
        e.dataTransfer.effectAllowed = 'move';
        try { e.dataTransfer.setData('text/plain', draggedEl.dataset.catId); } catch (err) {}
        draggedEl.classList.add('dragging');
    });

    tree.addEventListener('dragend', function() {
        if (draggedEl) draggedEl.classList.remove('dragging');
        draggedEl = null;
        clearIndicators();
    });

    tree.addEventListener('dragover', function(e) {
        e.preventDefault();
        var target = closestItem(e.target);
        if (!target || target === draggedEl) { clearIndicators(); return; }
        if (draggedEl && draggedEl.contains(target)) { clearIndicators(); return; }
        var pos = getDropPosition(e, target);
        clearIndicators();
        target.classList.add('drop-' + pos);
    });

    tree.addEventListener('drop', function(e) {
        e.preventDefault();
        clearIndicators();
        var target = closestItem(e.target);
        if (!target || target === draggedEl) return;
        if (draggedEl && draggedEl.contains(target)) return;
        var draggedId;
        try { draggedId = e.dataTransfer.getData('text/plain'); } catch (err) { return; }
        if (!draggedId) return;
        var pos = getDropPosition(e, target);
        var info = computeMove(target, pos, draggedId);
        var fd = new FormData();
        fd.append('csrf_token', csrf);
        fd.append('type', 'category');
        fd.append('id', draggedId);
        fd.append('parent_id', info.parentId || '');
        fd.append('sort_order', String(info.sortOrder));
        fetch('/knowledge/reorder', {
            method: 'POST',
            body: fd,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        }).then(function(r) { return r.json(); })
          .then(function(data) {
              if (data && data.success) location.reload();
              else (window.showAppToast || alert)((data && data.error) || '排序失败', 'error');
          })
          .catch(function(err) { (window.showAppToast || alert)('网络错误: ' + err, 'error'); });
    });

    tree.addEventListener('click', function(e) {
        var toggle = e.target.closest('.kb-tree-toggle');
        if (!toggle) return;
        e.preventDefault();
        var li = toggle.closest('.kb-tree-node');
        if (!li) return;
        var groups = Array.from(li.querySelectorAll(':scope > .kb-tree-children, :scope > .kb-tree-docs'));
        if (!groups.length) return;
        var shouldExpand = groups.some(function(group) { return group.classList.contains('collapsed'); });
        groups.forEach(function(group) { group.classList.toggle('collapsed', !shouldExpand); });
        toggle.textContent = shouldExpand ? '▾' : '▸';
    });

    // 默认折叠所有分支，但自动展开当前浏览文档/目录所在的父级路径
    function expandActivePath() {
        var active = tree.querySelector('.kb-tree-doc.active, .kb-tree-item.active');
        if (!active) return;
        var parentUl = active.closest('.kb-tree-docs, .kb-tree-children');
        while (parentUl) {
            parentUl.classList.remove('collapsed');
            var parentNode = parentUl.closest('.kb-tree-node');
            var parentToggle = parentNode && parentNode.querySelector(':scope > .kb-tree-item .kb-tree-toggle');
            if (parentToggle) parentToggle.textContent = '▾';
            parentUl = parentNode ? parentNode.parentElement.closest('.kb-tree-docs, .kb-tree-children') : null;
        }
    }
    expandActivePath();
})();
