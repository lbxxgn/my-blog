/* 知识库文档 TOC 生成 + 滚动高亮 + 目录树折叠 */
(function () {
  'use strict';

  // --- TOC 生成 ---
  var body = document.getElementById('kb-article-body');
  var tocNav = document.getElementById('kb-toc-nav');
  var tocAside = document.getElementById('kb-toc');

  if (body && tocNav) {
    var headings = body.querySelectorAll('h1, h2, h3');
    if (headings.length < 2) {
      if (tocAside) tocAside.style.display = 'none';
    } else {
      var frag = document.createDocumentFragment();
      var ul = document.createElement('ul');
      headings.forEach(function (h, i) {
        if (!h.id) h.id = 'kb-toc-head-' + i;
        var li = document.createElement('li');
        var a = document.createElement('a');
        a.href = '#' + h.id;
        a.textContent = h.textContent;
        var level = parseInt(h.tagName.charAt(1), 10);
        if (level === 2) li.className = 'toc-l2';
        if (level === 3) li.className = 'toc-l3';
        li.appendChild(a);
        ul.appendChild(li);
      });
      frag.appendChild(ul);
      tocNav.appendChild(frag);

      // 滚动高亮
      var links = tocNav.querySelectorAll('a');
      var headingEls = Array.prototype.slice.call(headings);
      if ('IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              links.forEach(function (l) { l.classList.remove('active'); });
              var active = tocNav.querySelector('a[href="#' + entry.target.id + '"]');
              if (active) active.classList.add('active');
            }
          });
        }, { rootMargin: '0px 0px -70% 0px' });
        headingEls.forEach(function (h) { observer.observe(h); });
      }
    }
  }

  // --- 目录树折叠 ---
  document.querySelectorAll('.kb-tree-toggle').forEach(function (toggle) {
    toggle.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var node = toggle.closest('.kb-tree-node');
      if (!node) return;
      var children = node.querySelector(':scope > .kb-tree-children');
      if (!children) return;
      var collapsed = children.style.display === 'none';
      children.style.display = collapsed ? '' : 'none';
      toggle.textContent = collapsed ? (children.children.length ? '▾' : '•') : '▸';
    });
  });
})();
