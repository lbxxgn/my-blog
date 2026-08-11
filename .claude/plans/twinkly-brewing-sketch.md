# 统一内容流 — 融合文章、快速记事与时间线

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将快速记事、文章、时间线融合为统一的内容流，笔记保存后在首页 Feed 中可见，导航和后台管理统一。

**Architecture:** 给 `posts` 表新增 `type` 字段区分文章/笔记；快速记事保存时创建 `type='note'` 的文章；首页和后台统一渲染；导航栏"文章"改为"内容"。

**Tech Stack:** Flask, Jinja2, SQLite, Vanilla JS

---

## Context

当前系统中快速记事保存为 `cards` 表记录，和文章完全割裂，用户在首页/时间线看不到笔记内容，知识库入口藏在导航栏下拉菜单中，使用流程不连贯。

本次改动将笔记数据融入 `posts` 表，首页统一展示，导航和后台统一管理。

---

## Files Overview

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/migrations/migrate_add_post_type.py` | 新建 | 迁移脚本：给 posts 表添加 type 列 |
| `backend/models/models.py` | 修改 | `create_post`/`update_post`/`get_all_posts` 支持 type 字段 |
| `backend/routes/knowledge_base.py` | 修改 | `quick_note` 路由改为创建 note 类型文章 |
| `backend/routes/blog.py` | 修改 | `index()` 路由传递 type 字段给模板 |
| `backend/routes/admin.py` | 修改 | `admin_dashboard` 支持按类型筛选；新增笔记转文章路由 |
| `templates/index.html` | 修改 | 统一卡片渲染，笔记和文章共用样式 |
| `templates/base.html` | 修改 | 导航栏"文章"改为"内容" |
| `templates/admin/dashboard.html` | 修改 | 增加类型列、类型筛选、转文章按钮 |
| `templates/quick_note.html` | 修改 | 保存成功后提示和跳转 |
| `static/css/style.css` | 修改 | 笔记卡片 modifier 样式 |

---

## Task 1: Database Migration

**Files:**
- Create: `backend/migrations/migrate_add_post_type.py`
- Test: Run migration script, verify schema

- [ ] **Step 1: Write migration script**

Create `backend/migrations/migrate_add_post_type.py`:

```python
"""Add type column to posts table for unified content stream"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import backend.config as config


def migrate():
    """为 posts 表添加 type 列，区分文章和笔记"""
    db_path = config.DATABASE_URL.replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查 type 列是否已存在
        cursor.execute("PRAGMA table_info(posts)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'type' not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN type TEXT DEFAULT 'post'")
            print("✅ posts.type 列添加成功")
        else:
            print("ℹ️ posts.type 列已存在，跳过")

        # 为现有数据填充默认值
        cursor.execute("UPDATE posts SET type = 'post' WHERE type IS NULL")
        updated = cursor.rowcount
        print(f"✅ 已更新 {updated} 条记录的 type 为 'post'")

        # 添加索引
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_posts_type ON posts(type)'
        )
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_posts_type_created ON posts(type, created_at DESC)'
        )
        print("✅ 索引创建成功")

        conn.commit()
        print("✅ 迁移完成")

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
```

- [ ] **Step 2: Run migration**

Run: `python backend/migrations/migrate_add_post_type.py`
Expected: Migration completes successfully with column added

- [ ] **Step 3: Verify schema**

Run: `sqlite3 db/blog.db "PRAGMA table_info(posts)"`
Expected: `type` column present

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/migrate_add_post_type.py
git commit -m "feat: add post type migration for unified content stream"
```

---

## Task 2: Update Data Models

**Files:**
- Modify: `backend/models/models.py`
- Test: `tests/test_models.py` or manual verification

- [ ] **Step 1: Modify `create_post` function (line ~430)**

Add `type` parameter, default `'post'`:

```python
def create_post(title, content, is_published=False, category_id=None, author_id=None,
                access_level='public', access_password=None, type='post'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO posts (title, content, is_published, category_id, author_id, access_level, access_password, type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (title, content, is_published, category_id, author_id, access_level, access_password, type)
    )
    post_id = cursor.lastrowid
    _safe_replace_post_fts(cursor, post_id, title, content)
    conn.commit()
    conn.close()
    return post_id
```

- [ ] **Step 2: Modify `update_post` function (line ~465)**

Support updating `type` field:

```python
def update_post(post_id, title, content, is_published, category_id=None,
                access_level=None, access_password=None, type=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if access_level is not None and type is not None:
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, access_level = ?, access_password = ?, type = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, access_level, access_password, type, post_id)
        )
    elif access_level is not None:
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, access_level = ?, access_password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, access_level, access_password, post_id)
        )
    else:
        cursor.execute(
            'UPDATE posts SET title = ?, content = ?, is_published = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, content, is_published, category_id, post_id)
        )

    _safe_replace_post_fts(cursor, post_id, title, content)
    conn.commit()
    conn.close()
    return True
```

- [ ] **Step 3: Modify `get_all_posts` function (line ~512)**

Add `type` parameter to query:

```python
def get_all_posts(include_drafts=False, page=1, per_page=20, category_id=None, type=None):
    """Get all posts with pagination, optionally including drafts and filtering by category/type"""
    conn = get_db_connection()
    cursor = conn.cursor()

    where_conditions = []
    params = []

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    if category_id == 'none':
        where_conditions.append('posts.category_id IS NULL')
    elif category_id is not None:
        where_conditions.append('posts.category_id = ?')
        params.append(category_id)

    if type is not None:
        where_conditions.append('posts.type = ?')
        params.append(type)

    where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
    ...  # rest unchanged, query already selects posts.* which includes type
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/ -v -k "post" --no-header`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/models/models.py
git commit -m "feat: add type support to post CRUD operations"
```

---

## Task 3: Update Quick Note to Create Posts

**Files:**
- Modify: `backend/routes/knowledge_base.py` (quick_note route, line ~285)

- [ ] **Step 1: Modify quick_note route**

```python
@knowledge_base_bp.route('/quick-note', methods=['GET', 'POST'])
@login_required
def quick_note():
    """快速记事页面 - 保存为 note 类型文章"""
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                title = data.get('title', '')
                content = data.get('content', '')
            else:
                title = request.form.get('title', '')
                content = request.form.get('content', '')

            if not content:
                return jsonify({'success': False, 'error': '内容不能为空'}), 400

            # 自动生成标题
            from datetime import datetime
            auto_title = title if title.strip() else datetime.now().strftime('%Y-%m-%d %H:%M')

            # 创建 note 类型文章
            post_id = create_post(
                title=auto_title,
                content=content,
                is_published=True,
                type='note',
                author_id=session['user_id']
            )

            log_operation(session['user_id'], session.get('username', 'Unknown'),
                          '创建快速笔记', f'文章ID: {post_id}')

            if request.is_json:
                return jsonify({
                    'success': True,
                    'post_id': post_id,
                    'message': '笔记已保存，已在内容流中可见'
                })
            else:
                return redirect(url_for('knowledge_base.timeline'))
        except Exception as e:
            import traceback
            traceback.print_exc()
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 500
            else:
                return redirect(url_for('knowledge_base.timeline'))

    return render_template('quick_note.html')
```

- [ ] **Step 2: Add import for create_post**

At top of `knowledge_base.py`, update imports:

```python
from models import (
    create_card, get_card_by_id, get_cards_by_user,
    update_card_status, update_card, delete_card, get_timeline_items,
    get_user_by_id, merge_cards_to_post, get_user_ai_config, ai_merge_cards_to_post,
    create_annotation, get_annotations_by_url,
    create_post  # 新增
)
```

- [ ] **Step 3: Commit**

```bash
git add backend/routes/knowledge_base.py
git commit -m "feat: quick note now creates note-type posts"
```

---

## Task 4: Update Blog Index to Pass Type

**Files:**
- Modify: `backend/routes/blog.py`

- [ ] **Step 1: Modify index route to include type filter**

In `blog.py`, find the `index()` route and ensure it passes type info:

```python
@blog_bp.route('/')
def index():
    """首页 - 统一内容流"""
    cursor_time = request.args.get('cursor')
    category_id = request.args.get('category_id')

    if cursor_time:
        posts_data = get_all_posts_cursor(
            cursor_time=cursor_time,
            per_page=20,
            include_drafts=False,
            category_id=category_id
        )
    else:
        posts_data = get_all_posts(
            include_drafts=False,
            page=1,
            per_page=20,
            category_id=category_id
        )

    # type 字段已在 posts_data['posts'] 中（posts.* 查询包含所有列）
    # 处理封面图等逻辑保持不变
    ...
```

- [ ] **Step 2: Commit**

```bash
git add backend/routes/blog.py
git commit -m "feat: index route supports note-type posts"
```

---

## Task 5: Update Admin Dashboard

**Files:**
- Modify: `backend/routes/admin.py`

- [ ] **Step 1: Modify admin_dashboard to support type filter**

```python
@admin_bp.route('/')
@login_required
def admin_dashboard():
    """管理仪表板 - 列出所有内容包括笔记"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id')
    type_filter = request.args.get('type')

    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_all_posts(
        include_drafts=True,
        page=page,
        per_page=per_page,
        category_id=category_id,
        type=type_filter
    )
    categories = get_all_categories()

    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])
    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    return render_template('admin/dashboard.html',
                         posts=posts_data['posts'],
                         categories=categories,
                         pagination=posts_data,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis,
                         current_category_id=category_id,
                         current_type=type_filter)
```

- [ ] **Step 2: Add convert note to post route**

```python
@admin_bp.route('/convert-note/<int:post_id>', methods=['POST'])
@login_required
def convert_note_to_post(post_id):
    """将笔记转为正式文章"""
    post = get_post_by_id(post_id)
    if not post:
        flash('文章不存在', 'error')
        return redirect(url_for('admin_dashboard'))

    update_post(
        post_id=post_id,
        title=post['title'],
        content=post['content'],
        is_published=post['is_published'],
        category_id=post.get('category_id'),
        type='post'
    )

    log_operation(session['user_id'], session.get('username', 'Unknown'),
                  '笔记转文章', f'文章ID: {post_id}')
    flash('笔记已转为正式文章', 'success')
    return redirect(url_for('admin_dashboard'))
```

- [ ] **Step 3: Commit**

```bash
git add backend/routes/admin.py
git commit -m "feat: admin dashboard supports type filter and note conversion"
```

---

## Task 6: Update Templates — Index (Unified Cards)

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1: Modify post card rendering**

In the post loop, add type-specific rendering:

```jinja2
{% for post in posts %}
    <a href="{{ url_for('view_post', post_id=post.id) }}" class="post-card-link">
        <article class="post-card {% if post.type == 'note' %}post-card--note{% endif %}">
            <div class="post-card-content">
                <h2>
                    {% if post.type == 'note' %}
                        <span class="note-badge">笔记</span>
                    {% endif %}
                    {{ post.title }}
                </h2>
                <div class="post-meta">
                    {% if post.category_name %}
                        <span class="post-category">{{ post.category_name }}</span>
                    {% endif %}
                    {% if post.author_display_name or post.author_username %}
                        <span>👤 {{ post.author_display_name or post.author_username }}</span>
                    {% endif %}
                    <time datetime="{{ post.created_at }}">{{ post.created_at|string|truncate(10, True, '') }}</time>
                </div>
                <div class="post-excerpt">
                    {% if post.type == 'note' %}
                        {{ post.content|striptags|truncate(80) }}
                    {% else %}
                        {{ post.excerpt|default(post.content|striptags)|truncate(100) }}
                    {% endif %}
                </div>
            </div>
            {% if post.image_urls and post.type != 'note' %}
            <div class="post-card-media ...">
                {% for image_url in post.image_urls %}
                ...
                {% endfor %}
            </div>
            {% endif %}
        </article>
    </a>
{% endfor %}
```

- [ ] **Step 2: Update empty state message**

```jinja2
<div class="empty-state">
    <p>还没有发布任何内容。</p>
    <a href="{{ url_for('knowledge_base.quick_note') }}" class="btn btn-primary">写一条笔记</a>
</div>
```

- [ ] **Step 3: Commit**

```bash
git add templates/index.html
git commit -m "feat: unified card rendering for posts and notes on index"
```

---

## Task 7: Update Templates — Navigation

**Files:**
- Modify: `templates/base.html`

- [ ] **Step 1: Change "文章" to "内容"**

In base.html line ~41, change:

```jinja2
<li><a href="{{ url_for('admin_dashboard') }}">文章</a></li>
```
to:
```jinja2
<li><a href="{{ url_for('admin_dashboard') }}">内容</a></li>
```

- [ ] **Step 2: Commit**

```bash
git add templates/base.html
git commit -m "feat: rename nav '文章' to '内容' for unified content"
```

---

## Task 8: Update Templates — Admin Dashboard

**Files:**
- Modify: `templates/admin/dashboard.html`

- [ ] **Step 1: Add type filter dropdown**

After category filter:

```jinja2
<div style="display: flex; align-items: center; gap: 1rem;">
    <label for="typeFilter" style="font-weight: 500;">筛选类型：</label>
    <select id="typeFilter" onchange="filterByType()" style="padding: 0.5rem 1rem; border: 1px solid var(--border-color); border-radius: 6px; font-size: 0.95rem;">
        <option value="" {% if not current_type %}selected{% endif %}>全部</option>
        <option value="post" {% if current_type == 'post' %}selected{% endif %}>文章</option>
        <option value="note" {% if current_type == 'note' %}selected{% endif %}>笔记</option>
    </select>
</div>
```

- [ ] **Step 2: Add type column to table**

```jinja2
<thead>
    <tr>
        <th style="width: 50px;"><input type="checkbox" id="selectAll" onchange="toggleSelectAll()"></th>
        <th>标题</th>
        <th>类型</th>
        <th>分类</th>
        <th>状态</th>
        <th>创建时间</th>
        <th>操作</th>
    </tr>
</thead>
```

In tbody:
```jinja2
<td>
    {% if post.type == 'note' %}
        <span class="badge badge-note">笔记</span>
    {% else %}
        <span class="badge badge-post">文章</span>
    {% endif %}
</td>
```

- [ ] **Step 3: Add convert-to-post button for notes**

In actions column:
```jinja2
<td class="actions">
    <a href="{{ url_for('edit_post', post_id=post.id) }}" class="btn btn-sm">编辑</a>
    {% if post.type == 'note' %}
    <form method="POST" action="{{ url_for('convert_note_to_post', post_id=post.id) }}" style="display: inline;">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
        <button type="submit" class="btn btn-sm btn-info">转文章</button>
    </form>
    {% endif %}
    <form method="POST" action="{{ url_for('delete_post_route', post_id=post.id) }}" class="delete-form" ...>
        ...
    </form>
</td>
```

- [ ] **Step 4: Add filterByType JS function**

```javascript
function filterByType() {
    const type = document.getElementById('typeFilter').value;
    const url = new URL(window.location.href);
    if (type) {
        url.searchParams.set('type', type);
    } else {
        url.searchParams.delete('type');
    }
    url.searchParams.set('page', '1');
    window.location.href = url.toString();
}
```

- [ ] **Step 5: Commit**

```bash
git add templates/admin/dashboard.html
git commit -m "feat: admin dashboard with type filter and note conversion"
```

---

## Task 9: Update Templates — Quick Note Success Feedback

**Files:**
- Modify: `templates/quick_note.html`

- [ ] **Step 1: Update JS success handler**

In `templates/quick_note.html`, modify the form submit success handler:

```javascript
if (data.success) {
    closeModal();
    notify(data.message || '笔记已保存，已在内容流中可见');

    // 提供跳转选项
    setTimeout(() => {
        if (confirm('笔记已保存！去内容流查看？')) {
            window.location.href = '/';
        }
    }, 500);
}
```

- [ ] **Step 2: Commit**

```bash
git add templates/quick_note.html
git commit -m "feat: quick note save feedback with view option"
```

---

## Task 10: Add CSS for Note Cards

**Files:**
- Modify: `static/css/style.css`

- [ ] **Step 1: Add note card styles**

Append to `static/css/style.css`:

```css
/* Note card modifier - unified style with subtle differentiation */
.post-card--note {
    border-left: 3px solid var(--accent-color, #667eea);
}

.post-card--note .note-badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--accent-color, #667eea);
    background: rgba(102, 126, 234, 0.1);
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 8px;
    vertical-align: middle;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.post-card--note .post-excerpt {
    color: var(--text-secondary);
}

/* Admin badge styles */
.badge-note {
    background: rgba(102, 126, 234, 0.15);
    color: #667eea;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
}

.badge-post {
    background: rgba(26, 188, 156, 0.15);
    color: #1abc9c;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
}

.dark-theme .post-card--note {
    border-left-color: #818cf8;
}

.dark-theme .post-card--note .note-badge {
    color: #818cf8;
    background: rgba(129, 140, 248, 0.15);
}
```

- [ ] **Step 2: Commit**

```bash
git add static/css/style.css
git commit -m "feat: add note card styles for unified content stream"
```

---

## Verification

### Manual Testing Checklist

1. **数据库迁移**
   - Run migration script → check `posts` table has `type` column
   - Verify existing posts have `type = 'post'`

2. **快速记事**
   - Open home page, click FAB "快速记事"
   - Write a note, save
   - Note appears in home feed with "笔记" badge
   - Note has no image area, left border accent

3. **后台管理**
   - Go to admin dashboard
   - Filter by type: 全部 / 文章 / 笔记
   - Notes show "转文章" button
   - Click "转文章" → note becomes post, badge disappears

4. **导航**
   - Logged in: nav shows "内容" instead of "文章"
   - Click "内容" → goes to admin dashboard

5. **暗色主题**
   - Switch to dark theme
   - Note cards render correctly with accent border

### Regression Testing

```bash
python -m pytest tests/ -v --no-header
```

All existing tests should pass.
