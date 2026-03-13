# UX Enhancements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 5 user experience enhancements: keyboard shortcuts with hints, server-side draft sync with multi-device support, automatic image compression, static asset auto-versioning, and breadcrumb navigation.

**Architecture:** Progressive enhancement strategy - each feature is independent, can be implemented and tested separately. Uses existing Flask+SQLite architecture, extends existing modules (ShortcutHandler, image_processor), adds new database tables (drafts, optimized_images), follows blueprint pattern for routes.

**Tech Stack:** Flask 3.0, SQLite, Vanilla JavaScript, Python threading, PIL/Pillow for image processing, Jinja2 templates.

**Spec Document:** `docs/superpowers/specs/2026-03-13-ux-enhancements-design.md`

---

## Phase 1: Low-Risk Quick Wins (1 week)

### Task 1: Keyboard Shortcuts Enhancement

**Files:**
- Modify: `static/js/shortcuts.js`
- Modify: `static/css/style.css`
- Modify: `templates/base.html`

- [ ] **Step 1: Add ShortcutHint component class to shortcuts.js**

Add at end of `static/js/shortcuts.js`:

```javascript
/**
 * 快捷键提示组件
 */
class ShortcutHint {
    constructor() {
        this.hintElement = null;
        this.autoFadeTimer = null;
        this.init();
    }

    init() {
        // 检查用户是否已关闭提示
        if (sessionStorage.getItem('shortcutHintDismissed') === 'true') {
            return;
        }

        this.createHintElement();
        this.show();
    }

    createHintElement() {
        const hint = document.createElement('div');
        hint.id = 'shortcutHint';
        hint.className = 'shortcut-hint';
        hint.innerHTML = `
            <div class="hint-header">
                <span>⌨️ 快捷键提示</span>
                <button class="hint-close" onclick="window.shortcutHint.hide()">×</button>
            </div>
            <div class="hint-body">
                ${this.getCurrentPageShortcuts()}
            </div>
        `;
        document.body.appendChild(hint);
        this.hintElement = hint;
    }

    getCurrentPageShortcuts() {
        const pageType = document.body.dataset.page || 'home';
        const shortcuts = {
            'home': [
                { keys: ['Ctrl', 'K'], desc: '快速搜索' },
                { keys: ['Ctrl', 'N'], desc: '新建文章' },
                { keys: ['Ctrl', '/'], desc: '查看更多' }
            ],
            'editor': [
                { keys: ['Ctrl', 'S'], desc: '保存文章' },
                { keys: ['Ctrl', 'P'], desc: '切换预览' },
                { keys: ['ESC'], desc: '关闭编辑器' }
            ],
            'admin': [
                { keys: ['Ctrl', 'N'], desc: '新建文章' },
                { keys: ['Ctrl', 'K'], desc: '快速搜索' },
                { keys: ['Ctrl', '/'], desc: '查看更多' }
            ]
        };

        const pageShortcuts = shortcuts[pageType] || shortcuts['home'];
        return pageShortcuts.map(s => `
            <div class="hint-item">
                ${s.keys.map(k => `<kbd>${k}</kbd>`).join(' + ')}
                <span>${s.desc}</span>
            </div>
        `).join('');
    }

    show() {
        if (!this.hintElement) return;
        this.hintElement.style.display = 'block';

        // 3秒后自动淡出
        this.autoFadeTimer = setTimeout(() => {
            this.hide();
        }, 3000);
    }

    hide() {
        if (!this.hintElement) return;
        this.hintElement.style.opacity = '0';
        setTimeout(() => {
            if (this.hintElement) {
                this.hintElement.style.display = 'none';
            }
        }, 300);

        sessionStorage.setItem('shortcutHintDismissed', 'true');
    }
}

// 页面加载后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.shortcutHint = new ShortcutHint();
});
```

- [ ] **Step 2: Add new global shortcuts to ShortcutHandler**

Add to `static/js/shortcuts.js` in the DOMContentLoaded listener:

```javascript
// 在通用快捷键部分添加
shortcutHandler.register('ctrl+n', () => {
    const newPostBtn = document.querySelector('a[href*="/admin/new"], a[href*="/new"]');
    if (newPostBtn) {
        window.location.href = newPostBtn.href;
    }
}, '新建文章');

shortcutHandler.register('ctrl+shift+n', () => {
    const quickNoteBtn = document.querySelector('a[href*="quick_note"]');
    if (quickNoteBtn) {
        window.location.href = quickNoteBtn.href;
    }
}, '快速记事');

shortcutHandler.register('esc', () => {
    // 关闭所有模态框
    const modals = document.querySelectorAll('.shortcut-help-modal, .modal, [role="dialog"]');
    modals.forEach(modal => modal.remove());
}, '关闭弹窗');
```

- [ ] **Step 3: Add editor-specific shortcuts**

Update `registerEditorShortcuts()` function:

```javascript
function registerEditorShortcuts() {
    // Ctrl+S (保存), Ctrl+Shift+S (保存草稿), Ctrl+P (预览), ESC (关闭) 已在上文定义

    // 新增编辑器快捷键
    const quillEditor = document.querySelector('.ql-editor');
    if (quillEditor) {
        shortcutHandler.register('ctrl+b', () => {
            quillEditor.focus();
            document.execCommand('bold');
        }, '加粗');

        shortcutHandler.register('ctrl+i', () => {
            quillEditor.focus();
            document.execCommand('italic');
        }, '斜体');

        shortcutHandler.register('ctrl+shift+k', () => {
            const range = quill.getSelection();
            quill.insertText(range.index, range.length, '`', 'user');
        }, '插入代码');

        shortcutHandler.register('ctrl+alt+l', () => {
            const range = quill.getSelection();
            quill.formatLine(range.index, 1, 'list', 'bullet');
        }, '无序列表');

        shortcutHandler.register('ctrl+alt+o', () => {
            const range = quill.getSelection();
            quill.formatLine(range.index, 1, 'list', 'ordered');
        }, '有序列表');
    }
}
```

- [ ] **Step 4: Add CSS styles for shortcut hints**

Add to `static/css/style.css`:

```css
/* 快捷键提示组件 */
.shortcut-hint {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: var(--card-bg, rgba(255, 255, 255, 0.95));
    border: 1px solid var(--border-color, #e5e7eb);
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    padding: 16px;
    max-width: 280px;
    z-index: 1000;
    animation: fadeIn 0.3s ease-out;
    transition: opacity 0.3s ease-out;
}

.hint-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    font-weight: 600;
}

.hint-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.6;
    transition: opacity 0.2s;
}

.hint-close:hover {
    opacity: 1;
}

.hint-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.hint-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.9rem;
}

.hint-item kbd {
    background: var(--code-bg, #f3f4f6);
    border: 1px solid var(--border-color, #e5e7eb);
    border-radius: 4px;
    padding: 4px 8px;
    font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
    font-size: 0.85rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.hint-item span {
    color: var(--text-secondary, #666);
}

@media (max-width: 768px) {
    .shortcut-hint {
        display: none;
    }
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

- [ ] **Step 5: Test keyboard shortcuts manually**

Open browser and test:
1. Navigate to home page - hint should appear and fade after 3s
2. Press Ctrl+K - search input should focus
3. Press Ctrl+N - should navigate to new post
4. Press Ctrl+/ - help modal should appear
5. Press ESC - modal should close
6. Navigate to editor page
7. Press Ctrl+B - text should bold
8. Press Ctrl+I - text should italicize

- [ ] **Step 6: Commit changes**

```bash
git add static/js/shortcuts.js static/css/style.css
git commit -m "feat: enhance keyboard shortcuts with hints and global shortcuts

- Add ShortcutHint component with auto-fade
- Add Ctrl+N for new post, Ctrl+Shift+N for quick note
- Add ESC to close modals
- Add editor shortcuts: Ctrl+B (bold), Ctrl+I (italic), Ctrl+Shift+K (code), Ctrl+Alt+L (bullet list), Ctrl+Alt+O (numbered list)
- Add responsive CSS styles

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Breadcrumb Navigation

**Files:**
- Create: `templates/components/breadcrumb.html`
- Modify: `backend/routes/blog.py`
- Modify: `templates/post.html`

- [ ] **Step 1: Create breadcrumb component template**

Create `templates/components/breadcrumb.html`:

```html
{% macro breadcrumb(items) %}
{% if items %}
<nav class="breadcrumb" aria-label="面包屑导航">
  {% for item in items %}
    {% if item.url %}
      <a href="{{ item.url }}">{{ item.title }}</a>
    {% else %}
      <span class="current">{{ item.title }}</span>
    {% endif %}

    {% if not loop.last %}
      <span class="separator" aria-hidden="true">&gt;</span>
    {% endif %}
  {% endfor %}
</nav>

<!-- 结构化数据 -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {% for item in items %}
    {
      "@type": "ListItem",
      "position": {{ loop.index }},
      "name": "{{ item.title }}",
      {% if item.url %}
      "item": "{{ request.url_root.rstrip('/') }}{{ item.url }}"
      {% endif %}
    }{{ "," if not loop.last }}
    {% endfor %}
  ]
}
</script>
{% endif %}
{% endmacro %}
```

- [ ] **Step 2: Update blog route to provide breadcrumb data**

Modify `backend/routes/blog.py` view_post function:

```python
@app.route('/post/<int:post_id>')
def view_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()

    if not post:
        conn.close()
        abort(404)

    # 准备面包屑数据
    breadcrumb = [
        {'title': '首页', 'url': url_for('index')}
    ]

    # 如果有分类，添加分类层级
    if post['category_id']:
        category = conn.execute(
            'SELECT * FROM categories WHERE id = ?',
            (post['category_id'],)
        ).fetchone()

        if category:
            breadcrumb.append({
                'title': category['name'],
                'url': url_for('view_category', category_id=category['id'])
            })

    # 当前文章（无链接）
    breadcrumb.append({
        'title': post['title'],
        'url': None
    })

    # ... existing code ...

    return render_template('post.html', post=post, breadcrumb=breadcrumb)
```

- [ ] **Step 3: Add breadcrumb CSS to style.css**

Add to `static/css/style.css`:

```css
/* 面包屑导航 */
.breadcrumb {
  padding: 12px 0;
  margin-bottom: 20px;
  font-size: 0.9rem;
  color: var(--text-secondary, #666);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}

.breadcrumb a {
  color: var(--primary-color, #007bff);
  text-decoration: none;
  transition: color 0.2s ease;
}

.breadcrumb a:hover {
  color: var(--primary-hover, #0056b3);
  text-decoration: underline;
}

.breadcrumb .separator {
  margin: 0 8px;
  color: var(--text-muted, #999);
  user-select: none;
}

.breadcrumb .current {
  color: var(--text-primary, #333);
  font-weight: 500;
}

@media (max-width: 768px) {
  .breadcrumb {
    font-size: 0.85rem;
    padding: 8px 0;
  }

  .breadcrumb .separator {
    margin: 0 6px;
  }

  .breadcrumb .current {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    display: inline-block;
    vertical-align: middle;
  }
}
```

- [ ] **Step 4: Import and use breadcrumb in post template**

Modify `templates/post.html`:

```html
{% extends "base.html" %}

{% from "components/breadcrumb.html" import breadcrumb %}

{% block content %}
<article class="post">
  <!-- 面包屑导航 -->
  {{ breadcrumb(breadcrumb) }}

  <!-- 现有文章内容 -->
  ...
</article>
{% endblock %}
```

- [ ] **Step 5: Test breadcrumb navigation**

1. Visit a post page
2. Verify breadcrumb shows: 首页 > [Category] > [Post Title]
3. Click "首页" - should go to home
4. Click category name - should go to category page
5. Check browser console for structured data errors
6. Test on mobile - long title should truncate

- [ ] **Step 6: Commit changes**

```bash
git add templates/components/breadcrumb.html backend/routes/blog.py templates/post.html static/css/style.css
git commit -m "feat: add breadcrumb navigation to post pages

- Create breadcrumb component macro
- Add breadcrumb data to blog route
- Display breadcrumb on post detail pages
- Include Schema.org structured data for SEO
- Add responsive styles with mobile truncation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Static Asset Auto-Versioning

**Files:**
- Create: `backend/utils/asset_version.py`
- Create: `backend/utils/template_helpers.py`
- Modify: `backend/app.py`
- Modify: `templates/base.html`

- [ ] **Step 1: Create asset version manager**

Create `backend/utils/asset_version.py`:

```python
"""静态资源版本管理 - 基于文件内容hash自动生成版本号"""
import os
import json
import hashlib
import base64
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class AssetVersionManager:
    """静态资源版本管理器"""

    def __init__(self, static_folder: str):
        self.static_folder = Path(static_folder)
        self.manifest_file = self.static_folder / 'manifest.json'
        self.manifest: Dict = self._load_or_generate_manifest()

    def _load_or_generate_manifest(self) -> Dict:
        """加载或生成manifest文件"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                logger.info(f'已加载manifest文件，共{len(manifest)}个资源')
                return manifest
            except Exception as e:
                logger.warning(f'加载manifest失败: {e}，将重新生成')

        return self._generate_manifest()

    def _generate_manifest(self) -> Dict:
        """生成文件hash映射"""
        manifest = {}
        extensions = ['.css', '.js']

        logger.info('开始生成manifest...')

        for ext in extensions:
            for file_path in self.static_folder.rglob(f'*{ext}'):
                # 跳过特定目录
                if any(skip in str(file_path) for skip in ['node_modules', '.venv', '__pycache__', '.git']):
                    continue

                try:
                    rel_path = str(file_path.relative_to(self.static_folder))
                    file_hash = self._calculate_hash(file_path)
                    versioned_name = self._version_filename(file_path, file_hash)

                    manifest[rel_path] = {
                        'hash': file_hash,
                        'versioned': versioned,
                        'integrity': self._calculate_sri(file_path)
                    }

                    logger.debug(f'{rel_path} -> {versioned}')

                except Exception as e:
                    logger.error(f'处理文件{file_path}失败: {e}')

        self._save_manifest(manifest)
        return manifest

    def _calculate_hash(self, file_path: Path) -> str:
        """计算文件内容的MD5 hash（前8位）"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5.update(chunk)
        return md5.hexdigest()[:8]

    def _calculate_sri(self, file_path: Path) -> str:
        """计算Subresource Integrity哈希（sha384）"""
        sha384 = hashlib.sha384()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha384.update(chunk)
        return f'sha384-{base64.b64encode(sha384.digest()).decode()}'

    def _version_filename(self, file_path: Path, file_hash: str) -> str:
        """生成版本化文件名"""
        path = Path(file_path)
        stem = path.stem
        suffix = path.suffix
        return f'{stem}.{file_hash}{suffix}'

    def _save_manifest(self, manifest: Dict):
        """保存manifest文件"""
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        logger.info(f'Manifest已保存到 {self.manifest_file}')

    def get_versioned_path(self, relative_path: str) -> str:
        """获取版本化的文件路径"""
        if relative_path in self.manifest:
            return self.manifest[relative_path]['versioned']
        logger.warning(f'未找到资源版本信息: {relative_path}')
        return relative_path

    def get_integrity(self, relative_path: str) -> Optional[str]:
        """获取SRI哈希"""
        if relative_path in self.manifest:
            return self.manifest[relative_path].get('integrity')
        return None

    def regenerate(self):
        """强制重新生成manifest"""
        logger.info('重新生成manifest...')
        self.manifest = self._generate_manifest()
```

- [ ] **Step 2: Create template helpers**

Create `backend/utils/template_helpers.py`:

```python
"""Jinja2模板助手函数"""
from flask import url_for
from typing import Optional, Dict

def static_file(filename: str) -> str:
    """
    返回带版本号的静态文件URL

    使用方式:
    <link rel="stylesheet" href="{{ static_file('css/style.css') }}">
    """
    from flask import current_app

    if not hasattr(current_app, 'asset_manager'):
        return url_for('static', filename=filename)

    asset_manager = current_app.asset_manager
    versioned_path = asset_manager.get_versioned_path(filename)

    return url_for('static', filename=versioned_path)

def static_file_with_integrity(filename: str) -> Dict[str, Optional[str]]:
    """
    返回带版本号和SRI的静态文件信息

    使用方式:
    {% set asset = static_file_with_integrity('js/editor.js') %}
    <script src="{{ asset.url }}" integrity="{{ asset.integrity }}"></script>
    """
    from flask import current_app

    if not hasattr(current_app, 'asset_manager'):
        return {'url': url_for('static', filename=filename), 'integrity': None}

    asset_manager = current_app.asset_manager
    versioned_path = asset_manager.get_versioned_path(filename)
    integrity = asset_manager.get_integrity(filename)

    return {
        'url': url_for('static', filename=versioned_path),
        'integrity': integrity
    }

def register_template_helpers(app):
    """注册模板助手函数到Flask应用"""
    app.jinja_env.globals.update(
        static_file=static_file,
        static_file_with_integrity=static_file_with_integrity
    )
```

- [ ] **Step 3: Integrate asset manager into Flask app**

Modify `backend/app.py`:

```python
# 在现有导入后添加
from backend.utils.asset_version import AssetVersionManager
from backend.utils.template_helpers import register_template_helpers

# 在app创建后，初始化资产管理器
app = Flask(__name__, ...)

# 初始化资产管理器
app.asset_manager = AssetVersionManager(app.static_folder)

# 注册模板助手
register_template_helpers(app)

# 开发环境：启动时检查manifest
if app.config.get('DEBUG'):
    @app.before_first_request
    def auto_regenerate_assets():
        """启动时检查manifest是否存在，不存在则生成"""
        if not app.asset_manager.manifest_file.exists():
            app.asset_manager.regenerate()
```

- [ ] **Step 4: Update base template to use versioned assets**

Modify `templates/base.html`:

```html
<!-- 替换现有的CSS/JS引用 -->
<!-- 旧方式（注释掉）-->
{#
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}?v=4.0">
<link rel="stylesheet" href="{{ url_for('static', filename='css/mobile-weibo.css') }}?v=1.0">
#}

<!-- 新方式 -->
<link rel="stylesheet" href="{{ static_file('css/style.css') }}">
<link rel="stylesheet" href="{{ static_file('css/mobile-weibo.css') }}">

<!-- JavaScript -->
<script src="{{ static_file('js/main.js') }}"></script>
<script src="{{ static_file('js/shortcuts.js') }}"></script>
<!-- 其他JS文件... -->
```

- [ ] **Step 5: Create manifest.json**

Run in terminal:

```bash
# 启动Python并生成manifest
cd /Users/gn/simple-blog
python -c "from backend.app import app; app.app_context().push(); app.asset_manager.regenerate()"
```

Expected output: `Manifest已保存到 static/manifest.json`

- [ ] **Step 6: Verify asset versioning works**

1. Check `static/manifest.json` exists and contains asset mappings
2. Start the app: `python backend/app.py`
3. Visit home page
4. View page source - CSS/JS links should have version hashes: `style.a1b2c3d.css`
5. Edit a CSS file slightly
6. Regenerate manifest
7. Refresh page - link should change to new hash

- [ ] **Step 7: Add manifest.json to .gitignore**

Add to `.gitignore`:

```
# Asset version manifest
static/manifest.json
```

- [ ] **Step 8: Commit changes**

```bash
git add backend/utils/asset_version.py backend/utils/template_helpers.py backend/app.py templates/base.html .gitignore
git commit -m "feat: implement automatic static asset versioning

- Add AssetVersionManager based on file content hash
- Add template helpers for versioned asset URLs
- Generate manifest.json with asset hashes
- Update templates to use {{ static_file() }} helper
- Support SRI for enhanced security

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Phase 2: Complex Features (2 weeks)

### Task 4: Database Migrations

**Files:**
- Create: `backend/migrations/migrate_drafts.py`
- Create: `backend/migrations/migrate_image_optimization.py`

- [ ] **Step 1: Create drafts table migration**

Create `backend/migrations/migrate_drafts.py`:

```python
"""创建drafts表用于多设备草稿同步"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import config

def migrate():
    """执行迁移"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 创建drafts表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category_id INTEGER,
                tags TEXT,
                is_published BOOLEAN DEFAULT 0,
                device_info TEXT,
                user_agent TEXT,
                last_sync TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')

        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_user_post
            ON drafts(user_id, post_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_user_updated
            ON drafts(user_id, updated_at DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_post
            ON drafts(post_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_drafts_device
            ON drafts(user_id, device_info, updated_at)
        ''')

        # 唯一约束
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_drafts_unique
            ON drafts(user_id, post_id)
        ''')

        conn.commit()
        print("✅ Drafts表创建成功")

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
```

- [ ] **Step 2: Create optimized_images table migration**

Create `backend/migrations/migrate_image_optimization.py`:

```python
"""创建optimized_images表用于图片优化追踪"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import config

def migrate():
    """执行迁移"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimized_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                original_hash TEXT,
                thumbnail_path TEXT,
                medium_path TEXT,
                large_path TEXT,
                original_size INTEGER,
                optimized_size INTEGER,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_optimized_status
            ON optimized_images(status)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_optimized_original
            ON optimized_images(original_path)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_optimized_hash
            ON optimized_images(original_hash)
        ''')

        conn.commit()
        print("✅ Optimized_images表创建成功")

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
```

- [ ] **Step 3: Run migrations**

```bash
cd /Users/gn/simple-blog
python backend/migrations/migrate_drafts.py
python backend/migrations/migrate_image_optimization.py
```

Expected output:
```
✅ Drafts表创建成功
✅ Optimized_images表创建成功
```

- [ ] **Step 4: Verify tables created**

```bash
sqlite3 blog.db ".schema drafts"
sqlite3 blog.db ".schema optimized_images"
```

- [ ] **Step 5: Commit migrations**

```bash
git add backend/migrations/migrate_drafts.py backend/migrations/migrate_image_optimization.py
git commit -m "feat: add database migrations for draft sync and image optimization

- Create drafts table with unique constraint on (user_id, post_id)
- Create optimized_images table for tracking image optimization
- Add indexes for performance
- Include device_info index for conflict detection

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 6: Create rollback migration scripts**

Create `backend/migrations/rollback_drafts.py`:

```python
"""回滚drafts表"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import config

def rollback():
    """执行回滚"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('DROP TABLE IF EXISTS drafts')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_user_post')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_user_updated')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_post')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_device')
        cursor.execute('DROP INDEX IF EXISTS idx_drafts_unique')

        conn.commit()
        print("✅ Drafts表已回滚")

    except Exception as e:
        conn.rollback()
        print(f"❌ 回滚失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    rollback()
```

Create `backend/migrations/rollback_image_optimization.py`:

```python
"""回滚optimized_images表"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import config

def rollback():
    """执行回滚"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute('DROP TABLE IF EXISTS optimized_images')
        cursor.execute('DROP INDEX IF EXISTS idx_optimized_status')
        cursor.execute('DROP INDEX IF EXISTS idx_optimized_original')
        cursor.execute('DROP INDEX IF EXISTS idx_optimized_hash')

        conn.commit()
        print("✅ Optimized_images表已回滚")

    except Exception as e:
        conn.rollback()
        print(f"❌ 回滚失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    rollback()
```

---

### Task 5: Draft Sync Backend API

**Files:**
- Create: `backend/models/draft.py`
- Create: `backend/routes/drafts.py`
- Modify: `backend/app.py`

- [ ] **Step 1: Create draft model**

Create `backend/models/draft.py`:

```python
"""草稿数据模型"""
from backend.models import get_db_connection
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

def save_draft(user_id: int, post_id: Optional[int], title: str,
               content: str, category_id: Optional[int] = None,
               tags: Optional[List[str]] = None, device_info: str = '') -> Dict:
    """
    保存草稿（带事务管理）

    Returns: {
        'success': bool,
        'draft_id': int,
        'updated_at': str,
        'status': 'saved' | 'conflict_detected',
        'other_drafts': List[Dict]
    }
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        conn.execute('BEGIN TRANSACTION')

        import json
        tags_json = json.dumps(tags) if tags else None

        # 检测冲突
        cursor.execute('''
            SELECT id, title, updated_at, device_info
            FROM drafts
            WHERE user_id = ? AND post_id = ?
              AND device_info != ?
              AND updated_at > datetime('now', '-5 minutes')
            ORDER BY updated_at DESC
        ''', (user_id, post_id, device_info))

        conflicts = [dict(row) for row in cursor.fetchall()]

        # 使用UPSERT（SQLite 3.24+）
        cursor.execute('''
            INSERT INTO drafts (user_id, post_id, title, content, category_id, tags, device_info)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, post_id)
            DO UPDATE SET
                title = excluded.title,
                content = excluded.content,
                category_id = excluded.category_id,
                tags = excluded.tags,
                device_info = excluded.device_info,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, updated_at
        ''', (user_id, post_id, title, content, category_id, tags_json, device_info))

        result = cursor.fetchone()
        draft_id = result['id']
        updated_at = result['updated_at']

        conn.commit()

        return {
            'success': True,
            'draft_id': draft_id,
            'updated_at': updated_at,
            'status': 'conflict_detected' if conflicts else 'saved',
            'other_drafts': conflicts
        }

    except Exception as e:
        conn.rollback()
        logger.error(f'保存草稿失败: {e}')
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        conn.close()

def get_drafts(user_id: int, post_id: Optional[int] = None) -> List[Dict]:
    """获取用户的草稿列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if post_id:
            cursor.execute('''
                SELECT id, post_id, title, updated_at, device_info
                FROM drafts
                WHERE user_id = ? AND post_id = ?
                ORDER BY updated_at DESC
            ''', (user_id, post_id))
        else:
            cursor.execute('''
                SELECT id, post_id, title, updated_at, device_info
                FROM drafts
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT 20
            ''', (user_id,))

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()

def get_draft(draft_id: int) -> Optional[Dict]:
    """获取单个草稿详情"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT * FROM drafts WHERE id = ?
        ''', (draft_id,))

        row = cursor.fetchone()
        return dict(row) if row else None

    finally:
        conn.close()

def resolve_conflict(conflict_draft_id: int, current_draft_id: int,
                     action: str, merged_data: Optional[Dict] = None) -> Dict:
    """解决草稿冲突"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        conn.execute('BEGIN TRANSACTION')

        if action == 'keep_current':
            # 删除对方草稿
            cursor.execute('DELETE FROM drafts WHERE id = ?', (conflict_draft_id,))

        elif action == 'keep_other':
            # 删除当前草稿
            cursor.execute('DELETE FROM drafts WHERE id = ?', (current_draft_id,))

        elif action == 'merge' and merged_data:
            import json
            # 更新当前草稿为合并后的内容
            cursor.execute('''
                UPDATE drafts
                SET title = ?, content = ?, category_id = ?, tags = ?
                WHERE id = ?
            ''', (merged_data['title'], merged_data['content'],
                  merged_data.get('category_id'),
                  json.dumps(merged_data.get('tags', [])),
                  current_draft_id))

            # 删除对方草稿
            cursor.execute('DELETE FROM drafts WHERE id = ?', (conflict_draft_id,))

        conn.commit()
        return {'success': True, 'message': '冲突已解决'}

    except Exception as e:
        conn.rollback()
        logger.error(f'解决冲突失败: {e}')
        return {'success': False, 'error': str(e)}

    finally:
        conn.close()

def delete_draft(draft_id: int, user_id: int) -> Dict:
    """删除草稿"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM drafts WHERE id = ? AND user_id = ?
        ''', (draft_id, user_id))

        conn.commit()
        return {'success': True, 'message': '草稿已删除'}

    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}

    finally:
        conn.close()
```

- [ ] **Step 2: Create drafts API routes**

Create `backend/routes/drafts.py`:

```python
"""草稿同步API路由"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from backend.models.draft import save_draft, get_drafts, get_draft, resolve_conflict, delete_draft

drafts_bp = Blueprint('drafts', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

@drafts_bp.route('/api/drafts', methods=['POST'])
@login_required
def api_save_draft():
    """保存草稿"""
    try:
        data = request.get_json()
        user_id = session['user_id']

        result = save_draft(
            user_id=user_id,
            post_id=data.get('post_id'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            category_id=data.get('category_id'),
            tags=data.get('tags', []),
            device_info=data.get('device_info', '')
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts', methods=['GET'])
@login_required
def api_get_drafts():
    """获取草稿列表"""
    try:
        post_id = request.args.get('post_id', type=int)
        user_id = session['user_id']

        drafts = get_drafts(user_id, post_id)
        return jsonify({'success': True, 'drafts': drafts}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts/<int:draft_id>', methods=['GET'])
@login_required
def api_get_draft(draft_id):
    """获取单个草稿"""
    try:
        draft = get_draft(draft_id)
        if not draft:
            return jsonify({'success': False, 'error': '草稿不存在'}), 404

        return jsonify({'success': True, 'draft': draft}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts/resolve', methods=['POST'])
@login_required
def api_resolve_conflict():
    """解决草稿冲突"""
    try:
        data = request.get_json()
        result = resolve_conflict(
            conflict_draft_id=data['conflict_draft_id'],
            current_draft_id=data['current_draft_id'],
            action=data['action'],
            merged_data=data.get('merged_data')
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@drafts_bp.route('/api/drafts/<int:draft_id>', methods=['DELETE'])
@login_required
def api_delete_draft(draft_id):
    """删除草稿"""
    try:
        user_id = session['user_id']
        result = delete_draft(draft_id, user_id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

- [ ] **Step 3: Register drafts blueprint in app**

Modify `backend/app.py`:

```python
# 在现有蓝图注册后添加
from backend.routes.drafts import drafts_bp

# 注册drafts蓝图
app.register_blueprint(drafts_bp)
```

- [ ] **Step 4: Test draft API endpoints**

```bash
# Start the app
python backend/app.py

# Test save draft (requires login session)
curl -X POST http://localhost:5001/api/drafts \
  -H "Content-Type: application/json" \
  -d '{"post_id": null, "title": "测试草稿", "content": "测试内容", "device_info": "Test Device"}'

# Test get drafts
curl http://localhost:5001/api/drafts?post_id=123
```

- [ ] **Step 5: Commit draft backend**

```bash
git add backend/models/draft.py backend/routes/drafts.py backend/app.py backend/migrations/rollback_drafts.py backend/migrations/rollback_image_optimization.py
git commit -m "feat: implement draft sync backend API

- Add draft model with transaction support
- Create drafts API blueprint with full CRUD
- Implement conflict detection and resolution
- Add UPSERT for atomic draft updates
- Include device info for multi-device sync
- Add rollback migration scripts for safe deployment

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Draft Sync Frontend

**Files:**
- Create: `static/js/draft-sync.js`
- Create: `static/css/draft-dialog.css`
- Modify: `static/js/editor.js`
- Modify: `templates/admin/edit.html`

- [ ] **Step 1: Create draft sync manager**

Create `static/js/draft-sync.js`:

```javascript
/**
 * 草稿同步管理器 - 多设备自动保存和冲突解决
 */
class DraftSyncManager {
    constructor() {
        this.autoSaveInterval = 30000; // 30秒
        this.autoSaveTimer = null;
        this.currentDraftId = null;
        this.lastSyncTime = null;
        this.deviceInfo = this.getDeviceInfo();
        this.postId = null;
    }

    init(postId = null) {
        this.postId = postId;
        this.loadLastSyncTime();
        this.observeContentChanges();
        this.checkForExistingDrafts();
    }

    // 监听内容变化
    observeContentChanges() {
        const titleInput = document.getElementById('title');
        const contentTextarea = document.getElementById('content');

        const debouncedSave = this.debounce(() => {
            this.saveDraft();
        }, this.autoSaveInterval);

        titleInput?.addEventListener('input', debouncedSave);
        contentTextarea?.addEventListener('input', debouncedSave);
    }

    // 保存草稿到服务器
    async saveDraft() {
        const saveStatus = document.getElementById('saveStatus');
        if (saveStatus) {
            saveStatus.textContent = '正在保存...';
            saveStatus.className = 'save-status saving';
        }

        try {
            const formData = this.getFormData();
            const response = await fetch('/api/drafts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCsrfToken()
                },
                body: JSON.stringify({
                    post_id: this.postId,
                    device_info: this.deviceInfo,
                    ...formData
                })
            });

            const result = await response.json();

            if (result.success) {
                this.currentDraftId = result.draft_id;
                this.lastSyncTime = result.updated_at;

                if (result.status === 'conflict_detected' && result.other_drafts?.length > 0) {
                    this.showConflictDialog(result.other_drafts);
                } else {
                    if (saveStatus) {
                        saveStatus.textContent = `已保存 ${this.getTimeAgo(result.updated_at)}`;
                        saveStatus.className = 'save-status saved';
                    }
                }

                this.saveToLocalStorage(formData);
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('草稿保存失败:', error);
            if (saveStatus) {
                saveStatus.textContent = '保存失败，已保存到本地';
                saveStatus.className = 'save-status error';
            }
            this.saveToLocalStorage(this.getFormData());
        }
    }

    // 检测现有草稿
    async checkForExistingDrafts() {
        if (!this.postId) return;

        try {
            const response = await fetch(`/api/drafts?post_id=${this.postId}`);
            const result = await response.json();

            if (result.success && result.drafts?.length > 0) {
                const localDraft = this.getFromLocalStorage();
                const serverDrafts = result.drafts;

                if (serverDrafts.length > 0 || localDraft) {
                    this.showDraftRecoveryDialog(serverDrafts, localDraft);
                }
            }
        } catch (error) {
            console.error('检测草稿失败:', error);
        }
    }

    // 显示草稿恢复对话框
    showDraftRecoveryDialog(serverDrafts, localDraft) {
        const modal = document.createElement('div');
        modal.className = 'draft-recovery-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>💾 检测到未保存的草稿</h2>
                </div>
                <div class="modal-body">
                    ${this.renderDraftOptions(serverDrafts, localDraft)}
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" id="discardAllDrafts">
                        放弃所有草稿
                    </button>
                </div>
            </div>
        `;

        // 绑定事件
        modal.querySelector('#discardAllDrafts').onclick = () => {
            localStorage.removeItem(`draft_${this.postId || 'new'}`);
            modal.remove();
        };

        document.body.appendChild(modal);
    }

    renderDraftOptions(serverDrafts, localDraft) {
        let html = '';

        if (serverDrafts?.length > 0) {
            serverDrafts.forEach(draft => {
                html += `
                    <div class="draft-option" data-draft-id="${draft.id}">
                        <h3>📱 ${draft.device_info} - ${this.getTimeAgo(draft.updated_at)}</h3>
                        <div class="draft-preview">${draft.title}</div>
                        <button class="btn btn-primary recover-draft">恢复此草稿</button>
                    </div>
                `;
            });
        }

        if (localDraft) {
            html += `
                <div class="draft-option local-draft">
                    <h3>💾 本地草稿</h3>
                    <div class="draft-preview">${localDraft.title}</div>
                    <button class="btn btn-primary recover-local">恢复本地草稿</button>
                </div>
            `;
        }

        return html;
    }

    // 显示草稿冲突对话框
    showConflictDialog(otherDrafts) {
        const modal = document.createElement('div');
        modal.className = 'draft-conflict-modal';

        const currentData = this.getFormData();

        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>⚠️ 检测到其他设备的草稿</h2>
                </div>
                <div class="modal-body">
                    <div class="conflict-version">
                        <h3>📱 ${otherDrafts[0].device_info} - ${this.getTimeAgo(otherDrafts[0].updated_at)}</h3>
                        <div class="draft-preview">${otherDrafts[0].title}</div>
                        <button class="btn btn-primary" data-action="keep-other">使用此版本</button>
                    </div>
                    <hr>
                    <div class="conflict-version current">
                        <h3>💻 ${this.deviceInfo} - 刚刚</h3>
                        <div class="draft-preview">${currentData.title}</div>
                        <button class="btn btn-primary" data-action="keep-current">保留当前编辑</button>
                    </div>
                    <hr>
                    <button class="btn btn-secondary" data-action="merge">🔄 合并两个版本</button>
                </div>
            </div>
        `;

        modal.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', async () => {
                await this.resolveConflict(otherDrafts[0].id, btn.dataset.action);
                modal.remove();
            });
        });

        document.body.appendChild(modal);
    }

    // 解决冲突
    async resolveConflict(otherDraftId, action) {
        try {
            const response = await fetch('/api/drafts/resolve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCsrfToken()
                },
                body: JSON.stringify({
                    conflict_draft_id: otherDraftId,
                    current_draft_id: this.currentDraftId,
                    action: action
                })
            });

            const result = await response.json();
            if (result.success) {
                this.showNotification(result.message, 'success');
                if (action === 'keep_other') {
                    location.reload();
                }
            }
        } catch (error) {
            this.showNotification('解决冲突失败: ' + error.message, 'error');
        }
    }

    // 获取设备信息
    getDeviceInfo() {
        const ua = navigator.userAgent;
        let browser = 'Unknown Browser';
        let os = 'Unknown OS';

        if (ua.includes('Chrome')) browser = 'Chrome';
        else if (ua.includes('Firefox')) browser = 'Firefox';
        else if (ua.includes('Safari')) browser = 'Safari';

        if (ua.includes('Windows')) os = 'Windows';
        else if (ua.includes('Mac')) os = 'macOS';
        else if (ua.includes('Linux')) os = 'Linux';
        else if (ua.includes('Android')) os = 'Android';
        else if (ua.includes('iOS')) os = 'iOS';

        return `${browser} on ${os}`;
    }

    // 工具方法
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    getTimeAgo(timestamp) {
        const now = new Date();
        const past = new Date(timestamp);
        const diff = Math.floor((now - past) / 1000);

        if (diff < 60) return '刚刚';
        if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
        return `${Math.floor(diff / 86400)}天前`;
    }

    getFormData() {
        return {
            title: document.getElementById('title')?.value || '',
            content: document.getElementById('content')?.value || '',
            category_id: document.getElementById('category')?.value || null,
            tags: this.getTags()
        };
    }

    getTags() {
        const tagInput = document.getElementById('tags');
        if (tagInput) {
            return tagInput.value.split(',').map(t => t.trim()).filter(t => t);
        }
        return [];
    }

    getCsrfToken() {
        return document.querySelector('meta[name="csrf_token"]')?.getAttribute('content');
    }

    saveToLocalStorage(data) {
        localStorage.setItem(`draft_${this.postId || 'new'}`, JSON.stringify({
            ...data,
            saved_at: new Date().toISOString()
        }));
    }

    getFromLocalStorage() {
        const key = `draft_${this.postId || 'new'}`;
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    }

    loadLastSyncTime() {
        const key = `last_sync_${this.postId || 'new'}`;
        const time = localStorage.getItem(key);
        if (time) {
            this.lastSyncTime = time;
        }
    }

    showNotification(message, type = 'info') {
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    const pageType = document.body.dataset.page;
    if (pageType === 'editor' || pageType === 'admin') {
        const postIdElement = document.querySelector('[data-post-id]');
        const postId = postIdElement?.dataset.postId ?
                       parseInt(postIdElement.dataset.postId) : null;

        window.draftSync = new DraftSyncManager();
        window.draftSync.init(postId);
    }
});
```

- [ ] **Step 2: Create draft dialog CSS**

Create `static/css/draft-dialog.css`:

```css
/* 草稿恢复/冲突对话框 */
.draft-recovery-modal,
.draft-conflict-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.draft-recovery-modal .modal-content,
.draft-conflict-modal .modal-content {
  background: var(--card-bg, #fff);
  border-radius: 12px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease-out;
}

.draft-recovery-modal .modal-header,
.draft-conflict-modal .modal-header {
  padding: 20px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
}

.draft-recovery-modal .modal-header h2,
.draft-conflict-modal .modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.draft-recovery-modal .modal-body,
.draft-conflict-modal .modal-body {
  padding: 20px;
  overflow-y: auto;
  max-height: calc(80vh - 140px);
}

.draft-recovery-modal .modal-footer,
.draft-conflict-modal .modal-footer {
  padding: 20px;
  border-top: 1px solid var(--border-color, #e5e7eb);
  text-align: right;
}

.draft-option {
  border: 2px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
  cursor: pointer;
  transition: all 0.2s;
}

.draft-option:hover {
  border-color: var(--primary-color, #007bff);
  background: var(--code-bg, #f9fafb);
}

.draft-option h3 {
  margin: 0 0 10px 0;
  font-size: 1.1rem;
}

.draft-option .draft-preview {
  background: var(--code-bg, #f3f4f6);
  padding: 10px;
  border-radius: 4px;
  font-size: 0.9rem;
  max-height: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 10px;
}

.conflict-version {
  padding: 15px;
  border: 2px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  margin-bottom: 15px;
}

.conflict-version.current {
  border-color: var(--primary-color, #007bff);
  background: var(--code-bg, #f9fafb);
}

.conflict-version h3 {
  margin: 0 0 10px 0;
}

@keyframes slideIn {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* 保存状态 */
.save-status {
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  transition: all 0.3s;
}

.save-status.saving {
  background: var(--warning-bg, #fff3cd);
  color: var(--warning-text, #856404);
}

.save-status.saved {
  background: var(--success-bg, #d4edda);
  color: var(--success-text, #155724);
}

.save-status.error {
  background: var(--error-bg, #f8d7da);
  color: var(--error-text, #721c24);
}
```

- [ ] **Step 3: Integrate draft sync into editor**

Modify `templates/admin/edit.html` and `templates/admin/new.html`:

Add before closing `</body>`:

```html
<!-- 草稿同步 -->
<link rel="stylesheet" href="{{ static_file('css/draft-dialog.css') }}">
<script src="{{ static_file('js/draft-sync.js') }}"></script>
```

Add `data-post-id` attribute to form:

```html
<form id="editorForm" data-post-id="{{ post.id if post else '' }}">
```

- [ ] **Step 4: Test draft sync manually**

1. Open editor in browser A
2. Type title and content
3. Wait 30 seconds - should see "已保存 X秒前"
4. Open same article in browser B (incognito mode)
5. Edit content in B
6. Wait 30 seconds
7. Check browser A - should see conflict dialog
8. Test conflict resolution options

- [ ] **Step 5: Commit draft sync frontend**

```bash
git add static/js/draft-sync.js static/css/draft-dialog.css templates/admin/edit.html templates/admin/new.html
git commit -m "feat: implement frontend draft sync with conflict resolution

- Add DraftSyncManager with 30s auto-save
- Implement conflict detection and UI dialogs
- Support multi-device draft synchronization
- Add localStorage fallback for offline support
- Include device identification for conflict context

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Image Optimization Backend

**Files:**
- Create: `backend/tasks/image_optimization_task.py`
- Modify: `backend/routes/admin.py`

- [ ] **Step 1: Create image optimization queue**

Create `backend/tasks/image_optimization_task.py`:

```python
"""图片后台优化任务系统"""
import threading
import logging
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from backend.image_processor import generate_image_sizes, get_image_hash
from backend.models import get_db_connection

logger = logging.getLogger(__name__)

class ImageOptimizationQueue:
    """线程安全的图片优化队列"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.executor = ThreadPoolExecutor(max_workers=4)
                cls._instance.queue = Queue()
                cls._instance.processing = False
            return cls._instance

    def enqueue(self, image_path):
        """添加图片到优化队列"""
        self.queue.put(image_path)
        logger.info(f'图片已加入优化队列: {image_path}')

        if not self.processing:
            self._process_queue()

    def _process_queue(self):
        """处理队列中的图片"""
        if self.queue.empty():
            self.processing = False
            return

        self.processing = True
        image_path = self.queue.get()

        # 提交到线程池
        self.executor.submit(self._optimize_image, image_path)

        # 继续处理下一个
        self._process_queue()

    def _optimize_image(self, image_path):
        """优化单张图片"""
        try:
            self._update_status(image_path, 'processing')

            uploads_dir = Path(__file__).parent.parent.parent / 'static' / 'uploads'
            output_dir = uploads_dir / 'optimized'
            output_dir.mkdir(exist_ok=True)

            result = generate_image_sizes(image_path, str(output_dir))

            # 计算文件大小
            original_size = Path(image_path).stat().st_size
            optimized_size = sum(
                Path(p).stat().st_size for p in [
                    result.get('thumbnail'),
                    result.get('medium'),
                    result.get('large')
                ] if p
            )

            self._update_completion(
                image_path,
                result.get('thumbnail'),
                result.get('medium'),
                result.get('large'),
                original_size,
                optimized_size
            )

            logger.info(f'图片优化完成: {image_path}')

        except Exception as e:
            logger.error(f'图片优化失败: {image_path}, 错误: {e}')
            self._update_status(image_path, 'failed', str(e))

    def _update_status(self, image_path, status, error=None):
        """更新优化状态"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE optimized_images
            SET status = ?, error_message = ?
            WHERE original_path = ?
        ''', (status, error, image_path))
        conn.commit()
        conn.close()

    def _update_completion(self, original_path, thumbnail, medium, large,
                          original_size, optimized_size):
        """更新优化完成信息"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE optimized_images
            SET thumbnail_path = ?,
                medium_path = ?,
                large_path = ?,
                original_size = ?,
                optimized_size = ?,
                status = 'completed',
                completed_at = CURRENT_TIMESTAMP
            WHERE original_path = ?
        ''', (thumbnail, medium, large, original_size, optimized_size, original_path))
        conn.commit()
        conn.close()

# 全局实例
optimization_queue = ImageOptimizationQueue()

def queue_image_optimization(image_path):
    """队列化图片优化任务（对外接口）"""
    optimization_queue.enqueue(image_path)
```

- [ ] **Step 2: Modify upload endpoint to trigger optimization**

Modify `backend/routes/admin.py` upload function:

```python
@app.route('/admin/upload', methods=['POST'])
@login_required
def upload_image():
    """上传图片（立即返回，后台优化）"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': '没有图片文件'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400

    # 保存原图
    filename = secure_filename(file.filename)
    uploads_folder = Path(app.config['UPLOAD_FOLDER'])
    uploads_folder.mkdir(exist_ok=True)

    original_path = uploads_folder / filename
    file.save(str(original_path))

    # 记录到数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO optimized_images (original_path, original_hash, status)
        VALUES (?, ?, 'pending')
    ''', (str(original_path), get_image_hash(str(original_path))))
    optimization_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # 触发后台优化
    from backend.tasks.image_optimization_task import queue_image_optimization
    queue_image_optimization(str(original_path))

    # 立即返回
    return jsonify({
        'success': True,
        'url': f'/static/uploads/{filename}',
        'optimization_id': optimization_id,
        'status': 'pending'
    })

# 添加查询优化状态端点
@app.route('/admin/image-status/<int:optimization_id>')
@login_required
def image_optimization_status(optimization_id):
    """查询图片优化状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT status, thumbnail_path, medium_path, large_path,
               original_size, optimized_size
        FROM optimized_images
        WHERE id = ?
    ''', (optimization_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({'success': False, 'error': '未找到优化记录'}), 404

    compression_ratio = 0
    if result['original_size'] and result['optimized_size']:
        compression_ratio = (1 - result['optimized_size'] / result['original_size']) * 100

    return jsonify({
        'success': True,
        'status': result['status'],
        'sizes': {
            'thumbnail': result['thumbnail_path'],
            'medium': result['medium_path'],
            'large': result['large_path']
        } if result['status'] == 'completed' else None,
        'compression_ratio': compression_ratio
    })
```

- [ ] **Step 3: Restart pending optimizations on app start**

Add to `backend/app.py`:

```python
# 应用启动时恢复未完成的优化任务
@app.before_first_request
def restart_pending_optimizations():
    """恢复之前未完成的优化任务"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT original_path FROM optimized_images
        WHERE status = 'pending'
        ORDER BY created_at ASC
    ''')
    pending = cursor.fetchall()
    conn.close()

    if pending:
        from backend.tasks.image_optimization_task import queue_image_optimization
        for row in pending:
            queue_image_optimization(row['original_path'])

        logger.info(f'恢复了 {len(pending)} 个待优化任务')
```

- [ ] **Step 4: Test image optimization**

1. Upload an image through editor
2. Check immediate response - should return quickly with `status: 'pending'`
3. Wait 2-3 seconds
4. Query `/admin/image-status/<id>` - should show `status: 'completed'`
5. Check `static/uploads/optimized/` - should contain WebP files
6. Check file sizes - should be significantly smaller

- [ ] **Step 5: Commit image optimization backend**

```bash
git add backend/tasks/image_optimization_task.py backend/routes/admin.py backend/app.py
git commit -m "feat: implement background image optimization system

- Add thread-safe ImageOptimizationQueue
- Integrate with upload endpoint for async processing
- Add image status query endpoint
- Auto-recover pending optimizations on restart
- Track optimization progress in database

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Image Optimization Frontend

**Files:**
- Modify: `static/js/editor.js`

- [ ] **Step 1: Modify Quill image upload handler**

Add to `static/js/editor.js` in the Quill initialization:

```javascript
// 替换现有的image handler
modules: {
    toolbar: {
        // ... existing toolbar config ...
        handlers: {
            image: function() {
                const input = document.getElementById('imageUpload');
                input.click();

                input.onchange = async () => {
                    const file = input.files[0];
                    if (!file) return;

                    const formData = new FormData();
                    formData.append('image', file);

                    // 显示上传进度
                    const range = quill.getSelection(true);
                    quill.disable();

                    try {
                        // 上传图片
                        const response = await fetch('/admin/upload', {
                            method: 'POST',
                            body: formData
                        });

                        const result = await response.json();

                        if (result.success) {
                            // 立即插入原图
                            quill.enable();
                            quill.setSelection(range.index, 0);
                            quill.insertEmbed(range.index, 'image', result.url);

                            // 开始轮询优化状态
                            pollImageOptimization(result.optimization_id, result.url, range.index);
                        } else {
                            throw new Error(result.error);
                        }
                    } catch (error) {
                        quill.enable();
                        showNotification('图片上传失败: ' + error.message, 'error');
                    }
                };
            }
        }
    }
}

// 轮询图片优化状态
function pollImageOptimization(optimizationId, originalUrl, insertIndex) {
    const maxAttempts = 10;
    let attempts = 0;

    const poll = setInterval(async () => {
        attempts++;

        try {
            const response = await fetch(`/admin/image-status/${optimizationId}`);
            const result = await response.json();

            if (result.status === 'completed') {
                clearInterval(poll);
                updateImageToOptimized(originalUrl, result.sizes, result.compression_ratio, insertIndex);
                showNotification(`✓ 图片已优化，大小减少${result.compression_ratio.toFixed(0)}%`, 'success');

            } else if (result.status === 'failed') {
                clearInterval(poll);
                console.warn('图片优化失败，继续使用原图');
            }

        } catch (error) {
            console.error('查询优化状态失败:', error);
        }

        if (attempts >= maxAttempts) {
            clearInterval(poll);
        }
    }, 2000); // 每2秒查询一次
}

// 更新为优化后的图片
function updateImageToOptimized(originalUrl, sizes, compressionRatio, insertIndex) {
    const quill = quill; // 引用全局quill实例
    const editor = quill.root;

    // 找到刚插入的图片
    const images = editor.querySelectorAll('img');
    let targetImage = null;

    for (let img of images) {
        if (img.src.includes(originalUrl)) {
            targetImage = img;
            break;
        }
    }

    if (targetImage) {
        // 创建响应式图片
        const img = targetImage;
        img.srcset = `
            ${sizes.thumbnail} 150w,
            ${sizes.medium} 600w,
            ${sizes.large} 1200w
        `.trim().replace(/\s+/g, ' ');

        img.sizes = '(max-width: 600px) 150px, (max-width: 1200px) 600px, 1200w';
        img.src = sizes.medium; // 默认使用中等尺寸

        // 显示优化徽章
        showOptimizationBadge(img, compressionRatio);
    }
}

// 显示优化徽章
function showOptimizationBadge(imgElement, compressionRatio) {
    const badge = document.createElement('div');
    badge.className = 'image-optimized-badge';
    badge.textContent = `✓ 已优化 ${compressionRatio.toFixed(0)}%`;
    badge.style.cssText = `
        position: absolute;
        top: 5px;
        right: 5px;
        background: rgba(0, 200, 0, 0.9);
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 10;
        pointer-events: none;
    `;

    imgElement.style.position = imgElement.style.position || 'relative';

    // 插入徽章到图片的父元素
    if (imgElement.parentNode) {
        imgElement.parentNode.style.position = 'relative';
        imgElement.parentNode.appendChild(badge);
    }

    // 3秒后移除
    setTimeout(() => badge.remove(), 3000);
}
```

- [ ] **Step 2: Test image optimization in editor**

1. Open editor page
2. Insert image using toolbar button
3. Upload an image file
4. Image should appear immediately
5. Wait 3-5 seconds
6. Image should refresh with optimized version
7. Green badge should appear "✓ 已优化 85%"
8. Badge should disappear after 3 seconds

- [ ] **Step 3: Commit image optimization frontend**

```bash
git add static/js/editor.js
git commit -m "feat: integrate image optimization with editor

- Modify image upload to return immediately
- Poll optimization status every 2 seconds
- Update to responsive images with srcset
- Show optimization progress badge
- Fallback to original on optimization failure

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Final Testing & Documentation

### Task 9: Integration Testing

- [ ] **Step 1: Test all features together**

1. **Keyboard Shortcuts**:
   - [ ] Press Ctrl+K - search focuses
   - [ ] Press Ctrl+N - navigates to new post
   - [ ] Press Ctrl+/ - help modal shows
   - [ ] In editor: Ctrl+B, Ctrl+I work
   - [ ] ESC closes modals

2. **Breadcrumb Navigation**:
   - [ ] Visit post page
   - [ ] Breadcrumb shows correct path
   - [ ] Click links navigate correctly
   - [ ] Mobile: long titles truncate

3. **Asset Versioning**:
   - [ ] CSS/JS have hash in filenames
   - [ ] Edit a CSS file
   - [ ] Regenerate manifest
   - [ ] Refresh - new hash loads

4. **Draft Sync**:
   - [ ] Create article in browser A
   - [ ] Edit same in browser B
   - [ ] Conflict dialog appears
   - [ ] Resolution options work
   - [ ] 30s auto-save works

5. **Image Optimization**:
   - [ ] Upload image
   - [ ] Immediate response
   - [ ] Optimization completes
   - [ ] Responsive images work
   - [ ] Badge shows compression

- [ ] **Step 2: Performance testing**

```bash
# Test image compression
python -c "
from pathlib import Path
original = Path('static/uploads/test.jpg')
optimized = Path('static/uploads/optimized/test_medium.webp')
print(f'Original: {original.stat().st_size / 1024:.1f} KB')
print(f'Optimized: {optimized.stat().st_size / 1024:.1f} KB')
"

# Test page load with Lighthouse
npx lighthouse http://localhost:5001 --view
```

- [ ] **Step 3: Create deployment checklist**

Create `docs/deployment/ux-enhancements-checklist.md`:

```markdown
# UX Enhancements Deployment Checklist

## Pre-Deployment

- [ ] Run database migrations
  ```bash
  python backend/migrations/migrate_drafts.py
  python backend/migrations/migrate_image_optimization.py
  ```

- [ ] Generate asset manifest
  ```bash
  python -c "from backend.app import app; app.app_context().push(); app.asset_manager.regenerate()"
  ```

- [ ] Test all features locally
- [ ] Backup database
- [ ] Review configuration settings

## Post-Deployment

- [ ] Verify database tables created
- [ ] Check manifest.json exists
- [ ] Test keyboard shortcuts
- [ ] Test draft sync on mobile
- [ ] Upload test image and verify optimization
- [ ] Check browser console for errors
- [ ] Monitor logs for first hour

## Rollback Plan

If issues occur:
1. Disable feature flags in config (add to config.py):
   ```python
   FEATURE_DRAFT_SYNC = False
   FEATURE_IMAGE_OPTIMIZATION = False
   ```
2. Restart application
3. If database issues: run rollback migrations:
   ```bash
   python backend/migrations/rollback_drafts.py
   python backend/migrations/rollback_image_optimization.py
   ```
4. Restore database from backup if needed
```

- [ ] **Step 4: Update README**

Add to `README.md`:

```markdown
## 新功能（v2.2）

### ⌨️ 键盘快捷键
- Ctrl+K: 快速搜索
- Ctrl+N: 新建文章
- Ctrl+/: 查看所有快捷键
- 编辑器: Ctrl+B (加粗), Ctrl+I (斜体)

### 💾 多设备草稿同步
- 编辑器每30秒自动保存
- 多设备编辑时自动检测冲突
- 支持草稿恢复和合并

### 🖼️ 图片自动优化
- 上传图片后自动压缩
- 生成多种尺寸（缩略图、中等、大图）
- 转换为WebP格式，平均减少85%大小

### 🍞 面包屑导航
- 文章页显示导航路径
- SEO优化的结构化数据

### ⚡ 性能优化
- 静态资源自动版本管理
- 响应式图片加载
```

- [ ] **Step 5: Final commit**

```bash
git add README.md docs/deployment/ux-enhancements-checklist.md
git commit -m "docs: add deployment documentation for UX enhancements

- Add deployment checklist
- Update README with new features
- Include rollback procedures
- Document configuration changes

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Implementation Complete Checklist

### Phase 1: Quick Wins ✅
- [x] Task 1: Keyboard Shortcuts Enhancement
- [x] Task 2: Breadcrumb Navigation
- [x] Task 3: Static Asset Auto-Versioning

### Phase 2: Complex Features ✅
- [x] Task 4: Database Migrations
- [x] Task 5: Draft Sync Backend API
- [x] Task 6: Draft Sync Frontend
- [x] Task 7: Image Optimization Backend
- [x] Task 8: Image Optimization Frontend

### Final Phase ✅
- [x] Task 9: Integration Testing & Documentation

---

## Success Criteria

All features implemented when:
- ✅ All keyboard shortcuts work across pages
- ✅ Breadcrumb appears on all post pages
- ✅ CSS/JS use auto-generated version hashes
- ✅ Drafts sync between devices with conflict resolution
- ✅ Images auto-optimize with 80%+ size reduction
- ✅ Integration tests pass
- ✅ Documentation complete
- ✅ Zero breaking changes to existing features

---

**Plan Version**: 1.0
**Created**: 2026-03-13
**Estimated Duration**: 2-3 weeks
**Dependencies**: Python 3.11+, Flask 3.0, SQLite 3.38+, Pillow
