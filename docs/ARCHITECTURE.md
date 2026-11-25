# Simple Blog 架构文档

## 目录

- [系统概述](#系统概述)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [数据模型](#数据模型)
- [路由架构](#路由架构)
- [应用工厂与启动流程](#应用工厂与启动流程)
- [后台任务队列](#后台任务队列)
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
| Flask-Limiter | 3.5+ | 速率限制（默认 memory://，单 worker） |
| Flask-Caching | 2.x+ | 简单缓存 |
| numpy | 1.26+ | 向量相似度计算 |
| webauthn | 2.7+ | Passkey 认证 |
| Pillow | 13.0+ | 图片处理 |
| pillow-heif | 0.13+ | HEIC 格式支持 |
| qrcode | - | 分享二维码 |
| html2text | - | Markdown 转换 |

### AI 集成

| 提供商 | SDK | 模型 |
|--------|-----|------|
| 阿里百炼 | openai（兼容模式） | 通义千问系列 |
| DeepSeek | openai（兼容模式） | deepseek-v4-flash / deepseek-v4-pro |
| 自定义 | openai（兼容模式） | 任意 OpenAI 兼容接口（自备 Base URL） |

### 前端

| 技术 | 用途 |
|------|------|
| Jinja2 | 服务器端模板渲染 |
| Vanilla JavaScript | 博客/后台核心交互 |
| Quill.js | 传统富文本编辑器 |
| 原生 CSS | 样式系统、响应式、暗黑模式 |
| React 19.3 | 新版知识库编辑器框架 |
| Vite 8.1 | 前端构建工具与 manifest |
| TypeScript 6.0 | 编辑器类型安全 |
| BlockNote 0.55 | 块编辑器 |
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
│   ├── app.py                   # create_app() 工厂、蓝图注册、Vite 清单读取、CLI
│   ├── config.py                # 配置管理（唯一配置入口）
│   ├── logger.py                # 日志系统
│   ├── auth_decorators.py       # 登录与权限装饰器
│   ├── image_cleanup_tool.py    # 图片清理工具
│   ├── db_check.py              # 数据库完整性检查
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
│   │   ├── embeddings.py       # 向量存取与相似度检索（带进程内缓存）
│   │   ├── revisions.py        # 文章/文档修订历史与回收站辅助
│   │   ├── ai_catalog.py       # AI 提供商与模型目录（站点级）
│   │   ├── site_settings.py    # 站点级键值配置（站点图标版本等）
│   │   ├── utils.py            # HTML 清理与文本截断
│   │   ├── draft.py            # 草稿模型
│   │   └── __init__.py         # 聚合各领域模块的 __all__，对外唯一入口
│   │
│   ├── routes/                  # 路由模块（蓝图）
│   │   ├── __init__.py         # 蓝图导出
│   │   ├── auth.py             # 认证路由（登录/Passkey）
│   │   ├── blog/               # 博客公开路由（feed / post_detail / search / mobile）
│   │   ├── admin/              # 管理后台路由 + 移动端上传蓝图
│   │   ├── api.py              # RESTful API
│   │   ├── ai/                 # AI 功能路由（config / generation / organize / mentor）
│   │   ├── knowledge_base.py   # 旧版插件 API（页面已重定向到 knowledge）
│   │   ├── knowledge.py        # 新版知识空间
│   │   ├── drafts.py           # 草稿同步路由
│   │   ├── review.py           # 回顾页 / 每周回顾
│   │   └── legacy.py           # 旧客户端路径兼容（/new、/api/plugin/*、/api/cards/*）
│   │
│   ├── services/                # 服务层
│   │   ├── backup.py           # 全量备份/恢复
│   │   ├── task_queue.py       # SQLite 持久化后台任务队列
│   │   └── weekly_review.py    # 每周回顾生成
│   │
│   ├── ai_services/            # AI 服务层
│   │   ├── tag_generator.py    # 标签生成服务
│   │   ├── card_merger.py      # AI 卡片合并
│   │   ├── base.py             # 提供商抽象基类
│   │   ├── openai_compatible.py # OpenAI 兼容 API 共享实现
│   │   ├── dashscope_provider.py
│   │   ├── deepseek_provider.py
│   │   ├── custom_provider.py
│   │   ├── embeddings.py       # Embedding 服务封装
│   │   ├── provider_defaults.py # 各提供商默认模型
│   │   └── url_guard.py        # AI Base URL SSRF 校验
│   │
│   ├── utils/                  # 工具函数
│   │   ├── asset_version.py    # 静态资源版本管理
│   │   ├── image_cleanup.py    # 图片清理逻辑
│   │   ├── image_processor.py  # 图片处理
│   │   ├── secret_box.py       # API Key 对称加密
│   │   ├── site_icon.py        # 站点图标处理
│   │   ├── markdown_renderer.py # 内容渲染（markdown / html 分流）
│   │   ├── template_helpers.py # 模板辅助函数（static_file/vite_asset）
│   │   └── timezone.py         # 本地时区工具
│   │
│   ├── tasks/                  # 后台任务
│   │   ├── image_optimization_task.py  # 图片优化线程池
│   │   └── embedding_task.py           # Embedding 任务（生产走持久化队列）
│   │
│   └── migrations/             # 版本化数据库迁移（000 baseline ~ 015）
│       ├── __init__.py         # 迁移运行器（schema_migrations 版本表）
│       ├── __main__.py         # python -m backend.migrations [status]
│       └── migrate_*.py        # 各版本迁移
│
├── frontend/                    # 新版知识库编辑器（React + Vite）
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html               # 本地开发挂载页（npm run dev）
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
│
├── static/                      # 静态资源
│   ├── css/                    # 样式文件（含 editor-page.css / post-page.css）
│   ├── js/                     # 传统 JavaScript
│   ├── vendor/                 # 第三方库（Quill 等）
│   ├── uploads/                # 用户上传内容（不入库）
│   ├── manifest.json           # 传统静态资源清单
│   └── frontend/               # Vite 构建产物（不入库，npm run build 生成）
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
├── tests/                       # 单元/集成测试 + tests/e2e/ 浏览器 E2E
├── scripts/                     # 项目脚本与诊断工具
│   ├── start.sh
│   ├── build-frontend.sh       # 前端构建（依赖变化才 npm ci）
│   ├── install-service.sh
│   ├── upgrade.sh
│   ├── rollback.sh
│   ├── verify_upgrade.sh
│   ├── backup.sh
│   ├── generate_manifest.py
│   └── diagnostics/
│
├── .github/workflows/           # CI（backend / frontend / e2e / audit）
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
    ai_provider TEXT DEFAULT 'dashscope',
    ai_api_key TEXT,
    ai_model TEXT DEFAULT 'qwen-turbo'
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

#### 文章修订表 (post_revisions)
```sql
CREATE TABLE post_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_format TEXT DEFAULT 'html',
    category_id INTEGER,
    tags_json TEXT,
    access_level TEXT DEFAULT 'public',
    access_password TEXT,
    post_type TEXT DEFAULT 'blog',
    type TEXT DEFAULT 'post',
    author_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
> 每次保存正文前生成修订快照；后台「历史版本」/「回收站」基于此与 `posts.deleted_at`。

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

#### 站点设置表 (site_settings)
```sql
CREATE TABLE site_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
> 站点级键值配置（目前用于自定义站点图标版本等）。

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

#### 向量表 (embeddings)
```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,   -- post / doc / card
    source_id INTEGER NOT NULL,
    model TEXT,
    vector BLOB,
    content_hash TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_type, source_id)
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

#### 后台任务表 (background_tasks)
```sql
CREATE TABLE background_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,                -- review_weekly / ai_title / embedding
    dedupe_key TEXT,
    payload TEXT NOT NULL,             -- JSON
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    run_after TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMP,
    locked_by TEXT,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 部分唯一索引：同 kind+dedupe_key 只允许一个 pending/running
```

#### AI 提供商表 (ai_providers) / 模型表 (ai_models)
```sql
CREATE TABLE ai_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    driver TEXT NOT NULL,
    base_url TEXT,
    currency TEXT NOT NULL DEFAULT 'CNY',
    allow_custom_model BOOLEAN DEFAULT 0,
    requires_base_url BOOLEAN DEFAULT 0,
    enabled BOOLEAN DEFAULT 1,
    is_builtin BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL REFERENCES ai_providers(id) ON DELETE CASCADE,
    model_id TEXT NOT NULL,
    display_name TEXT,
    description TEXT,
    input_price REAL,
    output_price REAL,
    enabled BOOLEAN DEFAULT 1,
    is_default BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider_id, model_id)
);
```
> 站点级 AI 目录，后台可启用/禁用提供商与模型、维护价格。

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
# backend/app.py::create_app()

# 认证蓝图
app.register_blueprint(auth_bp)

# 博客蓝图
app.register_blueprint(blog_bp)

# 管理后台蓝图（admin_bp 自带 url_prefix='/admin'）
app.register_blueprint(admin_bp)

# API 蓝图
app.register_blueprint(api_bp, url_prefix='/api')

# AI 蓝图（ai_bp 自带 url_prefix='/admin/ai'）
app.register_blueprint(ai_bp)

# 旧版知识库/插件 API 蓝图
app.register_blueprint(knowledge_base_bp, url_prefix='/knowledge_base')

# 新版知识空间蓝图
app.register_blueprint(knowledge_bp, url_prefix='/knowledge')

# 草稿同步蓝图
app.register_blueprint(drafts_bp)

# 回顾页蓝图（那年今日 / 写作热力 / 每周回顾）
app.register_blueprint(review_bp)

# 旧客户端路径兼容蓝图（/new、/api/plugin/*、/api/cards/*）
app.register_blueprint(legacy_bp)

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
| `review_bp` | 无 | 回顾与统计 | `/review`, `/api/review/today`, `/api/review/activity`, `/api/review/weekly` |
| `legacy_bp` | 无 | 旧客户端路径兼容 | `/new`, `/api/plugin/*`, `/api/cards/*`（内部转发到 knowledge_base 视图） |
| `mobile_bp` | `/mobile` | 移动端 | `/mobile/upload`, `/mobile/my-posts` |

健康检查端点（不属于任何蓝图）：`GET /healthz`（存活）、`GET /readyz`（就绪，含数据库探测）。

---

## 应用工厂与启动流程

`backend/app.py` 暴露 `create_app(config_overrides=None)`，模块级 `app = create_app()` 供 gunicorn 与旧脚本使用：

```python
# gunicorn backend.app:app
# 测试可直接创建隔离实例
app = create_app({'TESTING': True, 'DATABASE_URL': 'sqlite:///:memory:'})
```

启动顺序：

1. 加载 `backend.config`
2. `create_app()` 应用 `config_overrides`（测试/多实例）
3. 初始化扩展（CSRF / Limiter / Cache / 日志），每个实例独立
4. 注册蓝图与模板过滤器
5. 非 DEBUG 环境默认 `AUTO_MIGRATE=True`，执行待应用迁移，失败即拒绝启动
6. 启动备份调度器与持久化任务 worker（`TESTING`/pytest 下跳过）

可选副作用开关：`SETUP_LOGGING`、`REGENERATE_ASSETS`，测试中可关闭。

---

## 后台任务队列

生产环境的异步任务写入 SQLite `background_tasks` 表，由每个进程内的 worker 抢占执行：

- 入队：`backend/services/task_queue.py::enqueue(kind, payload, dedupe_key=...)`
- 支持任务类型：`review_weekly`、`ai_title`、`embedding`
- 去重：`dedupe_key` + 部分唯一索引（仅 `pending`/`running` 生效）
- 重试：失败按指数退避，超过 `max_attempts` 置为 `failed`
- 抢占：`BEGIN IMMEDIATE` + 条件更新，多 worker 只执行一次
- 手工排空（测试/运维）：`run_pending_tasks(app)`

图片优化任务仍使用进程内线程池（状态持久化在 `optimized_images`，启动时会重新入队未完成任务）。

---

## 安全机制

### 1. 认证与授权

#### 密码认证
- 使用 `werkzeug.security` 进行密码哈希
- 普通用户密码强度：至少 10 位，包含大小写字母和数字
- `ADMIN_PASSWORD` 环境变量：至少 12 位，且拒绝 `password`、`admin123` 等常见弱密码

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
# 每个 app 实例独立初始化（create_app 内）
app_csrf = CSRFProtect()
app_csrf.init_app(app)
app.csrf_protect = app_csrf

# 部分端点豁免（浏览器扩展 / 移动端 / 备份恢复无法携带 token）
app_csrf.exempt(app.view_functions['knowledge_base.plugin_submit'])
app_csrf.exempt(app.view_functions['knowledge_base.sync_annotations'])
app_csrf.exempt(app.view_functions['knowledge_base.plugin_validate'])
app_csrf.exempt(app.view_functions['mobile.mobile_upload_image'])
app_csrf.exempt(app.view_functions['ai.test_ai_config'])
app_csrf.exempt(app.view_functions['admin.restore_backup'])
app_csrf.exempt(app.view_functions['legacy.plugin_submit'])
app_csrf.exempt(app.view_functions['legacy.plugin_sync_annotations'])
```

> 豁免端点仍需通过会话校验与权限装饰器；`admin.restore_backup` 在视图内提高 body 上限后手动校验 CSRF。

### 3. 速率限制

```python
app_limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri="memory://",
)
app_limiter.init_app(app)
app.limiter = app_limiter

# 单端点限流在注册蓝图后按 view function 逐个应用（_apply_route_limit）
```

> `memory://` 只在单进程内有效，因此生产部署固定 `gunicorn --workers 1`；多 worker 需改用 Redis 或先迁移 PostgreSQL。登录接口目前尚未单独限流（见 backlog SEC-1）。

### 4. XSS 防护

```python
# 渲染管道按 content_format 分流（backend/utils/markdown_renderer.py）
# - markdown：markdown2 解析 + bleach 清洗
# - html（默认）：不做 Markdown 解析，仅 bleach 清洗，
#   避免纯文本里的 _xxx_ 被误解析成 <em> 破坏 URL
post['content_html'] = render_content(
    post['content'], post.get('content_format')
)
```

> 历史教训：所有内容曾统一走 markdown2，移动端上传图片的 URL 以纯文本写入正文时，
> 文件名中的下划线被解析为斜体（`20261009_143339_x.png` → `<em>` 注入 URL），
> 导致图片 404。治理措施：上传文件名改用连字符（`20261009-143339-x.png`，
> backend/routes/admin/media.py）、渲染按格式分流、迁移 011 纠偏存量文章的格式标注。

### 5. SQL 注入防护

所有数据库查询使用参数化查询：

```python
# 安全的查询方式
cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
```

### 6. 会话安全

```python
# 会话配置（backend/config.py）
SESSION_COOKIE_HTTPONLY = True    # 防止 JS 访问
SESSION_COOKIE_SAMESITE = 'Lax'   # CSRF 防护
SESSION_COOKIE_SECURE = True      # 仅生产且 FORCE_HTTPS=True 时为 True
```

> 生产环境需要在 `.env` 显式设置 `FORCE_HTTPS=True`，否则 Cookie 不带 `Secure` 标记（启动时会有告警）。

---

## AI 服务架构

### 服务抽象层

```python
class TagGenerator:
    """AI 标签生成器"""

    @staticmethod
    def create_provider(provider_name, api_key, model, base_url=None):
        """创建 AI 提供商实例"""
        providers = {
            'dashscope': DashscopeProvider,
            'deepseek': DeepSeekProvider,
            'custom': CustomOpenAIProvider,  # 需传入 base_url
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
| `frontend/package.json` | 依赖：React 19.3、Vite 8.1、BlockNote 0.55、Mantine 9.4 |
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
# 依赖变化时才 npm ci，并校验 manifest
./scripts/build-frontend.sh
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

迁移由版本化运行器管理（`schema_migrations` 表记录已应用版本），共 16 个：`000_baseline`（新建空库时创建基础表，复用 `init_db()`）到 `015_background_tasks`。

```bash
# 应用所有待执行迁移
python -m backend.migrations

# 查看迁移状态
python -m backend.migrations status
```

`AUTO_MIGRATE` 在非 DEBUG 环境默认 `True`（生产默认开启），应用启动时自动应用待执行迁移，失败则拒绝启动；`DEBUG=True` 与测试环境默认关闭。

新增迁移：在 `backend/migrations/` 新建 `migrate_xxx.py`（提供幂等的 `migrate()` 函数），
在 `backend/migrations/__init__.py` 的 `MIGRATIONS` 注册表末尾追加条目，
然后运行 `python scripts/generate_schema_snapshot.py` 更新 `tests/schema_snapshot.json`（否则 CI 失败）。

### 版本升级

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt

# 运行迁移（生产启动时 AUTO_MIGRATE 也会自动执行）
python -m backend.migrations

# 构建前端（static/frontend 不入库）
./scripts/build-frontend.sh

# 重启服务
sudo systemctl restart simple-blog
```

---

本文档持续更新中。如有疑问，请参考 [API 文档](./api-documentation.md) 或 [部署指南](../DEPLOYMENT.md)。
