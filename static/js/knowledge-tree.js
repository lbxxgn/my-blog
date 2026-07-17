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
        if (localStorage.getItem('kb-sidebar-collapsed') === '1') {
            setCollapsed(true);
        }
    } catch (e) {}
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
              else alert((data && data.error) || '排序失败');
          })
          .catch(function(err) { alert('网络错误: ' + err); });
    });

    tree.addEventListener('click', function(e) {
        var toggle = e.target.closest('.kb-tree-toggle');
        if (!toggle) return;
        var li = toggle.closest('.kb-tree-node');
        var children = li && li.querySelector(':scope > .kb-tree-children');
        if (children) {
            children.classList.toggle('collapsed');
            toggle.textContent = children.classList.contains('collapsed') ? '▸' : '▾';
        }
    });
})();
