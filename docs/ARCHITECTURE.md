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
| Flask | 3.1+ | Web 框架 |
| SQLite | 3.x | 数据库（FTS5 全文搜索） |
| Python | 3.11+ | 运行环境 |
| Flask-WTF | 1.2+ | CSRF 保护 |
| Flask-Limiter | 3.x+ | 速率限制 |
| Flask-Caching | 3.x+ | 简单缓存 |
| webauthn | 2.7+ | Passkey 认证 |
| Pillow | 10.0+ | 图片处理 |
| pillow-heif | 0.13+ | HEIC 格式支持 |
| qrcode | - | 分享二维码 |
| html2text | - | Markdown 转换 |

### AI 集成

| 提供商 | SDK | 模型 |
|--------|-----|------|
| OpenAI | openai | GPT-3.5/GPT-4 |
| 火山引擎 | 自定义 | 豆包系列 |
| 阿里百炼 | 自定义 | 通义千问系列 |

### 前端

| 技术 | 用途 |
|------|------|
| Jinja2 | 服务器端模板渲染 |
| Vanilla JavaScript | 博客/后台核心交互 |
| Quill.js | 传统富文本编辑器 |
| 原生 CSS | 样式系统、响应式、暗黑模式 |
| React 19.2 | 新版知识库编辑器框架 |
| Vite 8.1 | 前端构建工具与 manifest |
| TypeScript 6.0 | 编辑器类型安全 |
| BlockNote 0.51 | 块编辑器 |
| Mantine 9.4 | React UI 组件库 |
| Markdown2 | Markdown 渲染 |
| Bleach | HTML 清理 |

---

## 项目结构

```
my-blog/
│
├── backend/                      # 后端代码
│   ├── __init__.py              # 后端包标记
│   ├── app.py                   # 应用主入口、蓝图注册、Vite 清单读取
│   ├── config.py                # 配置管理（唯一配置入口）
│   ├── logger.py                # 日志系统
│   ├── auth_decorators.py       # 登录与权限装饰器
│   ├── image_cleanup_tool.py    # 图片清理工具
│   ├── db_check.py              # 数据库完整性检查
│   ├── migrate_db.py            # 旧版多用户迁移脚本（新迁移请用 migrations/ 运行器）
│   ├── export.py                # 数据导出
│   ├── import_blog.py           # 博客导入
│   ├── import_posts.py          # 文章导入
│   │
│   ├── models/                  # 数据模型层（按领域拆分）
│   │   ├── db.py               # 连接/上下文/分页/建表初始化/FTS
│   │   ├── posts.py            # 文章 CRUD/搜索/访问控制
│   │   ├── categories.py       # 博客分类
│   │   ├── knowledge.py        # 知识库分类树/文档/沉淀
│   │   ├── tags.py             # 标签
│   │   ├── comments.py         # 评论与图片优化记录
│   │   ├── users.py            # 用户/Passkey/AI 配置/API Key
│   │   ├── cards.py            # 卡片与标注
│   │   ├── utils.py            # HTML 清理与文本截断
│   │   ├── draft.py            # 草稿模型
│   │   ├── models.py           # re-export 兼容壳（勿新增代码）
│   │   └── __init__.py         # 模型导出
│   │
│   ├── routes/                  # 路由模块（蓝图）
│   │   ├── __init__.py         # 蓝图注册
│   │   ├── auth.py             # 认证路由（登录/Passkey）
│   │   ├── blog.py             # 博客公开路由
│   │   ├── admin.py            # 管理后台路由（含移动端上传蓝图）
│   │   ├── api.py              # RESTful API
│   │   ├── ai.py               # AI 功能路由
│   │   ├── knowledge_base.py   # 旧版插件 API（页面已重定向到 knowledge）
│   │   ├── knowledge.py        # 新版知识空间
│   │   └── drafts.py           # 草稿同步路由
│   │
│   ├── ai_services/            # AI 服务层
│   │   ├── __init__.py
│   │   ├── tag_generator.py    # 标签生成服务
│   │   ├── card_merger.py      # AI 卡片合并
│   │   ├── base.py             # 提供商抽象基类
│   │   ├── openai_compatible.py # OpenAI 兼容 API 共享实现
│   │   ├── openai_provider.py
│   │   ├── volcengine_provider.py
│   │   ├── volcengine_coding_provider.py
│   │   ├── zhipu_coding_provider.py
│   │   └── dashscope_provider.py
│   │
│   ├── utils/                  # 工具函数
│   │   ├── asset_version.py    # 旧版静态资源版本管理
│   │   ├── asset_optimizer.py  # 资源优化与路径映射
│   │   ├── image_cleanup.py    # 图片清理逻辑
│   │   ├── image_processor.py  # 图片处理
│   │   └── template_helpers.py # 模板辅助函数
│   │
│   ├── tasks/                  # 后台任务
│   │   └── image_optimization_task.py  # 图片优化任务
│   │
│   └── migrations/             # 版本化数据库迁移
│       ├── __init__.py         # 迁移运行器（schema_migrations 版本表）
│       ├── __main__.py         # python -m backend.migrations 入口
│       ├── migrate_add_access_control.py
│       ├── migrate_add_post_type.py
│       ├── migrate_ai_features.py
│       ├── migrate_drafts.py
│       ├── migrate_image_optimization.py
│       ├── migrate_knowledge_base.py
│       └── migrate_multiauthor.py
│
├── frontend/                    # 新版知识库编辑器（React + Vite）
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│
├── templates/                   # Jinja2 模板
│   ├── base.html                # 基础模板
│   ├── index.html               # 首页
│   ├── post.html                # 文章详情
│   ├── login.html               # 登录页
│   ├── change_password.html     # 修改密码 / Passkey 管理
│   ├── admin/                   # 管理后台模板
│   └── knowledge/               # 知识空间模板
│       ├── index.html
│       ├── category.html
│       ├── doc.html
│       ├── editor.html
│       └── _tree.html
│
├── static/                      # 静态资源
│   ├── css/                    # 样式文件
│   ├── js/                     # 传统 JavaScript
│   ├── vendor/                 # 第三方库
│   ├── uploads/                # 用户上传内容
│   ├── manifest.json           # 旧版资源清单
│   └── frontend/               # Vite 构建产物（运行 npm run build 生成）
│       └── .vite/manifest.json
│
├── db/                          # 数据库目录
│   └── simple_blog.db          # SQLite 数据库
│
├── logs/                        # 日志目录
│
├── browser-extension/           # Chrome 扩展（Manifest V3）
│
├── safari-extension/            # Safari 扩展
│
├── tests/                       # 测试代码
├── scripts/                     # 项目脚本与诊断工具
│   ├── start.sh
│   ├── install-service.sh
│   ├── upgrade.sh
│   ├── rollback.sh
│   ├── verify_upgrade.sh
│   ├── generate_manifest.py
│   └── diagnostics/
│
├── .github/workflows/           # CI 配置
├── docs/                        # 文档
└── requirements.txt             # Python 依赖
```

---

## 数据模型

> 注：以下 SQL 取自 `backend/models/db.py::init_db()` 及相关迁移脚本。实际建表使用 `CREATE TABLE IF NOT EXISTS`，并在后续通过 `ALTER TABLE ADD COLUMN` 渐进式增加列，以保证旧数据库平滑升级。

### 核心表结构

#### 用户表 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'author',   -- admin/editor/author
    display_name TEXT,
    bio TEXT,
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ai_tag_generation_enabled BOOLEAN DEFAULT 1,
    ai_provider TEXT DEFAULT 'openai',
    ai_api_key TEXT,
    ai_model TEXT DEFAULT 'gpt-3.5-turbo'
);
```

#### 文章表 (posts)
```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    is_published BOOLEAN DEFAULT 0,
    category_id INTEGER REFERENCES categories(id),
    author_id INTEGER DEFAULT 1 REFERENCES users(id),
    access_level TEXT DEFAULT 'public',   -- public/login/password/private
    access_password TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 以下列通过迁移脚本渐进式添加
    post_type TEXT DEFAULT 'blog',        -- blog / knowledge
    type TEXT DEFAULT 'post',             -- post / note
    source_card_ids TEXT,
    excerpt TEXT,
    metadata TEXT,
    parent_note_id INTEGER,
    link_count INTEGER DEFAULT 0,
    content_format TEXT DEFAULT 'html',   -- html / markdown
    sort_order INTEGER DEFAULT 0,
    source_post_id INTEGER
);
```

#### 全文搜索表 (posts_fts)
```sql
CREATE VIRTUAL TABLE posts_fts USING fts5(
    title,
    content,
    content='posts',
    content_rowid='rowid'
);
```
> FTS 索引不再通过触发器自动维护，而是在 `posts` 的增删改查操作中手动同步。

#### 分类表 (categories)
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    parent_id INTEGER,
    slug TEXT,
    sort_order INTEGER DEFAULT 0,
    space TEXT DEFAULT 'blog',        -- blog / knowledge
    icon TEXT,
    description TEXT,
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
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);
```

#### 评论表 (comments)
```sql
CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    author_email TEXT,
    content TEXT NOT NULL,
    is_visible BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Passkey 表 (user_passkeys)
```sql
CREATE TABLE user_passkeys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credential_id BLOB NOT NULL UNIQUE,
    public_key BLOB NOT NULL,
    sign_count INTEGER DEFAULT 0,
    device_name TEXT,
    transports TEXT,
    credential_device_type TEXT,
    backup_eligible BOOLEAN DEFAULT 0,
    backup_state BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);
```

#### 知识库卡片表 (cards)
```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT,
    content TEXT NOT NULL,
    tags TEXT,
    status TEXT DEFAULT 'idea',       -- idea/incubating/draft/published
    source TEXT DEFAULT 'web',
    linked_article_id INTEGER REFERENCES posts(id),
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
    original_hash TEXT,
    thumbnail_path TEXT,
    medium_path TEXT,
    large_path TEXT,
    original_size INTEGER,
    optimized_size INTEGER,
    status TEXT DEFAULT 'pending',    -- pending/processing/completed/failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### 卡片标注表 (card_annotations)
```sql
CREATE TABLE card_annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    card_id INTEGER REFERENCES cards(id),
    source_url TEXT NOT NULL,
    annotation_text TEXT,
    xpath TEXT,
    color TEXT DEFAULT 'yellow',
    note TEXT,
    annotation_type TEXT DEFAULT 'highlight',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API 密钥表 (api_keys)
```sql
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    api_key TEXT NOT NULL UNIQUE,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 笔记链接表 (note_links)
```sql
CREATE TABLE note_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    target_post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    link_text TEXT,
    link_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_post_id, target_post_id)
);
```

#### AI 使用记录表 (ai_tag_history)
```sql
CREATE TABLE ai_tag_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prompt TEXT,
    generated_tags TEXT,
    model_used TEXT,
    tokens_used INTEGER,
    cost DECIMAL(10, 6),
    currency TEXT DEFAULT 'USD',
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

# 旧版知识库/插件 API 蓝图
app.register_blueprint(knowledge_base_bp, url_prefix='/knowledge_base')

# 新版知识空间蓝图
app.register_blueprint(knowledge_bp, url_prefix='/knowledge')

# 草稿同步蓝图
app.register_blueprint(drafts_bp)

# 移动端蓝图
app.register_blueprint(mobile_bp, url_prefix='/mobile')
```

### 路由职责划分

| 蓝图 | 前缀 | 职责 | 主要端点 |
|------|------|------|----------|
| `auth_bp` | 无 | 用户认证 | `/login`, `/logout`, `/change-password`, `/passkeys/*` |
| `blog_bp` | 无 | 公开内容 | `/`, `/post/<id>`, `/search`, `/archive`, `/category/<id>`, `/author/<id>` |
| `admin_bp` | `/admin` | 管理后台 | `/admin`, `/admin/new`, `/admin/edit/<id>`, `/admin/users/*`, `/admin/import/*`, `/admin/export/*` |
| `api_bp` | `/api` | REST API | `/api/posts`, `/api/share/qrcode`, `/api/image/original-url` |
| `ai_bp` | `/admin/ai` | AI 功能 | `/admin/ai/generate-tags`, `/admin/ai/generate-summary`, `/admin/ai/recommend-posts`, `/admin/ai/continue-writing`, `/admin/ai/organize-content`, `/admin/ai/configure`, `/admin/ai/history` |
| `knowledge_base_bp` | `/knowledge_base` | 插件 API（旧） | `/knowledge_base/api/plugin/submit`, `/knowledge_base/api/plugin/sync-annotations`, `/knowledge_base/api/plugin/annotations`, `/knowledge_base/api/cards/*` |
| `knowledge_bp` | `/knowledge` | 知识空间（新） | `/knowledge/`, `/knowledge/category/<id>`, `/knowledge/doc/<id>`, `/knowledge/doc/new`, `/knowledge/doc/<id>/edit`, `/knowledge/reorder`, `/knowledge/doc/upload-image`, `/knowledge/doc/<id>/autosave` |
| `drafts_bp` | 无 | 草稿同步 | `/api/drafts/*` |
| `mobile_bp` | `/mobile` | 移动端 | `/mobile/upload`, `/mobile/my-posts` |

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
| 生成标题 | `/admin/ai/generate-title` | 根据内容生成标题 |
| 生成摘要 | `/admin/ai/generate-summary` | 生成文章摘要 |
| 推荐文章 | `/admin/ai/recommend-posts` | 推荐相关文章 |
| 内容续写 | `/admin/ai/continue-writing` | 智能续写 |
| 内容整理 | `/admin/ai/organize-content` | 智能整理建议 |
| AI 配置 | `/admin/ai/configure` | 获取/保存 AI 配置 |
| AI 状态 | `/admin/ai/status` | 检查 AI 是否可用 |
| AI 历史 | `/admin/ai/history` | 查看 AI 调用记录 |

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

### 模板层

项目使用 Jinja2 模板，基础模板 `templates/base.html` 定义页面骨架，各功能页面通过 `{% extends %}` 继承并填充 `title`、`content`、`scripts` 等块。

### 传统前端（博客与后台）

- `static/js/` 包含原生 JavaScript 模块：主交互 `main.js`、编辑器 `editor.js`、草稿同步 `draft-sync.js`、快捷键 `shortcuts.js`、Passkey `passkeys.js`、移动端编辑器 `mobile-editor.js` 等。
- `static/css/` 包含主题样式、响应式布局、移动端适配、图片灯箱等样式文件。
- 静态资源版本由 `static/manifest.json` 与 `backend/utils/asset_version.py` 管理，模板通过 `?v=hash` 防止缓存。

### 新版知识库编辑器

知识库文档编辑器是一个独立的 React + Vite 前端片段：

| 文件/目录 | 说明 |
|----------|------|
| `frontend/package.json` | 依赖：React 19.2、Vite 8.1、BlockNote 0.51、Mantine 9.4 |
| `frontend/vite.config.ts` | 构建到 `../static/frontend/`，启用 manifest |
| `frontend/src/main.tsx` | 挂载入口 |
| `frontend/src/KbEditorApp.tsx` | 编辑器主组件：标题、目录、标签、排序、发布、保存、自动保存、AI 面板 |
| `frontend/src/components/KbBlockNoteEditor.tsx` | BlockNote 编辑器封装 |
| `frontend/src/components/AiPanel.tsx` | AI 整理/摘要/续写/历史卡片 |
| `frontend/src/components/TocPanel.tsx` | 文档大纲 |
| `frontend/src/hooks/useAutoSave.ts` | 3 秒防抖自动保存 + 草稿恢复 |
| `frontend/src/styles/kb-editor.css` | 编辑器样式 |

构建流程：

```bash
cd frontend
npm install
npm run build
```

产物写入 `static/frontend/`，生成 `static/frontend/.vite/manifest.json`。Flask 在 `backend/app.py` 中通过 `get_vite_manifest()` 与 `vite_asset()` 读取清单，并在 `templates/knowledge/editor.html` 中注入对应的 JS/CSS 路径。

### 状态管理

- 服务器端草稿：通过 `/api/drafts/*` 与知识库编辑器的 `/knowledge/doc/<id>/autosave` 实现多设备同步。
- 本地状态：LocalStorage 用于保存 UI 偏好（如侧边栏折叠状态）和临时草稿。

---

## 扩展性设计

### 浏览器扩展集成

提供 Chrome / Safari 扩展（`browser-extension/`、`safari-extension/`），基于 Manifest V3：

```
浏览器扩展
    ↓
API Key 认证（X-API-Key）
    ↓
POST /knowledge_base/api/plugin/submit
    ↓
创建卡片或博客文章
```

主要插件端点（均在 `/knowledge_base` 蓝图下）：

| 端点 | 说明 |
|------|------|
| `POST /knowledge_base/api/plugin/submit` | 提交捕获内容 |
| `POST /knowledge_base/api/plugin/sync-annotations` | 同步网页高亮/批注 |
| `GET /knowledge_base/api/plugin/annotations` | 获取某 URL 的批注 |
| `GET /knowledge_base/api/plugin/recent` | 获取最近捕获 |

这些端点已豁免 CSRF 保护，使用 `api_keys` 表中的密钥认证。扩展默认连接 `http://localhost:5001/knowledge_base`，可在设置中修改为远程服务器地址。

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
| `logs/login.log` | 登录日志 |
| `logs/operation.log` | 操作日志 |
| `logs/sql.log` | SQL 查询日志 |

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

迁移由版本化运行器管理（`schema_migrations` 表记录已应用版本）：

```bash
# 应用所有待执行迁移
python -m backend.migrations

# 查看迁移状态
python -m backend.migrations status
```

新增迁移：在 `backend/migrations/` 新建 `migrate_xxx.py`（提供幂等的 `migrate()` 函数），
并在 `backend/migrations/__init__.py` 的 `MIGRATIONS` 注册表末尾追加条目。

### 版本升级

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt

# 运行迁移
python -m backend.migrations

# 重启服务
sudo systemctl restart simple-blog
```

---

本文档持续更新中。如有疑问，请参考 [API 文档](./api-documentation.md) 或 [部署指南](../DEPLOYMENT.md)。
