# Simple Blog 架构文档

## 目录

- [系统概述](#系统概述)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [数据模型](#数据模型)
- [路由架构](#路由架构)
- [安全机制](#安全机制)
- [AI 服务架构](#ai-服务架构)
- [图片处理流程](#图片处理流程)
- [前端架构](#前端架构)

---

## 系统概述

Simple Blog 是一个基于 Flask 的现代化博客系统，采用模块化蓝图架构设计，支持内容管理、知识库、AI 辅助等功能。

### 核心设计原则

1. **模块化设计**: 使用 Flask Blueprint 分离不同功能模块
2. **安全优先**: CSRF 保护、速率限制、XSS 防护等多层安全机制
3. **可扩展性**: 支持多种 AI 提供商、浏览器扩展集成
4. **用户体验**: 响应式设计、暗黑模式、移动端优化

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Flask | 3.0+ | Web 框架 |
| SQLite | 3.x | 数据库（FTS5 全文搜索） |
| Python | 3.11+ | 运行环境 |
| Flask-WTF | 1.2+ | CSRF 保护 |
| Flask-Limiter | 3.5+ | 速率限制 |
| webauthn | 2.7+ | Passkey 认证 |
| Pillow | 10.0+ | 图片处理 |
| pillow-heif | 0.13+ | HEIC 格式支持 |

### AI 集成

| 提供商 | SDK | 模型 |
|--------|-----|------|
| OpenAI | openai | GPT-3.5/GPT-4 |
| 火山引擎 | 自定义 | 豆包系列 |
| 阿里百炼 | 自定义 | 通义千问系列 |

### 前端

| 技术 | 用途 |
|------|------|
| Vanilla JavaScript | 核心交互 |
| Quill.js | 富文本编辑器 |
| 原生 CSS | 样式系统 |
| Markdown2 | Markdown 渲染 |
| Bleach | HTML 清理 |

---

## 项目结构

```
simple-blog/
│
├── backend/                      # 后端代码
│   ├── app.py                   # 应用主入口
│   ├── config.py                # 配置管理
│   ├── logger.py                # 日志系统
│   │
│   ├── models/                  # 数据模型层
│   │   ├── models.py           # 数据库模型和操作
│   │   └── init_db.py          # 数据库初始化
│   │
│   ├── routes/                  # 路由模块（蓝图）
│   │   ├── __init__.py         # 蓝图注册
│   │   ├── auth.py             # 认证路由（登录/Passkey）
│   │   ├── blog.py             # 博客公开路由
│   │   ├── admin.py            # 管理后台路由
│   │   ├── api.py              # RESTful API
│   │   ├── ai.py               # AI 功能路由
│   │   ├── knowledge_base.py   # 知识库路由
│   │   └── drafts.py           # 草稿同步路由
│   │
│   ├── ai_services/            # AI 服务层
│   │   ├── __init__.py
│   │   ├── tag_generator.py    # 标签生成服务
│   │   ├── providers/          # AI 提供商适配器
│   │   │   ├── openai.py
│   │   │   ├── volcengine.py
│   │   │   └── dashscope.py
│   │
│   ├── utils/                  # 工具函数
│   │   ├── asset_version.py    # 静态资源版本管理
│   │   └── template_helpers.py # 模板辅助函数
│   │
│   └── tasks/                  # 后台任务
│       ├── image_optimization_task.py  # 图片优化任务
│
├── templates/                   # Jinja2 模板
│   ├── base.html              # 基础模板
│   ├── index.html             # 首页
│   ├── post.html              # 文章详情
│   ├── login.html             # 登录页
│   │
│   ├── admin/                 # 管理后台模板
│   │   ├── dashboard.html     # 仪表板
│   │   ├── editor.html        # 编辑器
│   │   ├── ai_settings.html   # AI 设置
│   │   └── ai_history.html    # AI 历史
│   │
│   └── incubator.html         # 孵化箱
│
├── static/                     # 静态资源
│   ├── css/                   # 样式文件
│   │   ├── style.css          # 主样式
│   │   ├── mobile-weibo.css   # 移动端样式
│   │   ├── pc-feed.css        # PC 信息流样式
│   │   └── lightbox.css       # 图片灯箱
│   │
│   ├── js/                    # JavaScript 文件
│   │   ├── main.js            # 主脚本
│   │   ├── editor.js          # 编辑器逻辑
│   │   ├── mobile-editor.js   # 移动端编辑器
│   │   ├── draft-sync.js      # 草稿同步
│   │   ├── passkeys.js        # Passkey 登录
│   │   └── shortcuts.js       # 快捷键
│   │
│   └── uploads/               # 用户上传内容
│       ├── images/            # 原始图片
│       └── optimized/         # 优化后的图片
│
├── db/                         # 数据库目录
│   └── simple_blog.db         # SQLite 数据库
│
├── logs/                       # 日志目录
│
├── browser-extension/          # 浏览器扩展
│   ├── manifest.json
│   ├── popup.html
│   └── content.js
│
├── safari-extension/           # Safari 扩展
│
├── tests/                      # 测试代码
│
└── docs/                       # 文档
```

---

## 数据模型

### 核心表结构

#### 用户表 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'author',      -- admin/editor/author
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 文章表 (posts)
```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER REFERENCES users(id),
    category_id INTEGER REFERENCES categories(id),
    is_published INTEGER DEFAULT 0,
    access_level TEXT DEFAULT 'public',  -- public/login/password/private
    password TEXT,
    allow_comments INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 全文搜索表 (posts_fts)
```sql
CREATE VIRTUAL TABLE posts_fts USING fts5(
    title,
    content,
    content_rowid=rowid
);
```

#### 分类表 (categories)
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 标签表 (tags)
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);
```

#### 文章标签关联表 (post_tags)
```sql
CREATE TABLE post_tags (
    post_id INTEGER REFERENCES posts(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (post_id, tag_id)
);
```

#### 评论表 (comments)
```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER REFERENCES posts(id),
    author_name TEXT NOT NULL,
    author_email TEXT,
    content TEXT NOT NULL,
    is_visible INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Passkey 表 (passkeys)
```sql
CREATE TABLE passkeys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    credential_id TEXT UNIQUE NOT NULL,
    public_key TEXT NOT NULL,
    sign_count INTEGER DEFAULT 0,
    device_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);
```

#### 知识库卡片表 (cards)
```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    title TEXT,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'idea',      -- idea/incubating/draft
    tags TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 草稿表 (drafts)
```sql
CREATE TABLE drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    post_id INTEGER REFERENCES posts(id),
    title TEXT,
    content TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 图片优化表 (optimized_images)
```sql
CREATE TABLE optimized_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path TEXT NOT NULL,
    thumbnail_path TEXT,
    medium_path TEXT,
    large_path TEXT,
    feed_path TEXT,
    status TEXT DEFAULT 'pending',    -- pending/processing/completed/failed
    original_size INTEGER,
    optimized_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 路由架构

### 蓝图注册

```python
# backend/app.py

# 认证蓝图
app.register_blueprint(auth_bp)

# 博客蓝图
app.register_blueprint(blog_bp)

# 管理后台蓝图
app.register_blueprint(admin_bp, url_prefix='/admin')

# API 蓝图
app.register_blueprint(api_bp, url_prefix='/api')

# AI 蓝图
app.register_blueprint(ai_bp, url_prefix='/admin/ai')

# 知识库蓝图
app.register_blueprint(knowledge_base_bp, url_prefix='/knowledge_base')

# 草稿同步蓝图
app.register_blueprint(drafts_bp)

# 移动端蓝图
app.register_blueprint(mobile_bp, url_prefix='/mobile')
```

### 路由职责划分

| 蓝图 | 前缀 | 职责 | 主要端点 |
|------|------|------|----------|
| `auth_bp` | 无 | 用户认证 | `/login`, `/logout`, `/passkeys/*` |
| `blog_bp` | 无 | 公开内容 | `/`, `/post/<id>`, `/search` |
| `admin_bp` | `/admin` | 管理后台 | `/admin`, `/admin/new`, `/admin/edit` |
| `api_bp` | `/api` | REST API | `/api/posts`, `/api/share/qrcode` |
| `ai_bp` | `/admin/ai` | AI 功能 | `/admin/ai/generate-tags` |
| `knowledge_base_bp` | `/knowledge_base` | 知识库 | `/api/plugin/submit`, `/api/cards` |
| `drafts_bp` | 无 | 草稿同步 | `/api/drafts/*` |
| `mobile_bp` | `/mobile` | 移动端 | `/mobile/upload` |

---

## 安全机制

### 1. 认证与授权

#### 密码认证
- 使用 `werkzeug.security` 进行密码哈希
- 密码强度验证：至少 10 位，包含大小写字母和数字

#### Passkey / WebAuthn
- 支持无密码登录
- 使用 `webauthn` 库实现
- 支持设备记忆（90 天有效期）

#### 角色权限
```python
def can_manage_users(f):
    """仅管理员可访问"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('权限不足', 'error')
            return redirect(url_for('blog.index'))
        return f(*args, **kwargs)
    return decorated_function
```

### 2. CSRF 保护

```python
csrf = CSRFProtect(app)

# 全局启用
app.config['WTF_CSRF_ENABLED'] = True

# 部分端点豁免（浏览器扩展需求）
csrf.exempt(app.view_functions['knowledge_base.plugin_submit'])
```

### 3. 速率限制

```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "200 per hour"]
)

# 登录端点严格限制
limiter.limit("5 per minute")(app.view_functions['auth.login'])
```

### 4. XSS 防护

```python
# Markdown 渲染后清理 HTML
post['content_html'] = bleach.clean(
    markdown2.markdown(post['content']),
    tags=['p', 'a', 'strong', 'em', 'ul', 'ol', 'li', ...],
    attributes={'a': ['href', 'title'], 'img': ['src', 'alt']},
    strip_comments=False
)
```

### 5. SQL 注入防护

所有数据库查询使用参数化查询：

```python
# 安全的查询方式
cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
```

### 6. 会话安全

```python
# 会话配置
SESSION_COOKIE_SECURE = True      # HTTPS only
SESSION_COOKIE_HTTPONLY = True    # 防止 JS 访问
SESSION_COOKIE_SAMESITE = 'Lax'   # CSRF 防护
```

---

## AI 服务架构

### 服务抽象层

```python
class TagGenerator:
    """AI 标签生成器"""

    @staticmethod
    def create_provider(provider_name, api_key, model):
        """创建 AI 提供商实例"""
        providers = {
            'openai': OpenAIProvider,
            'volcengine': VolcengineProvider,
            'dashscope': DashscopeProvider,
        }
        return providers[provider_name](api_key, model)

    @staticmethod
    def generate_for_post(title, content, user_config, max_tags=3):
        """生成文章标签"""
        provider = TagGenerator.create_provider(...)
        return provider.generate_tags(title, content, max_tags)
```

### 提供商适配器

每个 AI 提供商实现统一接口：

```python
class AIProvider(ABC):
    @abstractmethod
    def generate_tags(self, title, content, max_tags):
        pass

    @abstractmethod
    def generate_summary(self, title, content, max_length):
        pass
```

### AI 功能端点

| 功能 | 端点 | 说明 |
|------|------|------|
| 生成标签 | `/admin/ai/generate-tags` | AI 自动生成文章标签 |
| 生成摘要 | `/admin/ai/generate-summary` | 生成文章摘要 |
| 推荐文章 | `/admin/ai/recommend-posts` | 推荐相关文章 |
| 内容续写 | `/admin/ai/continue-writing` | 智能续写 |
| 内容整理 | `/admin/ai/organize-content` | 智能整理建议 |

---

## 图片处理流程

### 上传流程

```
用户上传图片
    ↓
验证文件类型和大小
    ↓
生成唯一文件名（MD5 哈希）
    ↓
保存到 static/uploads/images/
    ↓
创建优化任务记录
    ↓
异步处理（多尺寸生成）
```

### 优化任务

```python
def queue_image_optimization(original_path):
    """将图片加入优化队列"""
    # 创建待优化记录
    create_optimized_image_record(original_path)

    # 异步处理（线程池）
    # 生成尺寸：
    # - thumbnail: 150×150
    # - medium: 600×400
    # - large: 1200×800
    # - feed: 1920×1280
```

### 响应式图片加载

前端根据设备自动选择合适尺寸：

```javascript
// 服务端图片 URL 转换
function getOptimizedImageUrl(originalUrl, size) {
    // /static/uploads/images/xxx.jpg
    // → /static/uploads/optimized/xxx_medium.webp
}
```

---

## 前端架构

### 模板继承

```django
{# base.html #}
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}{% endblock %}</title>
    {% block head %}{% endblock %}
</head>
<body>
    {% block header %}{% endblock %}
    {% block content %}{% endblock %}
    {% block footer %}{% endblock %}
</body>
</html>
```

### JavaScript 模块化

```javascript
// main.js - 主入口
document.addEventListener('DOMContentLoaded', () => {
    // 初始化各模块
    Editor.init();
    DraftSync.init();
    Shortcuts.init();
    Passkeys.init();
});
```

### 状态管理

使用 LocalStorage 存储草稿和用户设置：

```javascript
// 草稿自动保存
class DraftSync {
    static save(postId, content) {
        const key = `draft_${postId}`;
        localStorage.setItem(key, JSON.stringify({
            content,
            timestamp: Date.now()
        }));
    }
}
```

---

## 扩展性设计

### 浏览器扩展集成

```
浏览器扩展
    ↓
API Key 认证
    ↓
POST /api/plugin/submit
    ↓
创建文章或卡片
```

### 移动端支持

- 响应式 CSS (`mobile-weibo.css`)
- 移动端专用编辑器 (`mobile-editor.js`)
- 触摸手势支持

---

## 性能优化

1. **静态资源缓存**
   - CSS/JS: 1 年缓存
   - 图片: 1 周缓存
   - 版本化管理

2. **数据库优化**
   - SQLite WAL 模式
   - FTS5 全文搜索
   - 连接复用

3. **图片优化**
   - WebP 格式转换
   - 多尺寸生成
   - 懒加载

4. **前端优化**
   - 代码分割
   - 防抖/节流
   - 无限滚动

---

## 监控与日志

### 日志系统

```python
# 结构化日志
logger = logging.getLogger(__name__)

# 操作日志
log_operation(user_id, username, action, details)

# 错误日志
log_error(error, context='Error context')
```

### 日志文件

| 文件 | 内容 |
|------|------|
| `logs/app.log` | 应用日志 |
| `logs/error.log` | 错误日志 |
| `logs/access.log` | 访问日志 |

---

## 部署架构

### 推荐部署方式

```
┌─────────────────┐
│     Nginx       │  ← 反向代理 + SSL
└────────┬────────┘
         │
┌────────▼────────┐
│   Systemd       │  ← 进程管理
│   Simple Blog   │
└─────────────────┘
         │
┌────────▼────────┐
│     SQLite      │  ← 数据库
└─────────────────┘
```

### 环境变量配置

核心配置项参考 [配置文档](../backend/config.py)。

---

## 维护与升级

### 数据库迁移

```bash
# 运行迁移脚本
python backend/migrations/migrate_<feature>.py
```

### 版本升级

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r backend/requirements.txt

# 运行迁移
python backend/migrations/migrate_xxx.py

# 重启服务
sudo systemctl restart simple-blog
```

---

本文档持续更新中。如有疑问，请参考 [API 文档](./api-documentation.md) 或 [部署指南](../DEPLOYMENT.md)。
