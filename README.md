# Simple Blog

简洁、优雅的个人博客系统 + 知识库管理

## 快速开始

```bash
git clone https://github.com/lbxxgn/my-blog.git
cd my-blog
cp .env.example .env
# 编辑 .env，设置管理员密码和 SECRET_KEY
pip install -r requirements.txt

# 构建新版知识库编辑器（React + Vite）
cd frontend && npm install && npm run build && cd ..

# 启动服务
python backend/app.py
```

访问 http://localhost:5001，默认用户：admin

## 主要功能

### 博客功能
- **富文本编辑**：Quill 编辑器，支持粘贴保持格式
- **多用户系统**：支持 admin / editor / author 三种角色
- **分类和标签**：灵活的内容组织
- **评论系统**：支持评论管理
- **全文搜索**：SQLite FTS5 全文搜索
- **访问控制**：公开 / 登录用户 / 密码保护 / 私密
- **导入/导出**：文章数据的导入与导出

### 知识库
- **独立知识空间**（`/knowledge`）：目录树 + 文档，支持新版 React 编辑器
- **卡片管理**（`/knowledge_base`）：想法、孵化、草稿状态
- **时间线视图**：按时间查看所有内容
- **浏览器扩展采集**：一键采集网页内容
- **AI 辅助**：智能标签生成、内容合并、摘要与推荐

### AI 功能
- **标签生成**：自动为文章生成相关标签
- **摘要生成**：一键生成文章摘要
- **相关推荐**：基于内容推荐相关文章
- **内容续写/整理**：智能续写与内容组织
- **多提供商支持**：OpenAI / 火山引擎 / 阿里百炼

### 安全与体验
- **Passkey / WebAuthn**：Face ID / Touch ID 快捷登录
- **图片上传与优化**：上传后自动压缩、生成多尺寸、转换为 WebP
- **草稿同步**：多设备草稿自动保存与冲突检测
- **暗黑模式、响应式设计、代码复制、图片灯箱、键盘快捷键**

### 扩展与工具
- **浏览器扩展 / Safari 扩展**：网页内容采集
- **移动端蓝图**（`/mobile`）：移动端 API 支持
- **静态资源优化**：自动版本管理与压缩（`backend/utils/asset_optimizer.py`）

## 技术栈

- **后端**：Flask 3.1.3、Python 3.11+、SQLite 3 + FTS5、Jinja2
- **传统前端**：Vanilla JS + Quill 编辑器
- **新版知识库编辑器**：React 19.2 + Vite 8.1 + BlockNote 0.51 + Mantine 9
- **AI**：OpenAI API / 火山引擎 / 阿里百炼
- **测试**：pytest + pytest-cov（271 个测试）

## 项目结构

```
my-blog/
├── backend/                    # 后端代码
│   ├── models/                 # 数据模型
│   ├── routes/                 # 路由蓝图模块
│   │   ├── auth.py             # auth_bp
│   │   ├── blog.py             # blog_bp
│   │   ├── admin.py            # admin_bp (/admin)
│   │   ├── api.py              # api_bp (/api)
│   │   ├── ai.py               # ai_bp (/admin/ai)
│   │   ├── knowledge_base.py   # knowledge_base_bp (/knowledge_base)
│   │   ├── knowledge.py        # knowledge_bp (/knowledge)
│   │   └── drafts.py           # drafts_bp
│   ├── ai_services/            # AI 服务
│   ├── utils/                  # 工具模块
│   │   └── asset_optimizer.py  # 静态资源优化
│   ├── auth_decorators.py      # 认证装饰器
│   └── app.py                  # 应用入口
├── frontend/                   # React 知识库编辑器源码
├── static/                     # 静态资源
│   ├── css/                    # 传统样式
│   ├── js/                     # 传统脚本
│   └── frontend/               # Vite 构建产物（含 .vite/manifest.json）
├── templates/                  # Jinja2 HTML 模板
├── browser-extension/          # 浏览器扩展
├── safari-extension/           # Safari 扩展
├── scripts/                    # 运维脚本
│   ├── start.sh
│   ├── upgrade.sh
│   ├── rollback.sh
│   ├── verify_upgrade.sh
│   ├── install-service.sh
│   └── generate_manifest.py
├── tests/                      # 测试代码
│   ├── test_kb_editor_api.py
│   ├── e2e_kb_editor.py
│   └── ...
└── docs/                       # 文档
```

## 📚 文档

### 快速开始
- [快速启动](docs/startup.md) - 环境配置和启动
- [快速升级参考](QUICKSTART.md) - 一行命令升级与启动
- [前端构建指南](docs/frontend-build.md) - React/Vite 知识库编辑器构建说明
- [知识库重构说明](docs/knowledge-base-refactor.md) - 新版独立知识空间介绍

### 部署运维
- [部署指南](DEPLOYMENT.md) - 完整部署文档

### 更多文档
- [完整文档索引](docs/) - 所有文档的导航中心
- [API 文档](docs/api-documentation.md) - REST API 参考
- [测试说明](docs/testing.md) - 测试运行方式与调试方法
- [归档报告](docs/archive/reports/) - 历史优化与验收记录

## 开发

```bash
# 快速检查（语法 + 图片相关关键测试）
make check

# 运行全部测试
make test

# 构建静态资源
make build-assets

# 启动开发服务器
make run
```

## 部署

项目支持以下部署方式：

- **开发环境**：直接运行 `python backend/app.py`
- **生产环境**：使用 `scripts/install-service.sh` 安装 systemd 服务（参考 [部署指南](DEPLOYMENT.md)）
- **Docker**：当前未提供 Docker 部署方案，请使用脚本或 systemd 方式部署

## 环境变量

主要环境变量（完整示例见 `.env.example`）：

```bash
# 管理员账号
ADMIN_USERNAME=admin
ADMIN_PASSWORD=YourSecurePassword123!

# 应用安全
SECRET_KEY=change-this-to-a-random-secret-key-in-production
DEBUG=False
PORT=5001
FLASK_ENV=production
FORCE_HTTPS=False

# 网站信息
SITE_NAME=我的博客
SITE_DESCRIPTION=一个简单的博客系统
SITE_AUTHOR=管理员

# Passkey / WebAuthn
PASSKEY_RP_NAME=Simple Blog
PASSKEY_RP_ID=localhost
PASSKEY_ALLOWED_ORIGINS=http://localhost:5001,https://example.com
REMEMBER_DEVICE_DAYS=90

# AI 配置（可选）
AI_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
VOLCENGINE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AI_MODEL=gpt-3.5-turbo
AI_TAG_GENERATION_ENABLED=0

# 静态资源
USE_MINIFIED_ASSETS=True
ASSET_BUILD_VERSION=1
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v2.3 (2026-06-28)
- 新增独立知识空间（`/knowledge`）：目录树 + 文档
- 新增 React 19 + Vite 8 + BlockNote 知识库编辑器
- 新增 Passkey / WebAuthn 快捷登录
- 新增 Safari 扩展
- 知识库与博客数据完全独立

### v2.2 (2026-03-13)
- 新增键盘快捷键系统
- 新增多设备草稿同步
- 新增图片自动优化
- 新增面包屑导航
- 新增静态资源自动版本管理

### v2.1 (2026-01-31)
- 新增知识库功能（卡片、时间线、孵化器）
- 新增浏览器扩展（网页内容采集）
- 新增 AI 辅助功能（标签生成、内容合并）
- 优化暗黑模式
- 改进用户体验（快速记事、草稿恢复）

### v2.0
- 富文本编辑器
- 多用户系统
- AI 标签生成
- 暗黑模式

### v1.0
- 基础博客功能
- 评论系统
- 全文搜索
