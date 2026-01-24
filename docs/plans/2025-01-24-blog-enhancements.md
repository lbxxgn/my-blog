# 博客系统增强功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 为个人博客系统添加8项增强功能，提升用户体验和性能

**架构:** 基于现有Flask + SQLite架构，逐步添加功能模块，每个功能独立实现和测试

**技术栈:** Flask, SQLite (FTS5), CSS Variables, JavaScript (Intersection Observer, Clipboard API), qrcode库

---

## Task 1: 数据库索引优化

**Files:**
- Modify: `backend/models.py:13-54`

**Step 1: 添加索引到init_db函数**

在 `init_db()` 函数中的表创建之后添加索引：

```python
# 在 conn.commit() 之前，表创建之后添加以下代码

# 创建索引以提升查询性能
cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON posts(created_at DESC)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_published_created ON posts(is_published, created_at DESC)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_category_id ON posts(category_id)')
```

**Step 2: 运行数据库初始化**

Run: `cd backend && flask init`
Expected: 输出 "Database initialized successfully" 和索引创建信息

**Step 3: 验证索引创建**

Run: `sqlite3 db/posts.db ".indexes"`
Expected: 看到新创建的索引 `idx_created_at`, `idx_published_created`, `idx_category_id`

**Step 4: 提交**

```bash
git add backend/models.py
git commit -m "feat: add database indexes for improved query performance

- Add index on posts.created_at for chronological ordering
- Add composite index on is_published + created_at for filtered queries
- Add index on category_id for category filtering
"
```

---

## Task 2: 文章分享功能

**Files:**
- Modify: `requirements.txt`
- Modify: `backend/app.py:339`
- Modify: `templates/post.html:89`
- Create: `static/css/share.css`
- Create: `static/js/share.js`

**Step 1: 添加qrcode依赖**

在 `requirements.txt` 末尾添加：

```
qrcode==7.4.2
```

**Step 2: 安装依赖**

Run: `pip install qrcode==7.4.2`
Expected: 成功安装 qrcode 库

**Step 3: 添加QR码生成API端点**

在 `backend/app.py` 的 `upload_image` 函数之后添加：

```python
@app.route('/api/share/qrcode')
def generate_qrcode():
    """Generate QR code for WeChat sharing"""
    import qrcode
    from io import BytesIO
    import base64

    url = request.args.get('url', url_for('index', _external=True))

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({'qrcode': f'data:image/png;base64,{img_str}'})
```

**Step 4: 创建分享样式文件**

Create: `static/css/share.css`

```css
/* Share Buttons */
.share-buttons {
    display: flex;
    gap: 0.75rem;
    margin: 2rem 0;
    padding: 1.5rem 0;
    border-top: 1px solid var(--border-color);
    border-bottom: 1px solid var(--border-color);
}

.share-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background-color: var(--bg-color);
    color: var(--text-color);
    text-decoration: none;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
}

.share-btn:hover {
    background-color: var(--code-bg);
    border-color: var(--primary-color);
    color: var(--primary-color);
}

.share-btn.weibo {
    background-color: #e6162d;
    color: white;
    border-color: #e6162d;
}

.share-btn.weibo:hover {
    background-color: #c41022;
    border-color: #c41022;
}

.share-btn.wechat {
    background-color: #07c160;
    color: white;
    border-color: #07c160;
}

.share-btn.wechat:hover {
    background-color: #06ad56;
    border-color: #06ad56;
}

/* QR Code Modal */
.modal-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 2000;
    align-items: center;
    justify-content: center;
}

.modal-overlay.active {
    display: flex;
}

.modal-content {
    background-color: var(--bg-color);
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
    text-align: center;
}

.modal-content h3 {
    margin-bottom: 1rem;
}

.modal-content img {
    max-width: 200px;
    height: auto;
}

.modal-close {
    margin-top: 1rem;
}

.copy-toast {
    position: fixed;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%);
    background-color: var(--text-color);
    color: var(--bg-color);
    padding: 0.75rem 1.5rem;
    border-radius: 6px;
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
}

.copy-toast.show {
    opacity: 1;
}
```

**Step 5: 创建分享脚本**

Create: `static/js/share.js`

```javascript
// Share functionality
document.addEventListener('DOMContentLoaded', function() {
    const wechatBtn = document.querySelector('.share-btn.wechat');
    const copyBtn = document.querySelector('.share-btn.copy');
    const modal = document.querySelector('.modal-overlay');
    const modalClose = document.querySelector('.modal-close');
    const qrcodeImg = document.querySelector('.qrcode-img');
    const toast = document.querySelector('.copy-toast');

    // WeChat QR code
    if (wechatBtn && modal) {
        wechatBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            const url = window.location.href;

            try {
                const response = await fetch(`/api/share/qrcode?url=${encodeURIComponent(url)}`);
                const data = await response.json();

                if (data.qrcode) {
                    qrcodeImg.src = data.qrcode;
                    modal.classList.add('active');
                }
            } catch (error) {
                console.error('Failed to generate QR code:', error);
            }
        });
    }

    // Close modal
    if (modalClose) {
        modalClose.addEventListener('click', function() {
            modal.classList.remove('active');
        });
    }

    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    }

    // Copy link
    if (copyBtn) {
        copyBtn.addEventListener('click', async function(e) {
            e.preventDefault();

            try {
                await navigator.clipboard.writeText(window.location.href);

                // Show toast
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                }, 2000);
            } catch (error) {
                console.error('Failed to copy:', error);
            }
        });
    }
});
```

**Step 6: 在文章页面添加分享按钮**

在 `templates/post.html` 的文章内容之后，导航之前添加：

```html
<!-- Share Buttons -->
<div class="share-buttons">
    <a href="https://service.weibo.com/share/share.php?url={{ request.url_external }}&title={{ post.title }}"
       class="share-btn weibo"
       target="_blank"
       rel="noopener">
        分享到微博
    </a>
    <button class="share-btn wechat">分享到微信</button>
    <button class="share-btn copy">复制链接</button>
</div>

<!-- QR Code Modal -->
<div class="modal-overlay">
    <div class="modal-content">
        <h3>微信扫码分享</h3>
        <img src="" alt="QR Code" class="qrcode-img">
        <button class="btn btn-sm modal-close">关闭</button>
    </div>
</div>

<div class="copy-toast">链接已复制</div>
```

并在 `templates/post.html` 的 `<head>` 中添加：

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/share.css') }}">
```

在 `</body>` 之前添加：

```html
<script src="{{ url_for('static', filename='js/share.js') }}"></script>
```

**Step 7: 测试并提交**

测试：
1. 访问文章页面，查看分享按钮
2. 点击"分享到微博"，验证跳转
3. 点击"分享到微信"，验证QR码显示
4. 点击"复制链接"，验证复制成功

```bash
git add requirements.txt backend/app.py templates/post.html static/css/share.css static/js/share.js
git commit -m "feat: add article sharing functionality

- Add Weibo sharing button
- Add WeChat QR code sharing
- Add copy link button with toast notification
- Implement QR code generation API
"
```

---

## Task 3: 暗黑模式

**Files:**
- Modify: `static/css/style.css:8-22`
- Modify: `templates/base.html:52`
- Create: `static/js/theme.js`

**Step 1: 添加暗黑主题CSS变量**

在 `static/css/style.css` 的 `:root` 之后添加：

```css
/* Dark Theme */
.dark-theme {
    --bg-color: #1a1a1a;
    --text-color: #e0e0e0;
    --border-color: #404040;
    --primary-color: #3b82f6;
    --primary-hover: #2563eb;
    --success-color: #10b981;
    --error-color: #ef4444;
    --warning-color: #f59e0b;
    --code-bg: #2d2d2d;
    --header-bg: #242424;
    --header-shadow: rgba(0, 0, 0, 0.3);
    --card-shadow: rgba(0, 0, 0, 0.2);
    --card-shadow-hover: rgba(0, 0, 0, 0.3);
}

/* Theme Toggle Button */
.theme-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: none;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    cursor: pointer;
    color: var(--text-color);
    transition: all 0.2s;
}

.theme-toggle:hover {
    background-color: var(--code-bg);
}

.theme-toggle-icon {
    font-size: 1.2rem;
}

/* Smooth theme transition */
body {
    transition: background-color 0.3s, color 0.3s;
}
```

**Step 2: 添加主题切换按钮**

在 `templates/base.html` 的导航栏中添加切换按钮（在 `.nav-links` 内）：

```html
<li>
    <button class="theme-toggle" id="themeToggle" aria-label="切换主题">
        <span class="theme-toggle-icon">🌙</span>
        <span class="theme-toggle-text">暗色</span>
    </button>
</li>
```

**Step 3: 创建主题切换脚本**

Create: `static/js/theme.js`

```javascript
// Theme switching
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = themeToggle.querySelector('.theme-toggle-icon');
    const themeText = themeToggle.querySelector('.theme-toggle-text');

    // Get saved theme or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';

    function applyTheme(theme) {
        if (theme === 'dark') {
            document.body.classList.add('dark-theme');
            themeIcon.textContent = '☀️';
            themeText.textContent = '亮色';
        } else {
            document.body.classList.remove('dark-theme');
            themeIcon.textContent = '🌙';
            themeText.textContent = '暗色';
        }
    }

    // Apply saved theme on load
    applyTheme(savedTheme);

    // Toggle theme on button click
    themeToggle.addEventListener('click', function() {
        const isDark = document.body.classList.contains('dark-theme');
        const newTheme = isDark ? 'light' : 'dark';

        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    });
});
```

**Step 4: 在base.html中引入脚本**

在 `templates/base.html` 的 `</body>` 之前添加：

```html
<script src="{{ url_for('static', filename='js/theme.js') }}"></script>
```

**Step 5: 测试主题切换**

测试：
1. 点击主题切换按钮，验证主题切换
2. 刷新页面，验证主题保持
3. 检查所有页面样式正确

**Step 6: 提交**

```bash
git add static/css/style.css templates/base.html static/js/theme.js
git commit -m "feat: add dark mode theme switching

- Add dark theme CSS variables
- Add theme toggle button in navigation
- Persist theme choice in localStorage
- Smooth transitions between themes
"
```

---

## Task 4: 加载动画

**Files:**
- Modify: `requirements.txt`
- Modify: `static/css/style.css`
- Create: `static/js/loading.js`

**Step 1: 添加lodash依赖**

在 `requirements.txt` 末尾添加：

```
lodash==4.17.21
```

**Step 2: 安装依赖**

Run: `pip install lodash` (注意：lodash是JavaScript库，我们通过CDN引入)

修改：在 `templates/base.html` 中添加CDN链接（如果需要使用lodash的debounce功能）

实际上，我们只需要在前端使用lodash，可以直接在HTML中引入CDN。

**Step 3: 添加骨架屏样式**

在 `static/css/style.css` 末尾添加：

```css
/* Skeleton Loading */
.skeleton {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 4px;
}

.dark-theme .skeleton {
    background: linear-gradient(90deg, #2d2d2d 25%, #3d3d3d 50%, #2d2d2d 75%);
}

@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.skeleton-card {
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 2rem;
}

.skeleton-title {
    height: 2rem;
    width: 70%;
    margin-bottom: 1rem;
}

.skeleton-meta {
    height: 1rem;
    width: 40%;
    margin-bottom: 1rem;
}

.skeleton-excerpt {
    height: 1rem;
    width: 100%;
    margin-bottom: 0.5rem;
}

.skeleton-excerpt:last-child {
    width: 80%;
}

/* Page Loading Spinner */
.page-loader {
    display: none;
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 1000;
}

.page-loader.active {
    display: block;
}

.spinner {
    width: 50px;
    height: 50px;
    border: 4px solid var(--border-color);
    border-top-color: var(--primary-color);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Lazy load images */
img[data-src] {
    opacity: 0;
    transition: opacity 0.3s;
}

img.loaded {
    opacity: 1;
}
```

**Step 4: 创建加载脚本**

Create: `static/js/loading.js`

```javascript
// Image lazy loading with Intersection Observer
document.addEventListener('DOMContentLoaded', function() {
    // Lazy load images
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const src = img.getAttribute('data-src');

                if (src) {
                    img.src = src;
                    img.onload = () => img.classList.add('loaded');
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    }, {
        rootMargin: '50px 0px'
    });

    // Observe all images with data-src
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });

    // Show skeleton cards while loading
    const showSkeleton = (container, count = 3) => {
        for (let i = 0; i < count; i++) {
            const skeleton = document.createElement('div');
            skeleton.className = 'skeleton-card';
            skeleton.innerHTML = `
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-meta"></div>
                <div class="skeleton skeleton-excerpt"></div>
                <div class="skeleton skeleton-excerpt"></div>
            `;
            container.appendChild(skeleton);
        }
    };

    // Export functions for use in other scripts
    window.loadingUtils = {
        showSkeleton,
        imageObserver
    };
});
```

**Step 5: 在文章卡片中使用懒加载**

修改 `templates/index.html`，将文章图片改为：

```html
{% if post.image %}
<img src="" data-src="{{ post.image }}" alt="{{ post.title }}" loading="lazy">
{% endif %}
```

**Step 6: 在base.html中引入脚本**

在 `templates/base.html` 的 `</body>` 之前添加：

```html
<script src="{{ url_for('static', filename='js/loading.js') }}"></script>
```

**Step 7: 测试并提交**

测试：
1. 滚动页面，验证图片懒加载
2. 检查骨架屏动画
3. 验证性能提升

```bash
git add static/css/style.css static/js/loading.js templates/index.html
git commit -m "feat: add loading animations and lazy image loading

- Add skeleton loading screens
- Implement Intersection Observer for lazy image loading
- Add loading spinner for page transitions
- Improve perceived performance
"
```

---

## Task 5: 标签系统

**Files:**
- Modify: `backend/models.py:28,54`
- Modify: `backend/app.py:11-16`
- Create: `templates/admin/tags.html`
- Create: `templates/tag_posts.html`
- Modify: `templates/admin/editor.html:50`
- Modify: `templates/post.html:77`

**Step 1: 创建标签相关表和函数**

在 `backend/models.py` 的 `init_db()` 函数中添加：

```python
# 在 users 表创建之后添加

# Create tags table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Create post_tags association table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS post_tags (
        post_id INTEGER,
        tag_id INTEGER,
        PRIMARY KEY (post_id, tag_id),
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )
''')
```

在 `backend/models.py` 末尾添加标签CRUD函数：

```python
def create_tag(name):
    """Create a new tag"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO tags (name) VALUES (?)',
            (name,)
        )
        conn.commit()
        tag_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        tag_id = None
    conn.close()
    return tag_id

def get_all_tags():
    """Get all tags"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags ORDER BY name')
    tags = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tags

def get_tag_by_id(tag_id):
    """Get a tag by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags WHERE id = ?', (tag_id,))
    tag = cursor.fetchone()
    conn.close()
    return dict(tag) if tag else None

def get_tag_by_name(name):
    """Get a tag by name"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags WHERE name = ?', (name,))
    tag = cursor.fetchone()
    conn.close()
    return dict(tag) if tag else None

def update_tag(tag_id, name):
    """Update a tag"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE tags SET name = ? WHERE id = ?',
            (name, tag_id)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def delete_tag(tag_id):
    """Delete a tag"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
    conn.commit()
    conn.close()

def set_post_tags(post_id, tag_names):
    """Set tags for a post (replace existing)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete existing tag associations
    cursor.execute('DELETE FROM post_tags WHERE post_id = ?', (post_id,))

    # Add new tag associations
    for tag_name in tag_names:
        if not tag_name.strip():
            continue

        # Get or create tag
        tag = get_tag_by_name(tag_name.strip())
        if not tag:
            tag_id = create_tag(tag_name.strip())
        else:
            tag_id = tag['id']

        if tag_id:
            cursor.execute(
                'INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)',
                (post_id, tag_id)
            )

    conn.commit()
    conn.close()

def get_post_tags(post_id):
    """Get all tags for a post"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT tags.* FROM tags
        JOIN post_tags ON tags.id = post_tags.tag_id
        WHERE post_tags.post_id = ?
        ORDER BY tags.name
    ''', (post_id,))
    tags = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tags

def get_posts_by_tag(tag_id, include_drafts=False, page=1, per_page=20):
    """Get all posts with a specific tag"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build WHERE clause
    where_conditions = ['post_tags.tag_id = ?']
    params = [tag_id]

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    where_clause = ' AND '.join(where_conditions)

    # Count total posts
    count_query = f'''
        SELECT COUNT(*) as count
        FROM posts
        JOIN post_tags ON posts.id = post_tags.post_id
        WHERE {where_clause}
    '''
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # Calculate offset
    offset = (page - 1) * per_page

    # Get posts for current page
    query = f'''
        SELECT posts.*, categories.name as category_name, categories.id as category_id
        FROM posts
        JOIN post_tags ON posts.id = post_tags.post_id
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE {where_clause}
        ORDER BY posts.created_at DESC
        LIMIT ? OFFSET ?
    '''
    cursor.execute(query, params + [per_page, offset])

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        'posts': posts,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 1
    }
```

**Step 2: 更新app.py导入**

在 `backend/app.py` 的导入部分添加：

```python
from models import (
    # ... existing imports ...
    create_tag, get_all_tags, get_tag_by_id, update_tag, delete_tag,
    get_tag_by_name, set_post_tags, get_post_tags, get_posts_by_tag
)
```

**Step 3: 添加标签管理路由**

在 `backend/app.py` 的分类管理路由之后添加：

```python
# Tag Management Routes
@app.route('/admin/tags')
@login_required
def tag_list():
    """List all tags"""
    tags = get_all_tags()
    return render_template('admin/tags.html', tags=tags)

@app.route('/admin/tags/new', methods=['POST'])
@login_required
def new_tag():
    """Create a new tag"""
    name = request.form.get('name')
    if not name:
        flash('标签名称不能为空', 'error')
        return redirect(url_for('tag_list'))

    tag_id = create_tag(name)
    if tag_id:
        flash('标签创建成功', 'success')
    else:
        flash('标签名称已存在', 'error')
    return redirect(url_for('tag_list'))

@app.route('/admin/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag_route(tag_id):
    """Delete a tag"""
    delete_tag(tag_id)
    flash('标签已删除', 'success')
    return redirect(url_for('tag_list'))

@app.route('/tag/<int:tag_id>')
def view_tag(tag_id):
    """View all posts with a tag"""
    tag = get_tag_by_id(tag_id)
    if not tag:
        flash('标签不存在', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Validate per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_posts_by_tag(tag_id, include_drafts=False, page=page, per_page=per_page)

    # Calculate pagination info
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # Calculate page range to display
    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    # Get all tags for the filter bar
    tags = get_all_tags()

    return render_template('tag_posts.html',
                         tag=tag,
                         posts=posts_data['posts'],
                         tags=tags,
                         pagination=posts_data,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis)
```

**Step 4: 修改文章创建和编辑路由**

在 `new_post` 和 `edit_post` 函数中，保存文章后添加标签处理：

```python
# 在 create_post 之后添加
tag_names = request.form.get('tags', '').split(',')
if tag_names:
    set_post_tags(post_id, tag_names)
```

修改 `get_post_by_id` 调用，添加标签：

```python
# 在获取 post 之后添加
post['tags'] = get_post_tags(post_id)
```

**Step 5: 创建标签管理页面**

Create: `templates/admin/tags.html`

```html
{% extends "base.html" %}

{% block title %}标签管理 - 管理后台{% endblock %}

{% block content %}
<div class="admin-categories">
    <div class="dashboard-header">
        <h2>标签管理</h2>
    </div>

    <div class="category-form">
        <h3>创建新标签</h3>
        <form action="{{ url_for('new_tag') }}" method="post">
            <div class="form-group">
                <label for="name">标签名称</label>
                <input type="text" name="name" id="name" required>
            </div>
            <button type="submit" class="btn btn-primary">创建</button>
        </form>
    </div>

    {% if tags %}
    <table class="categories-table">
        <thead>
            <tr>
                <th>ID</th>
                <th>名称</th>
                <th>文章数量</th>
                <th>创建时间</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            {% for tag in tags %}
            <tr>
                <td>{{ tag.id }}</td>
                <td>{{ tag.name }}</td>
                <td>
                    {# TODO: Add post count query #}
                    -
                </td>
                <td>{{ tag.created_at }}</td>
                <td>
                    <form action="{{ url_for('delete_tag_route', tag_id=tag.id) }}" method="post" class="delete-form">
                        <button type="submit" class="btn btn-sm btn-danger" onclick="return confirm('确定删除此标签吗？')">删除</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty-state">
        <p>暂无标签</p>
    </div>
    {% endif %}
</div>
{% endblock %}
```

**Step 6: 创建标签文章列表页面**

Create: `templates/tag_posts.html`

```html
{% extends "base.html" %}

{% block title %}{{ tag.name }} - {{ config['BLOG_NAME'] }}{% endblock %}

{% block content %}
<main class="container">
    <div class="tag-filter">
        <strong>标签：</strong>
        {% for t in tags %}
        <a href="{{ url_for('view_tag', tag_id=t.id) }}" class="tag-link {% if t.id == tag.id %}active{% endif %}">
            #{{ t.name }}
        </a>
        {% endfor %}
    </div>

    {% if posts %}
    <div class="posts-list">
        {% for post in posts %}
        <a href="{{ url_for('view_post', post_id=post.id) }}" class="post-card-link">
            <article class="post-card">
                <h2>{{ post.title }}</h2>
                <div class="post-meta">
                    <span>{{ post.created_at.strftime('%Y-%m-%d') }}</span>
                    {% if post.category_name %}
                    <span>· {{ post.category_name }}</span>
                    {% endif %}
                </div>
                <p class="post-excerpt">{{ post.content[:200] }}...</p>
            </article>
        </a>
        {% endfor %}
    </div>

    {# Pagination #}
    {% if pagination.total_pages > 1 %}
    <div class="pagination">
        {% if pagination.page > 1 %}
        <a href="{{ url_for('view_tag', tag_id=tag.id, page=pagination.page-1, per_page=pagination.per_page) }}" class="btn">上一页</a>
        {% endif %}

        <span class="pagination-info">
            {{ start_item }}-{{ end_item }} / 共 {{ pagination.total }} 篇
        </span>

        {% if pagination.page < pagination.total_pages %}
        <a href="{{ url_for('view_tag', tag_id=tag.id, page=pagination.page+1, per_page=pagination.per_page) }}" class="btn">下一页</a>
        {% endif %}
    </div>
    {% endif %}
    {% else %}
    <div class="empty-state">
        <p>该标签下暂无文章</p>
        <a href="{{ url_for('index') }}">返回首页</a>
    </div>
    {% endif %}
</main>
{% endblock %}
```

**Step 7: 修改编辑器添加标签输入**

在 `templates/admin/editor.html` 的分类选择之后添加：

```html
<div class="form-group">
    <label for="tags">标签（用逗号分隔）</label>
    <input type="text" name="tags" id="tags" value="{% if post and post.tags %}{{ post.tags|map(attribute='name')|join(', ') }}{% endif %}" placeholder="例如: Python, Flask, Web">
    <small style="color: #666;">多个标签用逗号分隔</small>
</div>
```

**Step 8: 在文章页面显示标签**

在 `templates/post.html` 的文章元信息中添加：

```html
{% if post.tags %}
<div class="post-tags">
    {% for tag in post.tags %}
    <a href="{{ url_for('view_tag', tag_id=tag.id) }}" class="post-tag">#{{ tag.name }}</a>
    {% endfor %}
</div>
{% endif %}
```

在 `static/css/style.css` 中添加：

```css
.post-tags {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 1rem 0;
}

.post-tag {
    color: var(--primary-color);
    text-decoration: none;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.875rem;
    background-color: #dbeafe;
}

.dark-theme .post-tag {
    background-color: #1e3a5f;
}

.tag-filter {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
    padding: 1rem 0;
    border-bottom: 1px solid var(--border-color);
    align-items: center;
}

.tag-link {
    color: var(--text-color);
    text-decoration: none;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.9rem;
    background-color: var(--code-bg);
    transition: all 0.3s;
}

.tag-link:hover,
.tag-link.active {
    background-color: var(--primary-color);
    color: white;
}
```

**Step 9: 测试并提交**

测试：
1. 创建标签
2. 为文章添加标签
3. 查看标签文章列表
4. 删除标签

```bash
git add backend/models.py backend/app.py templates/admin/tags.html templates/tag_posts.html templates/admin/editor.html templates/post.html static/css/style.css
git commit -m "feat: add tag system

- Add tags and post_tags tables with many-to-many relationship
- Add tag management interface
- Add tag filtering on posts
- Display tags on post pages
- Support multiple tags per post
"
```

---

## Task 6: 加载更多按钮

**Files:**
- Modify: `backend/app.py:163`
- Modify: `templates/index.html:29`
- Create: `static/js/pagination.js`

**Step 1: 添加文章列表API端点**

在 `backend/app.py` 的 `index` 函数之后添加：

```python
@app.route('/api/posts')
def api_get_posts():
    """API endpoint for paginated posts"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id')

    # Validate per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    posts_data = get_all_posts(include_drafts=False, page=page, per_page=per_page, category_id=category_id)

    # Render posts as HTML
    posts_html = ''
    for post in posts_data['posts']:
        posts_html += f'''
        <a href="/post/{post['id']}" class="post-card-link">
            <article class="post-card">
                <h2>{post['title']}</h2>
                <div class="post-meta">
                    <span>{post['created_at']}</span>
                    {% if post['category_name'] %}
                    <span>· {post['category_name']}</span>
                    {% endif %}
                </div>
                <p class="post-excerpt">{post['content'][:200]}...</p>
            </article>
        </a>
        '''

    return jsonify({
        'posts_html': posts_html,
        'has_more': posts_data['page'] < posts_data['total_pages']
    })
```

**Step 2: 修改首页模板**

在 `templates/index.html` 的文章列表之后添加"加载更多"按钮：

```html
<div id="posts-container" class="posts-list">
    {% for post in posts %}
    <a href="{{ url_for('view_post', post_id=post.id) }}" class="post-card-link">
        <article class="post-card">
            <h2>{{ post.title }}</h2>
            <div class="post-meta">
                <span>{{ post.created_at.strftime('%Y-%m-%d') }}</span>
                {% if post.category_name %}
                <span>· {{ post.category_name }}</span>
                {% endif %}
            </div>
            <p class="post-excerpt">{{ post.content[:200] }}...</p>
        </article>
    </a>
    {% endfor %}
</div>

{% if pagination.page < pagination.total_pages %}
<div class="load-more-container">
    <button id="load-more" class="btn btn-primary" data-page="{{ pagination.page + 1 }}" data-category="{{ current_category_id or '' }}">
        加载更多
    </button>
</div>
{% endif %}
```

**Step 3: 创建分页脚本**

Create: `static/js/pagination.js`

```javascript
// Load more functionality
document.addEventListener('DOMContentLoaded', function() {
    const loadMoreBtn = document.getElementById('load-more');
    const postsContainer = document.getElementById('posts-container');

    if (!loadMoreBtn || !postsContainer) return;

    loadMoreBtn.addEventListener('click', async function() {
        const page = this.dataset.page;
        const categoryId = this.dataset.category;

        // Disable button and show loading
        this.disabled = true;
        this.textContent = '加载中...';

        try {
            // Build URL with parameters
            let url = `/api/posts?page=${page}`;
            if (categoryId) {
                url += `&category_id=${categoryId}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (data.posts_html) {
                // Append new posts
                postsContainer.insertAdjacentHTML('beforeend', data.posts_html);

                // Update button state
                if (data.has_more) {
                    this.dataset.page = parseInt(page) + 1;
                    this.disabled = false;
                    this.textContent = '加载更多';
                } else {
                    this.remove();
                }

                // Re-initialize lazy loading for new images
                if (window.loadingUtils && window.loadingUtils.imageObserver) {
                    document.querySelectorAll('img[data-src]').forEach(img => {
                        window.loadingUtils.imageObserver.observe(img);
                    });
                }
            }
        } catch (error) {
            console.error('Failed to load more posts:', error);
            this.disabled = false;
            this.textContent = '加载失败，重试';
        }
    });
});
```

**Step 4: 在base.html中引入脚本**

在 `templates/base.html` 的 `</body>` 之前添加：

```html
<script src="{{ url_for('static', filename='js/pagination.js') }}"></script>
```

**Step 5: 添加样式**

在 `static/css/style.css` 中添加：

```css
.load-more-container {
    text-align: center;
    margin: 2rem 0;
    padding: 2rem 0;
}

#load-more {
    padding: 0.75rem 2rem;
    font-size: 1rem;
}

#load-more:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
```

**Step 6: 测试并提交**

测试：
1. 访问首页
2. 点击"加载更多"按钮
3. 验证新文章加载
4. 验证按钮状态变化

```bash
git add backend/app.py templates/index.html static/js/pagination.js static/css/style.css
git commit -m "feat: add load more button for pagination

- Add JSON API endpoint for paginated posts
- Add AJAX load more functionality
- Replace pagination with load more button
- Improve user experience with seamless loading
"
```

---

## Task 7: 文章搜索

**Files:**
- Modify: `backend/models.py:54`
- Modify: `backend/app.py:11`
- Create: `templates/search.html`
- Modify: `templates/base.html:47`
- Modify: `static/css/style.css`

**Step 1: 添加FTS5全文搜索表**

在 `backend/models.py` 的 `init_db()` 函数中添加：

```python
# 在所有表创建之后添加

# Create FTS5 virtual table for full-text search
cursor.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
        title,
        content,
        content='posts',
        content_rowid='rowid'
    )
''')

# Create triggers to keep FTS index in sync
cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
        INSERT INTO posts_fts(rowid, title, content)
        VALUES (new.id, new.title, new.content);
    END
''')

cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
        INSERT INTO posts_fts(posts_fts, rowid, title, content)
        VALUES ('delete', old.id, old.title, old.content);
    END
''')

cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
        INSERT INTO posts_fts(posts_fts, rowid, title, content)
        VALUES ('delete', old.id, old.title, old.content);
        INSERT INTO posts_fts(rowid, title, content)
        VALUES (new.id, new.title, new.content);
    END
''')
```

在 `backend/models.py` 末尾添加搜索函数：

```python
def search_posts(query, include_drafts=False, page=1, per_page=20):
    """Search posts using FTS5"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build WHERE clause
    where_conditions = ['posts_fts MATCH ?']
    params = [query]

    if not include_drafts:
        where_conditions.append('posts.is_published = 1')

    where_clause = ' AND '.join(where_conditions)

    # Count total results
    count_query = f'''
        SELECT COUNT(*) as count
        FROM posts_fts
        JOIN posts ON posts_fts.rowid = posts.id
        WHERE {where_clause}
    '''
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['count']

    # Calculate offset
    offset = (page - 1) * per_page

    # Get results for current page
    search_query = f'''
        SELECT posts.*, categories.name as category_name, categories.id as category_id
        FROM posts_fts
        JOIN posts ON posts_fts.rowid = posts.id
        LEFT JOIN categories ON posts.category_id = categories.id
        WHERE {where_clause}
        ORDER BY posts.created_at DESC
        LIMIT ? OFFSET ?
    '''
    cursor.execute(search_query, params + [per_page, offset])

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        'posts': posts,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page if total_count > 0 else 1
    }
```

**Step 2: 更新app.py导入**

在 `backend/app.py` 的导入部分添加：

```python
from models import search_posts
```

**Step 3: 添加搜索路由**

在 `backend/app.py` 中添加：

```python
@app.route('/search')
def search():
    """Search posts"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Validate per_page
    if per_page not in [10, 20, 40, 80]:
        per_page = 20

    if not query:
        return render_template('search.html', query='', posts=None, pagination=None)

    posts_data = search_posts(query, include_drafts=False, page=page, per_page=per_page)

    # Calculate pagination info
    start_item = (posts_data['page'] - 1) * posts_data['per_page'] + 1
    end_item = min(posts_data['page'] * posts_data['per_page'], posts_data['total'])

    # Calculate page range to display
    page_start = max(1, posts_data['page'] - 2)
    page_end = min(posts_data['total_pages'] + 1, posts_data['page'] + 3)
    page_range = list(range(page_start, page_end))
    show_ellipsis = posts_data['total_pages'] > posts_data['page'] + 2

    return render_template('search.html',
                         query=query,
                         posts=posts_data['posts'],
                         pagination=posts_data,
                         start_item=start_item,
                         end_item=end_item,
                         page_range=page_range,
                         show_ellipsis=show_ellipsis)
```

**Step 4: 创建搜索页面**

Create: `templates/search.html`

```html
{% extends "base.html" %}

{% block title %}搜索：{{ query }} - {{ config['BLOG_NAME'] }}{% endblock %}

{% block content %}
<main class="container">
    <div class="search-header">
        <h2>搜索结果</h2>
        {% if query %}
        <p class="search-query">关键词：<strong>{{ query }}</strong></p>
        {% endif %}
    </div>

    {% if posts is none %}
    <div class="search-form">
        <form action="{{ url_for('search') }}" method="get">
            <input type="text" name="q" placeholder="输入搜索关键词..." class="search-input">
            <button type="submit" class="btn btn-primary">搜索</button>
        </form>
    </div>
    {% elif posts %}
    <div class="search-info">
        找到 {{ pagination.total }} 个结果
    </div>

    <div class="posts-list">
        {% for post in posts %}
        <a href="{{ url_for('view_post', post_id=post.id) }}" class="post-card-link">
            <article class="post-card">
                <h2>{{ post.title }}</h2>
                <div class="post-meta">
                    <span>{{ post.created_at.strftime('%Y-%m-%d') }}</span>
                    {% if post.category_name %}
                    <span>· {{ post.category_name }}</span>
                    {% endif %}
                </div>
                <p class="post-excerpt">{{ post.content[:200] }}...</p>
            </article>
        </a>
        {% endfor %}
    </div>

    {# Pagination #}
    {% if pagination.total_pages > 1 %}
    <div class="pagination">
        {% if pagination.page > 1 %}
        <a href="{{ url_for('search', q=query, page=pagination.page-1, per_page=pagination.per_page) }}" class="btn">上一页</a>
        {% endif %}

        <span class="pagination-info">
            {{ start_item }}-{{ end_item }} / 共 {{ pagination.total }} 篇
        </span>

        {% if pagination.page < pagination.total_pages %}
        <a href="{{ url_for('search', q=query, page=pagination.page+1, per_page=pagination.per_page) }}" class="btn">下一页</a>
        {% endif %}
    </div>
    {% endif %}
    {% else %}
    <div class="empty-state">
        <p>未找到相关文章</p>
        <a href="{{ url_for('index') }}">返回首页</a>
    </div>
    {% endif %}
</main>
{% endblock %}
```

**Step 5: 在导航栏添加搜索框**

在 `templates/base.html` 的导航栏中添加：

```html
<form action="{{ url_for('search') }}" method="get" class="search-form-nav">
    <input type="text" name="q" placeholder="搜索文章..." class="search-input-nav" value="{{ request.args.get('q', '') }}">
    <button type="submit" class="search-btn">🔍</button>
</form>
```

**Step 6: 添加搜索样式**

在 `static/css/style.css` 中添加：

```css
/* Search */
.search-header {
    margin-bottom: 2rem;
}

.search-query {
    color: #666;
    font-size: 1.1rem;
}

.search-form {
    max-width: 600px;
    margin: 2rem auto;
    text-align: center;
}

.search-input {
    width: 100%;
    padding: 1rem;
    border: 2px solid var(--border-color);
    border-radius: 8px;
    font-size: 1rem;
    margin-bottom: 1rem;
}

.search-input:focus {
    outline: none;
    border-color: var(--primary-color);
}

.search-form-nav {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.search-input-nav {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 0.9rem;
    width: 200px;
    transition: width 0.3s;
}

.search-input-nav:focus {
    outline: none;
    border-color: var(--primary-color);
    width: 300px;
}

.search-btn {
    background: none;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    padding: 0.5rem;
}

.search-info {
    margin-bottom: 1.5rem;
    color: #666;
    font-size: 0.95rem;
}

@media (max-width: 768px) {
    .search-form-nav {
        display: none;
    }
}
```

**Step 7: 测试并提交**

测试：
1. 在导航栏搜索框输入关键词
2. 验证搜索结果
3. 测试分页
4. 测试空结果

```bash
git add backend/models.py backend/app.py templates/search.html templates/base.html static/css/style.css
git commit -m "feat: add full-text search functionality

- Implement SQLite FTS5 full-text search
- Add search page with results display
- Add search box in navigation
- Support Chinese text search
- Auto-sync FTS index with triggers
"
```

---

## Task 8: 评论系统

**Files:**
- Modify: `backend/models.py:54`
- Modify: `backend/app.py:11`
- Create: `templates/admin/comments.html`
- Modify: `templates/post.html:89`

**Step 1: 创建评论表和函数**

在 `backend/models.py` 的 `init_db()` 函数中添加：

```python
# 在 users 表创建之后添加

# Create comments table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        author_email TEXT,
        content TEXT NOT NULL,
        is_visible BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
    )
''')
```

在 `backend/models.py` 末尾添加评论CRUD函数：

```python
def create_comment(post_id, author_name, author_email, content):
    """Create a new comment"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO comments (post_id, author_name, author_email, content) VALUES (?, ?, ?, ?)',
        (post_id, author_name, author_email, content)
    )
    conn.commit()
    comment_id = cursor.lastrowid
    conn.close()
    return comment_id

def get_comments_by_post(post_id, include_hidden=False):
    """Get all comments for a post"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if include_hidden:
        cursor.execute('''
            SELECT * FROM comments
            WHERE post_id = ?
            ORDER BY created_at DESC
        ''', (post_id,))
    else:
        cursor.execute('''
            SELECT * FROM comments
            WHERE post_id = ? AND is_visible = 1
            ORDER BY created_at DESC
        ''', (post_id,))

    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comments

def get_all_comments(include_hidden=False):
    """Get all comments"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if include_hidden:
        cursor.execute('''
            SELECT comments.*, posts.title as post_title, posts.id as post_id
            FROM comments
            JOIN posts ON comments.post_id = posts.id
            ORDER BY comments.created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT comments.*, posts.title as post_title, posts.id as post_id
            FROM comments
            JOIN posts ON comments.post_id = posts.id
            WHERE comments.is_visible = 1
            ORDER BY comments.created_at DESC
        ''')

    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comments

def update_comment_visibility(comment_id, is_visible):
    """Update comment visibility"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE comments SET is_visible = ? WHERE id = ?',
        (is_visible, comment_id)
    )
    conn.commit()
    conn.close()

def delete_comment(comment_id):
    """Delete a comment"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    conn.commit()
    conn.close()
```

**Step 2: 更新app.py导入**

在 `backend/app.py` 的导入部分添加：

```python
from models import (
    # ... existing imports ...
    create_comment, get_comments_by_post, get_all_comments,
    update_comment_visibility, delete_comment
)
```

**Step 3: 添加评论路由**

在 `backend/app.py` 中添加：

```python
# Comment Routes
@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    """Add a comment to a post"""
    post = get_post_by_id(post_id)
    if post is None:
        flash('文章不存在', 'error')
        return redirect(url_for('index'))

    author_name = request.form.get('author_name', '').strip()
    author_email = request.form.get('author_email', '').strip()
    content = request.form.get('content', '').strip()

    if not author_name or not content:
        flash('姓名和评论内容不能为空', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    if len(author_name) > 50:
        flash('姓名过长', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    if len(content) > 1000:
        flash('评论内容过长', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    create_comment(post_id, author_name, author_email, content)
    flash('评论提交成功', 'success')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/admin/comments')
@login_required
def comment_list():
    """List all comments"""
    comments = get_all_comments(include_hidden=True)
    return render_template('admin/comments.html', comments=comments)

@app.route('/admin/comments/<int:comment_id>/toggle', methods=['POST'])
@login_required
def toggle_comment(comment_id):
    """Toggle comment visibility"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT is_visible FROM comments WHERE id = ?', (comment_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        new_visibility = not result['is_visible']
        update_comment_visibility(comment_id, new_visibility)
        flash('评论状态已更新', 'success')
    else:
        flash('评论不存在', 'error')

    return redirect(url_for('comment_list'))

@app.route('/admin/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment_route(comment_id):
    """Delete a comment"""
    delete_comment(comment_id)
    flash('评论已删除', 'success')
    return redirect(url_for('comment_list'))
```

**Step 4: 在文章页面添加评论**

在 `templates/post.html` 的文章内容之后、导航之前添加：

```html
<!-- Comments Section -->
<section class="comments-section">
    <h3>评论 ({{ comments|length }})</h3>

    {% if comments %}
    <div class="comments-list">
        {% for comment in comments %}
        <div class="comment">
            <div class="comment-header">
                <strong>{{ comment.author_name }}</strong>
                <span class="comment-date">{{ comment.created_at.strftime('%Y-%m-%d %H:%M') }}</span>
            </div>
            <div class="comment-content">
                {{ comment.content }}
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <p class="no-comments">暂无评论，快来抢沙发吧！</p>
    {% endif %}

    <!-- Comment Form -->
    <form class="comment-form" action="{{ url_for('add_comment', post_id=post.id) }}" method="post">
        <h4>发表评论</h4>
        <div class="form-group">
            <label for="author_name">姓名 *</label>
            <input type="text" name="author_name" id="author_name" required maxlength="50">
        </div>
        <div class="form-group">
            <label for="author_email">邮箱（可选，不会公开）</label>
            <input type="email" name="author_email" id="author_email" maxlength="100">
        </div>
        <div class="form-group">
            <label for="content">评论内容 *</label>
            <textarea name="content" id="content" rows="5" required maxlength="1000"></textarea>
        </div>
        <button type="submit" class="btn btn-primary">提交评论</button>
    </form>
</section>
```

**Step 5: 修改view_post路由获取评论**

在 `backend/app.py` 的 `view_post` 函数中添加：

```python
# 在 markdown 渲染之后添加
comments = get_comments_by_post(post_id)
return render_template('post.html', post=post, comments=comments)
```

**Step 6: 创建评论管理页面**

Create: `templates/admin/comments.html`

```html
{% extends "base.html" %}

{% block title %}评论管理 - 管理后台{% endblock %}

{% block content %}
<div class="admin-categories">
    <div class="dashboard-header">
        <h2>评论管理</h2>
    </div>

    {% if comments %}
    <table class="categories-table">
        <thead>
            <tr>
                <th>作者</th>
                <th>内容</th>
                <th>文章</th>
                <th>时间</th>
                <th>状态</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            {% for comment in comments %}
            <tr>
                <td>{{ comment.author_name }}</td>
                <td>{{ comment.content[:100] }}{% if comment.content|length > 100 %}...{% endif %}</td>
                <td>
                    <a href="{{ url_for('view_post', post_id=comment.post_id) }}" target="_blank">
                        {{ comment.post_title }}
                    </a>
                </td>
                <td>{{ comment.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                <td>
                    {% if comment.is_visible %}
                    <span class="status published">可见</span>
                    {% else %}
                    <span class="status draft">隐藏</span>
                    {% endif %}
                </td>
                <td>
                    <div class="actions">
                        <form action="{{ url_for('toggle_comment', comment_id=comment.id) }}" method="post" class="delete-form">
                            <button type="submit" class="btn btn-sm">
                                {% if comment.is_visible %}隐藏{% else %}显示{% endif %}
                            </button>
                        </form>
                        <form action="{{ url_for('delete_comment_route', comment_id=comment.id) }}" method="post" class="delete-form">
                            <button type="submit" class="btn btn-sm btn-danger" onclick="return confirm('确定删除此评论吗？')">删除</button>
                        </form>
                    </div>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty-state">
        <p>暂无评论</p>
    </div>
    {% endif %}
</div>
{% endblock %}
```

**Step 7: 在管理后台导航添加评论链接**

在管理后台模板中添加评论管理链接（具体位置根据模板结构确定）。

**Step 8: 添加评论样式**

在 `static/css/style.css` 中添加：

```css
/* Comments */
.comments-section {
    max-width: 680px;
    margin: 3rem auto 0;
    padding-top: 2rem;
    border-top: 1px solid var(--border-color);
}

.comments-section h3 {
    margin-bottom: 1.5rem;
}

.comments-list {
    margin-bottom: 2rem;
}

.comment {
    padding: 1.5rem;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    margin-bottom: 1rem;
    background-color: var(--bg-color);
}

.comment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
}

.comment-header strong {
    font-size: 1rem;
}

.comment-date {
    color: #666;
    font-size: 0.875rem;
}

.comment-content {
    line-height: 1.6;
    color: var(--text-color);
}

.no-comments {
    color: #666;
    text-align: center;
    padding: 2rem;
}

.comment-form {
    padding: 2rem;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background-color: var(--code-bg);
}

.comment-form h4 {
    margin-bottom: 1rem;
}

.comment-form textarea {
    min-height: 120px;
}
```

**Step 9: 测试并提交**

测试：
1. 在文章页面添加评论
2. 验证评论显示
3. 在管理后台管理评论
4. 测试评论显示/隐藏
5. 测试删除评论

```bash
git add backend/models.py backend/app.py templates/admin/comments.html templates/post.html static/css/style.css
git commit -m "feat: add comment system

- Add comments table with post foreign key
- Add guest commenting (no login required)
- Add comment management interface
- Support comment visibility toggle
- Add email field (optional, not public)
- Add form validation
"
```

---

## 完成所有任务后的最终步骤

**Final Step: 测试所有功能并合并分支**

```bash
# 运行完整测试
1. 测试数据库索引：验证查询性能
2. 测试文章分享：微博、微信、复制链接
3. 测试暗黑模式：切换、持久化
4. 测试加载动画：骨架屏、懒加载
5. 测试标签系统：创建、分配、搜索
6. 测试加载更多：AJAX加载、按钮状态
7. 测试文章搜索：FTS5搜索、分页
8. 测试评论系统：添加、管理、显示/隐藏

# 如果所有测试通过
git checkout main
git merge feature-blog-enhancements
git push origin main

# 或者创建 Pull Request
```

**总任务数：** 8个主要功能
**预计时间：** 每个功能1-2小时
**测试重点：** 每个功能独立测试后再合并

---

## 注意事项

1. **数据库迁移：** 添加索引和表后需要重新初始化数据库
2. **依赖管理：** 确保所有Python依赖都已安装
3. **CSS变量：** 暗黑模式需要在所有颜色处使用CSS变量
4. **性能优化：** 图片懒加载和骨架屏提升用户体验
5. **搜索优化：** FTS5需要重新索引现有数据
6. **评论安全：** 考虑添加反垃圾评论机制（可选）
7. **响应式设计：** 所有新功能需要移动端适配
8. **用户隐私：** 评论邮箱不公开显示

---

**实现顺序：** 按Task 1-8的顺序依次实现，每个功能独立测试通过后再进行下一个。
