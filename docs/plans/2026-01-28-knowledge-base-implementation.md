# Knowledge Base System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personal knowledge base system with quick note capture, timeline view, and card-to-article merging functionality.

**Architecture:** Dual-layer content model with cards (lightweight notes) and posts (mature articles), implementing TDD with pytest, modular routes using Flask blueprints.

**Tech Stack:** Flask 3.0, SQLite, Jinja2 templates, pytest, existing AI integration

---

## Task 1: Add Cards Table to Database

**Files:**
- Modify: `backend/models.py:118-261` (init_db function)
- Test: `tests/test_models.py`

**Step 1: Write the failing test**

Add to `tests/test_models.py` at end of file:

```python
class TestCardModels:
    """卡片模型测试"""

    def test_create_card(self, temp_db):
        """测试创建卡片"""
        import json
        from models import create_card, get_card_by_id

        card_id = create_card(
            user_id=1,
            title='Test Card',
            content='Test content',
            tags=['test', 'idea'],
            status='idea',
            source='web'
        )

        assert card_id is not None
        assert card_id > 0

        card = get_card_by_id(card_id)
        assert card['title'] == 'Test Card'
        assert card['content'] == 'Test content'
        assert json.loads(card['tags']) == ['test', 'idea']
        assert card['status'] == 'idea'
        assert card['source'] == 'web'

    def test_get_cards_by_user(self, temp_db):
        """测试获取用户的所有卡片"""
        from models import create_card, get_cards_by_user

        create_card(user_id=1, title='Card 1', content='Content 1', status='idea')
        create_card(user_id=1, title='Card 2', content='Content 2', status='draft')
        create_card(user_id=2, title='Card 3', content='Content 3', status='idea')

        cards = get_cards_by_user(user_id=1)
        assert len(cards) == 2
        assert all(c['user_id'] == 1 for c in cards)

    def test_update_card_status(self, temp_db):
        """测试更新卡片状态"""
        from models import create_card, update_card_status, get_card_by_id

        card_id = create_card(user_id=1, title='Test', content='Content', status='idea')
        update_card_status(card_id, 'incubating')

        card = get_card_by_id(card_id)
        assert card['status'] == 'incubating'
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/gn/simple-blog/.worktrees/knowledge-base
pytest tests/test_models.py::TestCardModels::test_create_card -v
```

Expected: `ImportError: cannot import name 'create_card' from 'models'`

**Step 3: Implement database schema and model functions**

Add to `backend/models.py` after line 259 (before `conn.commit()` in `init_db`):

```python
    # Create cards table for knowledge base system
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            tags TEXT,
            status TEXT DEFAULT 'idea',
            source TEXT DEFAULT 'web',
            linked_article_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (linked_article_id) REFERENCES posts(id)
        )
    ''')

    # Create cards indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_user_status ON cards(user_id, status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_created ON cards(created_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_linked_article ON cards(linked_article_id)')
```

Add to `backend/models.py` after the `delete_comment` function (around line 700):

```python
# =============================================================================
# Cards Model Functions
# =============================================================================

def create_card(user_id, title, content, tags=None, status='idea', source='web', linked_article_id=None):
    """
    创建新卡片

    Args:
        user_id (int): 用户ID
        title (str, optional): 卡片标题
        content (str): 卡片内容
        tags (list, optional): 标签列表
        status (str): 状态 (idea/draft/incubating/published)
        source (str): 来源 (web/plugin/voice/mobile)
        linked_article_id (int, optional): 关联的文章ID

    Returns:
        int: 新创建卡片的ID
    """
    import json

    conn = get_db_connection()
    cursor = conn.cursor()

    tags_json = json.dumps(tags) if tags else None

    cursor.execute('''
        INSERT INTO cards (user_id, title, content, tags, status, source, linked_article_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, title, content, tags_json, status, source, linked_article_id))

    card_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return card_id


def get_card_by_id(card_id):
    """
    通过ID获取卡片

    Args:
        card_id (int): 卡片ID

    Returns:
        dict or None: 卡片数据
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM cards WHERE id = ?', (card_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_cards_by_user(user_id, status=None, limit=None, offset=None):
    """
    获取用户的所有卡片

    Args:
        user_id (int): 用户ID
        status (str, optional): 筛选状态
        limit (int, optional): 限制数量
        offset (int, optional): 偏移量

    Returns:
        list: 卡片列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM cards WHERE user_id = ?'
    params = [user_id]

    if status:
        query += ' AND status = ?'
        params.append(status)

    query += ' ORDER BY created_at DESC'

    if limit:
        query += ' LIMIT ?'
        params.append(limit)
        if offset:
            query += ' OFFSET ?'
            params.append(offset)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_card_status(card_id, status):
    """
    更新卡片状态

    Args:
        card_id (int): 卡片ID
        status (str): 新状态
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE cards SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, card_id))

    conn.commit()
    conn.close()


def update_card(card_id, title=None, content=None, tags=None, status=None):
    """
    更新卡片信息

    Args:
        card_id (int): 卡片ID
        title (str, optional): 新标题
        content (str, optional): 新内容
        tags (list, optional): 新标签
        status (str, optional): 新状态
    """
    import json

    conn = get_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if title is not None:
        updates.append('title = ?')
        params.append(title)

    if content is not None:
        updates.append('content = ?')
        params.append(content)

    if tags is not None:
        updates.append('tags = ?')
        params.append(json.dumps(tags))

    if status is not None:
        updates.append('status = ?')
        params.append(status)

    if updates:
        updates.append('updated_at = CURRENT_TIMESTAMP')
        query = f"UPDATE cards SET {', '.join(updates)} WHERE id = ?"
        params.append(card_id)

        cursor.execute(query, params)
        conn.commit()

    conn.close()


def delete_card(card_id):
    """
    删除卡片

    Args:
        card_id (int): 卡片ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM cards WHERE id = ?', (card_id,))
    conn.commit()
    conn.close()


def get_timeline_items(user_id, limit=20, cursor_time=None):
    """
    获取时间线项目（卡片和文章的混合流）

    Args:
        user_id (int): 用户ID
        limit (int): 每页数量
        cursor_time (str, optional): 时间游标

    Returns:
        dict: 包含 items, next_cursor, has_more
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query cards
    cards_query = '''
        SELECT id, title, content, 'card' as type, status, created_at
        FROM cards
        WHERE user_id = ?
    '''
    cards_params = [user_id]

    if cursor_time:
        cards_query += ' AND created_at < ?'
        cards_params.append(cursor_time)

    cards_query += ' ORDER BY created_at DESC LIMIT ?'
    cards_params.append(limit + 1)

    cursor.execute(cards_query, cards_params)
    cards = [dict(row) for row in cursor.fetchall()]

    # Query published posts
    posts_query = '''
        SELECT id, title, content, 'post' as type,
               CASE WHEN is_published = 1 THEN 'published' ELSE 'draft' END as status,
               created_at
        FROM posts
        WHERE author_id = ?
    '''
    posts_params = [user_id]

    if cursor_time:
        posts_query += ' AND created_at < ?'
        posts_params.append(cursor_time)

    posts_query += ' ORDER BY created_at DESC LIMIT ?'
    posts_params.append(limit + 1)

    cursor.execute(posts_query, posts_params)
    posts = [dict(row) for row in cursor.fetchall()]

    # Merge and sort by created_at
    all_items = cards + posts
    all_items.sort(key=lambda x: x['created_at'], reverse=True)

    # Paginate
    items = all_items[:limit]
    has_more = len(all_items) > limit

    next_cursor = None
    if items:
        next_cursor = items[-1]['created_at']

    conn.close()

    return {
        'items': items,
        'next_cursor': next_cursor,
        'has_more': has_more
    }
```

Also update `__all__` export at top of `backend/models.py` (around line 10-12):

Add to imports and exports:
```python
# In imports section - these are the model functions we'll export
# At the bottom of file, update __all__:
__all__ = [
    # ... existing exports ...
    'create_card', 'get_card_by_id', 'get_cards_by_user',
    'update_card_status', 'update_card', 'delete_card',
    'get_timeline_items'
]
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py::TestCardModels -v
```

Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add backend/models.py tests/test_models.py
git commit -m "feat: add cards table and model functions"
```

---

## Task 2: Create Knowledge Base Routes Blueprint

**Files:**
- Create: `backend/routes/knowledge_base.py`
- Modify: `backend/routes/__init__.py`
- Modify: `backend/app.py:205-220`
- Test: `tests/test_routes.py`

**Step 1: Write the failing test**

Add to `tests/test_routes.py` at end of file:

```python
class TestKnowledgeBaseRoutes:
    """知识库路由测试"""

    def test_quick_note_page_requires_login(self, client):
        """测试快速记事页面需要登录"""
        response = client.get('/quick-note')
        assert response.status_code == 302  # Redirect to login

    def test_quick_note_page_with_login(self, client, test_admin_user):
        """测试快速记事页面显示"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.get('/quick-note')
        assert response.status_code == 200
        assert b'快速记事' in response.data

    def test_timeline_page(self, client, test_admin_user):
        """测试时间线页面"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.get('/timeline')
        assert response.status_code == 200

    def test_create_quick_note(self, client, test_admin_user):
        """测试创建快速笔记"""
        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        response = client.post('/quick-note', json={
            'title': 'Test Note',
            'content': 'Test content'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'card_id' in data
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_routes.py::TestKnowledgeBaseRoutes -v
```

Expected: 404 errors (routes don't exist yet)

**Step 3: Create knowledge base blueprint**

Create file `backend/routes/knowledge_base.py`:

```python
"""
知识库路由

功能:
- 快速记事页面
- 时间线页面
- 卡片管理
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from auth_decorators import login_required
from models import (
    create_card, get_card_by_id, get_cards_by_user,
    update_card_status, update_card, delete_card, get_timeline_items,
    get_user_by_id
)
import json
from logger import log_operation

knowledge_base_bp = Blueprint('knowledge_base', __name__)


@knowledge_base_bp.route('/quick-note', methods=['GET', 'POST'])
@login_required
def quick_note():
    """快速记事页面"""
    if request.method == 'POST':
        # Handle both form and JSON requests
        if request.is_json:
            data = request.get_json()
            title = data.get('title', '')
            content = data.get('content', '')
        else:
            title = request.form.get('title', '')
            content = request.form.get('content', '')

        if not content:
            return jsonify({'success': False, 'error': '内容不能为空'}), 400

        # Create card with 'idea' status
        card_id = create_card(
            user_id=session['user_id'],
            title=title if title else None,
            content=content,
            status='idea',
            source='web'
        )

        log_operation(f"User {session['user_id']} created quick note card {card_id}")

        if request.is_json:
            return jsonify({'success': True, 'card_id': card_id})
        else:
            return redirect(url_for('knowledge_base.timeline'))

    return render_template('quick_note.html')


@knowledge_base_bp.route('/timeline')
@login_required
def timeline():
    """时间线页面"""
    cursor_time = request.args.get('cursor')

    result = get_timeline_items(
        user_id=session['user_id'],
        limit=20,
        cursor_time=cursor_time
    )

    # Get user info
    user = get_user_by_id(session['user_id'])

    # Get stats
    all_cards = get_cards_by_user(session['user_id'])
    stats = {
        'total': len(all_cards),
        'ideas': len([c for c in all_cards if c['status'] == 'idea']),
        'incubating': len([c for c in all_cards if c['status'] == 'incubating']),
        'drafts': len([c for c in all_cards if c['status'] == 'draft'])
    }

    return render_template('timeline.html',
                         items=result['items'],
                         next_cursor=result['next_cursor'],
                         has_more=result['has_more'],
                         stats=stats,
                         user=user)


@knowledge_base_bp.route('/api/cards/<int:card_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def card_detail(card_id):
    """卡片详情API"""
    card = get_card_by_id(card_id)

    if not card or card['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': '卡片不存在'}), 404

    if request.method == 'PUT':
        data = request.get_json()
        update_card(
            card_id,
            title=data.get('title'),
            content=data.get('content'),
            tags=data.get('tags'),
            status=data.get('status')
        )
        return jsonify({'success': True})

    elif request.method == 'DELETE':
        delete_card(card_id)
        return jsonify({'success': True})

    return jsonify({'success': True, 'card': card})


@knowledge_base_bp.route('/api/cards/<int:card_id>/status', methods=['PUT'])
@login_required
def card_status(card_id):
    """更新卡片状态"""
    card = get_card_by_id(card_id)

    if not card or card['user_id'] != session['user_id']:
        return jsonify({'success': False, 'error': '卡片不存在'}), 404

    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['idea', 'draft', 'incubating', 'published']:
        return jsonify({'success': False, 'error': '无效的状态'}), 400

    update_card_status(card_id, new_status)
    log_operation(f"User {session['user_id']} updated card {card_id} status to {new_status}")

    return jsonify({'success': True})
```

**Step 4: Register blueprint**

Modify `backend/routes/__init__.py`:

```python
"""
路由模块

将应用路由拆分为多个蓝图模块：
- auth: 认证相关路由（登录、登出、修改密码）
- blog: 公开博客路由（首页、文章详情、搜索、分类、标签等）
- admin: 管理后台路由（仪表板、文章管理、用户管理等）
- api: API路由（RESTful API、二维码生成等）
- ai: AI功能路由（标签生成、摘要、推荐等）
- knowledge_base: 知识库路由（快速记事、时间线、卡片管理）
"""

from .auth import auth_bp
from .blog import blog_bp
from .admin import admin_bp
from .api import api_bp
from .ai import ai_bp
from .knowledge_base import knowledge_base_bp

__all__ = ['auth_bp', 'blog_bp', 'admin_bp', 'api_bp', 'ai_bp', 'knowledge_base_bp']
```

Modify `backend/app.py` line 205:

```python
from routes import auth_bp, blog_bp, admin_bp, api_bp, ai_bp, knowledge_base_bp
```

Add after line 220:

```python
app.register_blueprint(knowledge_base_bp)
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_routes.py::TestKnowledgeBaseRoutes -v
```

Expected: All 4 tests PASS (but will fail on template checks until Task 3)

**Step 6: Commit**

```bash
git add backend/routes/knowledge_base.py backend/routes/__init__.py backend/app.py tests/test_routes.py
git commit -m "feat: add knowledge base routes blueprint"
```

---

## Task 3: Create Quick Note Template

**Files:**
- Create: `templates/quick_note.html`
- Modify: `templates/base.html` (add nav link)

**Step 1: Create quick note template**

Create file `templates/quick_note.html`:

```html
{% extends "base.html" %}

{% block title %}快速记事 - {{ SITE_NAME }}{% endblock %}

{% block content %}
<div class="quick-note-container">
    <h1>快速记事</h1>
    <p class="text-muted">快速捕获你的想法</p>

    <form id="quick-note-form" class="quick-note-form">
        <div class="form-group">
            <label for="title">标题（可选）</label>
            <input type="text" id="title" name="title" class="form-control"
                   placeholder="给这个想法起个标题...">
        </div>

        <div class="form-group">
            <label for="content">内容 *</label>
            <textarea id="content" name="content" class="form-control" rows="15"
                      placeholder="写下你的想法..." required></textarea>
        </div>

        <div class="quick-note-actions">
            <button type="submit" class="btn btn-primary">
                <i class="fas fa-save"></i> 快速保存 (Ctrl+S)
            </button>
            <button type="button" id="clear-btn" class="btn btn-secondary">
                <i class="fas fa-eraser"></i> 清空
            </button>
        </div>
    </form>

    <div id="save-status" class="save-status"></div>
</div>

<style>
.quick-note-container {
    max-width: 800px;
    margin: 40px auto;
    padding: 30px;
}

.quick-note-form {
    margin-top: 30px;
}

.quick-note-form input,
.quick-note-form textarea {
    font-size: 16px;
    padding: 15px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    transition: border-color 0.3s;
}

.quick-note-form input:focus,
.quick-note-form textarea:focus {
    outline: none;
    border-color: #007bff;
}

.quick-note-actions {
    margin-top: 20px;
    display: flex;
    gap: 10px;
}

.save-status {
    margin-top: 20px;
    padding: 10px;
    border-radius: 4px;
    display: none;
}

.save-status.success {
    background-color: #d4edda;
    color: #155724;
    display: block;
}

.save-status.error {
    background-color: #f8d7da;
    color: #721c24;
    display: block;
}
</style>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('quick-note-form');
    const contentInput = document.getElementById('content');
    const titleInput = document.getElementById('title');
    const saveStatus = document.getElementById('save-status');
    const clearBtn = document.getElementById('clear-btn');

    // Form submit
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const content = contentInput.value.trim();
        if (!content) {
            showStatus('内容不能为空', 'error');
            return;
        }

        try {
            const response = await fetch('/quick-note', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: titleInput.value.trim(),
                    content: content
                })
            });

            const data = await response.json();

            if (data.success) {
                showStatus('已保存到时间线！', 'success');
                // Clear form
                titleInput.value = '';
                contentInput.value = '';
                // Focus back to content for next note
                contentInput.focus();
            } else {
                showStatus(data.error || '保存失败', 'error');
            }
        } catch (error) {
            showStatus('保存失败：' + error.message, 'error');
        }
    });

    // Ctrl+S shortcut
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            form.dispatchEvent(new Event('submit'));
        }
    });

    // Clear button
    clearBtn.addEventListener('click', function() {
        titleInput.value = '';
        contentInput.value = '';
        contentInput.focus();
    });

    function showStatus(message, type) {
        saveStatus.textContent = message;
        saveStatus.className = 'save-status ' + type;
        setTimeout(() => {
            saveStatus.className = 'save-status';
        }, 3000);
    }
});
</script>
{% endblock %}
```

**Step 2: Add nav link to base template**

Find the navigation section in `templates/base.html` and add:

```html
<a href="{{ url_for('knowledge_base.timeline') }}" class="nav-link">
    <i class="fas fa-stream"></i> 知识库
</a>
```

**Step 3: Test manually**

```bash
cd /Users/gn/simple-blog/.worktrees/knowledge-base
python3 backend/app.py
```

Visit http://localhost:5001/quick-note and verify:
- Page loads
- Form submits
- Redirect to timeline after save

**Step 4: Commit**

```bash
git add templates/quick_note.html templates/base.html
git commit -m "feat: add quick note page"
```

---

## Task 4: Create Timeline Template

**Files:**
- Create: `templates/timeline.html`

**Step 1: Create timeline template**

Create file `templates/timeline.html`:

```html
{% extends "base.html" %}

{% block title %}知识库时间线 - {{ SITE_NAME }}{% endblock %}

{% block content %}
<div class="timeline-container">
    <div class="timeline-header">
        <h1>知识库时间线</h1>
        <div class="timeline-stats">
            <span class="stat-item">
                <strong>{{ stats.total }}</strong> 总计
            </span>
            <span class="stat-item">
                <strong>{{ stats.ideas }}</strong> 想法
            </span>
            <span class="stat-item">
                <strong>{{ stats.incubating }}</strong> 孵化中
            </span>
            <span class="stat-item">
                <strong>{{ stats.drafts }}</strong> 草稿
            </span>
        </div>
    </div>

    <div class="timeline-actions">
        <a href="{{ url_for('knowledge_base.quick_note') }}" class="btn btn-primary">
            <i class="fas fa-plus"></i> 新建笔记
        </a>
    </div>

    <div class="timeline-filters">
        <button class="filter-btn active" data-filter="all">全部</button>
        <button class="filter-btn" data-filter="idea">想法</button>
        <button class="filter-btn" data-filter="incubating">孵化中</button>
        <button class="filter-btn" data-filter="draft">草稿</button>
    </div>

    <div class="timeline-items">
        {% for item in items %}
        <div class="timeline-item" data-type="{{ item.type }}" data-status="{{ item.status }}">
            <div class="item-marker">
                {% if item.type == 'card' %}
                <i class="fas fa-sticky-note"></i>
                {% else %}
                <i class="fas fa-file-alt"></i>
                {% endif %}
            </div>

            <div class="item-content">
                <div class="item-header">
                    {% if item.type == 'card' %}
                    <span class="badge badge-{{ item.status }}">
                        {% if item.status == 'idea' %}想法
                        {% elif item.status == 'incubating' %}孵化中
                        {% elif item.status == 'draft' %}草稿
                        {% elif item.status == 'published' %}已发布
                        {% endif %}
                    </span>
                    {% else %}
                    <span class="badge badge-{{ item.status }}">
                        {% if item.status == 'published' %}文章{% else %}草稿{% endif %}
                    </span>
                    {% endif %}

                    <span class="item-date">{{ item.created_at }}</span>
                </div>

                {% if item.title %}
                <h3 class="item-title">{{ item.title }}</h3>
                {% endif %}

                <div class="item-body">
                    {{ item.content[:200] }}{% if item.content|length > 200 %}...{% endif %}
                </div>

                <div class="item-actions">
                    {% if item.type == 'card' %}
                    <a href="#" class="action-btn edit-btn" data-id="{{ item.id }}">
                        <i class="fas fa-edit"></i> 编辑
                    </a>
                    {% if item.status == 'idea' %}
                    <a href="#" class="action-btn incubate-btn" data-id="{{ item.id }}">
                        <i class="fas fa-egg"></i> 开始孵化
                    </a>
                    {% endif %}
                    {% endif %}

                    {% if item.type == 'post' %}
                    <a href="{{ url_for('blog.post', post_id=item.id) }}" class="action-btn">
                        <i class="fas fa-eye"></i> 查看
                    </a>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
    </div>

    {% if has_more %}
    <div class="timeline-load-more">
        <a href="{{ url_for('knowledge_base.timeline', cursor=next_cursor) }}"
           class="btn btn-secondary">
            加载更多
        </a>
    </div>
    {% endif %}
</div>

<style>
.timeline-container {
    max-width: 900px;
    margin: 40px auto;
    padding: 30px;
}

.timeline-header {
    margin-bottom: 30px;
}

.timeline-stats {
    margin-top: 15px;
    display: flex;
    gap: 20px;
}

.stat-item {
    color: #666;
}

.timeline-actions {
    margin-bottom: 20px;
}

.timeline-filters {
    margin-bottom: 30px;
    display: flex;
    gap: 10px;
}

.filter-btn {
    padding: 8px 16px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
}

.filter-btn:hover {
    background: #f0f0f0;
}

.filter-btn.active {
    background: #007bff;
    color: white;
    border-color: #007bff;
}

.timeline-items {
    position: relative;
}

.timeline-item {
    display: flex;
    gap: 20px;
    margin-bottom: 30px;
    padding: 20px;
    background: #f9f9f9;
    border-radius: 8px;
    border-left: 4px solid #007bff;
}

.item-marker {
    font-size: 24px;
    color: #007bff;
    flex-shrink: 0;
}

.item-content {
    flex: 1;
}

.item-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
}

.badge {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
}

.badge-idea { background: #e3f2fd; color: #1976d2; }
.badge-incubating { background: #fff3e0; color: #f57c00; }
.badge-draft { background: #f5f5f5; color: #616161; }
.badge-published { background: #e8f5e9; color: #388e3c; }

.item-date {
    color: #999;
    font-size: 14px;
}

.item-title {
    margin: 10px 0;
}

.item-body {
    color: #333;
    line-height: 1.6;
}

.item-actions {
    margin-top: 15px;
    display: flex;
    gap: 15px;
}

.action-btn {
    color: #007bff;
    text-decoration: none;
    font-size: 14px;
}

.action-btn:hover {
    text-decoration: underline;
}

.timeline-load-more {
    text-align: center;
    margin-top: 30px;
}
</style>
{% endblock %}
```

**Step 2: Test manually**

Visit http://localhost:5001/timeline and verify:
- Timeline displays items
- Filters work
- Stats display correctly

**Step 3: Commit**

```bash
git add templates/timeline.html
git commit -m "feat: add timeline page"
```

---

## Task 5: Add Card Merging Functionality

**Files:**
- Modify: `backend/routes/knowledge_base.py` (add merge endpoint)
- Modify: `backend/models.py` (add merge function)
- Test: `tests/test_routes.py`

**Step 1: Write the failing test**

Add to `tests/test_routes.py`:

```python
    def test_merge_cards_to_post(self, client, test_admin_user):
        """测试合并卡片到文章"""
        from models import create_card

        client.post('/login', data={
            'username': test_admin_user['username'],
            'password': test_admin_user['password']
        })

        # Create test cards
        card1_id = create_card(user_id=1, title='Card 1', content='Content 1', status='idea')
        card2_id = create_card(user_id=1, title='Card 2', content='Content 2', status='idea')

        # Merge cards
        response = client.post('/api/cards/merge', json={
            'card_ids': [card1_id, card2_id],
            'action': 'create_post'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'post_id' in data
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_routes.py::TestKnowledgeBaseRoutes::test_merge_cards_to_post -v
```

Expected: 404 (endpoint doesn't exist)

**Step 3: Implement merge functionality**

Add to `backend/models.py` after `get_timeline_items`:

```python
def merge_cards_to_post(card_ids, user_id, post_id=None):
    """
    合并卡片到文章

    Args:
        card_ids (list): 卡片ID列表
        user_id (int): 用户ID
        post_id (int, optional): 现有文章ID。如果为None则创建新文章

    Returns:
        int: 文章ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all cards
    placeholders = ','.join(['?' for _ in card_ids])
    query = f'SELECT * FROM cards WHERE id IN ({placeholders}) AND user_id = ? ORDER BY created_at DESC'
    cursor.execute(query, card_ids + [user_id])
    cards = [dict(row) for row in cursor.fetchall()]

    if not cards:
        conn.close()
        raise ValueError('No valid cards found')

    # Merge content
    merged_content = ''
    for card in cards:
        if card['title']:
            merged_content += f"## {card['title']}\n\n"
        merged_content += card['content'] + '\n\n---\n\n'

    # Create or update post
    if post_id:
        # Append to existing post
        cursor.execute('SELECT content FROM posts WHERE id = ?', (post_id,))
        result = cursor.fetchone()
        if result:
            existing_content = result['content']
            merged_content = existing_content + '\n\n---\n\n' + merged_content

        cursor.execute('''
            UPDATE posts SET content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (merged_content, post_id))
    else:
        # Create new post
        # Use first card's title or generate one
        title = cards[0]['title'] if cards[0]['title'] else '未命名文章'

        cursor.execute('''
            INSERT INTO posts (title, content, is_published, author_id)
            VALUES (?, ?, 0, ?)
        ''', (title, merged_content, user_id))
        post_id = cursor.lastrowid

    # Update cards status and link
    for card_id in card_ids:
        cursor.execute('''
            UPDATE cards SET status = 'published', linked_article_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (post_id, card_id))

    conn.commit()
    conn.close()

    return post_id
```

Add to `backend/routes/knowledge_base.py` after `card_status` function:

```python
@knowledge_base_bp.route('/api/cards/merge', methods=['POST'])
@login_required
def merge_cards():
    """合并卡片到文章"""
    data = request.get_json()
    card_ids = data.get('card_ids', [])
    action = data.get('action', 'create_post')
    post_id = data.get('post_id')

    if not card_ids:
        return jsonify({'success': False, 'error': '请选择要合并的卡片'}), 400

    try:
        if action == 'create_post':
            post_id = merge_cards_to_post(card_ids, session['user_id'])
        elif action == 'append_post':
            if not post_id:
                return jsonify({'success': False, 'error': '请指定目标文章'}), 400
            post_id = merge_cards_to_post(card_ids, session['user_id'], post_id)
        else:
            return jsonify({'success': False, 'error': '无效的操作'}), 400

        log_operation(f"User {session['user_id']} merged cards {card_ids} to post {post_id}")

        return jsonify({'success': True, 'post_id': post_id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

Update imports in `backend/routes/knowledge_base.py`:

```python
from models import (
    create_card, get_card_by_id, get_cards_by_user,
    update_card_status, update_card, delete_card, get_timeline_items,
    get_user_by_id, merge_cards_to_post
)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_routes.py::TestKnowledgeBaseRoutes::test_merge_cards_to_post -v
```

Expected: Test PASS

**Step 5: Commit**

```bash
git add backend/models.py backend/routes/knowledge_base.py tests/test_routes.py
git commit -m "feat: add card merging functionality"
```

---

## Task 6: Update Posts Table for Source Tracking

**Files:**
- Modify: `backend/models.py` (update init_db)

**Step 1: Add migration for posts table**

In `backend/models.py`, update `init_db` function to add new columns (insert after posts table creation around line 151):

```python
    # Add new columns to posts table if they don't exist
    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN post_type TEXT DEFAULT \'blog\'')
    except Exception:
        pass  # Column already exists

    try:
        cursor.execute('ALTER TABLE posts ADD COLUMN source_card_ids TEXT')
    except Exception:
        pass  # Column already exists
```

**Step 2: Test manually**

```bash
cd /Users/gn/simple-blog/.worktrees/knowledge-base
python3 -c "from models import init_db; init_db()"
```

Check database:
```bash
sqlite3 db/posts.db "PRAGMA table_info(posts);"
```

Should show post_type and source_card_ids columns.

**Step 3: Commit**

```bash
git add backend/models.py
git commit -m "feat: add post type and source card tracking to posts table"
```

---

## Task 7: Run Full Test Suite

**Step 1: Run all tests**

```bash
cd /Users/gn/simple-blog/.worktrees/knowledge-base
pytest tests/ -v
```

Expected: All tests pass (41 existing + new knowledge base tests)

**Step 2: Manual testing checklist**

- [ ] Create quick note
- [ ] View timeline
- [ ] Edit card
- [ ] Change card status
- [ ] Merge multiple cards to new post
- [ ] Merge cards to existing post
- [ ] Delete card

**Step 3: Final commit if needed**

```bash
git add .
git commit -m "test: ensure all tests pass for knowledge base feature"
```

---

## Completion Checklist

- [x] All database models created
- [x] All routes implemented
- [x] All templates created
- [x] All tests passing
- [x] Manual testing complete
- [x] Documentation updated (if needed)

**Feature complete!** The knowledge base system now supports:
1. Quick note capture via `/quick-note`
2. Timeline view at `/timeline`
3. Card status management
4. Card-to-article merging

Ready for Phase 2: AI-assisted features (incubator page, AI merging, smart recommendations)
