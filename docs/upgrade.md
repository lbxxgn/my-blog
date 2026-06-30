# Simple Blog 升级指南

## 📋 概述

本指南说明如何从旧版本升级 Simple Blog 到当前实现版本。当前版本包含以下主要能力：

1. **多角色访问控制** - admin/editor/author 权限体系
2. **文章类型与分类** - 支持 post/knowledge 等类型
3. **AI 功能增强** - 标签、摘要、推荐、续写
4. **草稿服务器同步** - 防止数据丢失，支持多设备编辑
5. **图片自动压缩优化** - 自动生成多尺寸图片，提升加载速度
6. **静态资源自动版本化** - 解决浏览器缓存问题
7. **知识库编辑器** - 基于 React + Vite 的现代化编辑器
8. **Passkey / WebAuthn 登录** - 无密码认证支持

---

## 🚀 快速开始

### 方法一：自动升级（推荐）

```bash
# 1. 赋予执行权限
chmod +x scripts/upgrade.sh scripts/verify_upgrade.sh scripts/rollback.sh

# 2. 执行升级
./scripts/upgrade.sh

# 3. 验证升级结果
./scripts/verify_upgrade.sh
```

### 方法二：手动升级

如果自动升级失败，可以按照以下步骤手动升级：

```bash
# 1. 备份数据库和配置
BACKUP_DIR="backups/upgrade_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp db/simple_blog.db "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"

# 2. 拉取最新代码
git fetch origin
git pull origin main

# 3. 激活虚拟环境
source .venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 运行数据库迁移
export DATABASE_URL="sqlite:///db/simple_blog.db"
python3 backend/migrations/migrate_add_access_control.py
python3 backend/migrations/migrate_add_post_type.py
python3 backend/migrations/migrate_ai_features.py
python3 backend/migrations/migrate_drafts.py
python3 backend/migrations/migrate_image_optimization.py
python3 backend/migrations/migrate_knowledge_base.py
python3 backend/migrations/migrate_multiauthor.py

# 6. 构建知识库编辑器前端（需要 Node.js 18+）
cd frontend && npm install && npm run build && cd ..

# 7. 生成静态资源 manifest
python3 scripts/generate_manifest.py

# 8. 重启应用
sudo systemctl restart simple-blog
# 或直接启动
# nohup python3 backend/app.py > logs/app.log 2>&1 &

# 9. 验证
./scripts/verify_upgrade.sh
```

---

## 📦 新增与变更文件清单

### 后端文件
```
backend/
├── models/
│   ├── draft.py                    # 草稿数据模型
│   ├── post_type.py                # 文章类型扩展
│   ├── user.py                     # 用户与角色
│   └── knowledge_base.py           # 知识库模型
├── routes/
│   ├── drafts.py                   # 草稿 API 路由
│   ├── ai.py                       # AI 功能路由
│   ├── auth.py                     # 认证与 Passkey
│   └── knowledge.py                # 知识库路由
├── tasks/
│   └── image_optimization_task.py  # 图片优化任务队列
├── utils/
│   ├── asset_version.py            # 资源版本管理器
│   └── template_helpers.py         # 模板助手函数
└── migrations/
    ├── migrate_add_access_control.py
    ├── migrate_add_post_type.py
    ├── migrate_ai_features.py
    ├── migrate_drafts.py
    ├── migrate_image_optimization.py
    ├── migrate_knowledge_base.py
    └── migrate_multiauthor.py
```

### 前端文件
```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
└── src/                            # React 知识库编辑器源码

static/frontend/                    # Vite 构建产物
```

### 根目录脚本
```
scripts/
├── start.sh
├── install-service.sh
├── upgrade.sh
├── rollback.sh
├── verify_upgrade.sh
└── generate_manifest.py
```

---

## 🗄️ 数据库变更

当前版本涉及的数据库迁移脚本位于 `backend/migrations/`：

| 迁移脚本 | 作用 |
| --- | --- |
| `migrate_add_access_control.py` | 添加角色与权限字段 |
| `migrate_add_post_type.py` | 添加文章类型字段 |
| `migrate_ai_features.py` | 添加 AI 使用记录等表 |
| `migrate_drafts.py` | 创建 `drafts` 表 |
| `migrate_image_optimization.py` | 创建 `optimized_images` 表 |
| `migrate_knowledge_base.py` | 创建知识库相关表 |
| `migrate_multiauthor.py` | 多作者关联字段 |

升级脚本会根据需要自动运行相关迁移。手动升级时，请按上表顺序运行。

### 主要新增表

#### 1. drafts（草稿表）
```sql
CREATE TABLE drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_id INTEGER,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category_id INTEGER,
    tags TEXT,
    device_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    error_message TEXT,
    UNIQUE(user_id, post_id)
);
```

**索引：**
- `idx_drafts_user_post` ON (user_id, post_id)
- `idx_drafts_updated_at` ON (updated_at DESC)

#### 2. optimized_images（图片优化表）
```sql
CREATE TABLE optimized_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path TEXT NOT NULL UNIQUE,
    thumbnail_path TEXT,
    medium_path TEXT,
    large_path TEXT,
    original_size INTEGER,
    optimized_size INTEGER,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

---

## ⚙️ 配置变更

如需自定义，可修改 `.env` 文件：

```bash
# 图片优化线程数（默认：4）
export IMAGE_OPTIMIZATION_WORKERS=4

# 草稿自动保存间隔（默认：30秒）
export DRAFT_AUTO_SAVE_INTERVAL=30

# Passkey / WebAuthn
PASSKEY_RP_NAME=Simple Blog
PASSKEY_RP_ID=your-domain.com
PASSKEY_ALLOWED_ORIGINS=https://your-domain.com

# 设备记住时长（天）
REMEMBER_DEVICE_DAYS=90

# 静态资源
USE_MINIFIED_ASSETS=True
# ASSET_BUILD_VERSION=

# AI 默认配置
AI_DEFAULT_PROVIDER=openai
AI_DEFAULT_MODEL=gpt-3.5-turbo
AI_RATE_LIMIT_PER_HOUR=10
AI_CONTENT_MAX_LENGTH=500
```

完整环境变量请参见 `.env.example`。

---

## 🧪 功能验证

### 自动验证
```bash
./scripts/verify_upgrade.sh
```

### 手动验证步骤

#### 1. 键盘快捷键 ✅
- [ ] 访问首页按 `Ctrl+N` 跳转到新建文章
- [ ] 在编辑器按 `ESC` 看到关闭确认
- [ ] 看到快捷键提示浮层

#### 2. 面包屑导航 ✅
- [ ] 访问文章页面
- [ ] 看到：`首页 > 分类 > 文章标题`
- [ ] 点击面包屑能跳转

#### 3. 草稿自动保存 ✅
- [ ] 登录系统
- [ ] 编辑文章，等待 30 秒
- [ ] 查看浏览器控制台有保存日志
- [ ] 刷新页面，内容未丢失

#### 4. 图片优化 ✅
- [ ] 上传一张图片
- [ ] 检查 `static/uploads/optimized/` 目录
- [ ] 看到三个尺寸：thumbnail/medium/large

#### 5. 静态资源版本化 ✅
- [ ] 查看页面源代码
- [ ] CSS/JS 链接带 `?v=hash` 参数
- [ ] 修改 CSS 后 hash 值变化

#### 6. 知识库编辑器 ✅
- [ ] 访问 http://localhost:5001/knowledge/edit
- [ ] 确认 `/static/frontend/` 下的 JS/CSS 资源加载正常
- [ ] 编辑器可正常创建和编辑知识库条目

#### 7. Passkey 登录 ✅
- [ ] 登录后进入账户设置
- [ ] 可注册 Passkey
- [ ] 登出后可使用 Passkey 登录

---

## 🔄 回滚方法

如果升级后遇到问题，可以使用回滚脚本：

```bash
# 查看可用的备份
ls -lt backups/upgrade_*

# 回滚到指定备份
./scripts/rollback.sh backups/upgrade_20260314_105500
```

### 手动回滚步骤

```bash
# 1. 停止应用
sudo systemctl stop simple-blog
# 或
lsof -ti:5001 | xargs kill -9 2>/dev/null || true

# 2. 恢复数据库
cp backups/upgrade_YYYYMMDD_HHMMSS/simple_blog.db db/simple_blog.db

# 3. 删除新增的数据库表（如需完全回滚）
sqlite3 db/simple_blog.db <<EOF
DROP TABLE IF EXISTS drafts;
DROP TABLE IF EXISTS optimized_images;
DROP TABLE IF EXISTS knowledge_nodes;
DROP TABLE IF EXISTS knowledge_edges;
DROP TABLE IF EXISTS ai_usage_records;
EOF

# 4. 回退代码（如需要）
git log --oneline -10
git reset --hard <old-commit-hash>

# 5. 重启应用
sudo systemctl start simple-blog
```

---

## 🐛 常见问题

### 1. 升级脚本执行失败

**问题：** 权限错误或命令找不到
**解决：**
```bash
# 确保脚本有执行权限
chmod +x scripts/upgrade.sh scripts/verify_upgrade.sh scripts/rollback.sh

# 检查 Python 和 pip 是否可用
python3 --version
source .venv/bin/activate
pip --version
```

### 2. 应用启动失败

**问题：** Flask 应用无法启动
**解决：**
```bash
# 查看错误日志
tail -50 logs/error.log
tail -50 logs/app.log

# 常见原因：
# - 端口被占用：lsof -ti:5001 | xargs kill -9
# - 依赖缺失：pip install -r requirements.txt
# - 数据库错误：export DATABASE_URL="sqlite:///db/simple_blog.db"
# - 前端未构建：cd frontend && npm install && npm run build
```

### 3. 静态资源 404

**问题：** CSS/JS 文件无法加载
**解决：**
```bash
# 重新生成 manifest
python3 scripts/generate_manifest.py

# 重新构建前端（知识库编辑器）
cd frontend && npm install && npm run build && cd ..

# 检查文件权限
chmod -R 755 static/

# 重启应用
sudo systemctl restart simple-blog
```

### 4. 数据库迁移失败

**问题：** 表创建失败
**解决：**
```bash
# 检查数据库文件权限
ls -la db/simple_blog.db

# 手动运行迁移
source .venv/bin/activate
export DATABASE_URL="sqlite:///db/simple_blog.db"
python3 backend/migrations/migrate_drafts.py
python3 backend/migrations/migrate_knowledge_base.py

# 检查表是否创建
sqlite3 db/simple_blog.db ".tables"
```

### 5. 草稿保存失败

**问题：** 自动保存不工作
**解决：**
```bash
# 检查是否登录
# 草稿功能需要登录后才能使用

# 检查浏览器控制台
# 应该看到保存请求日志

# 检查 API 端点
curl -X POST http://127.0.0.1:5001/api/drafts \
  -H "Content-Type: application/json" \
  -d '{"title":"test"}'
# 应该返回 401 未授权（需要登录）或成功
```

### 6. 知识库编辑器空白或报错

**问题：** 访问 `/knowledge/edit` 页面空白
**解决：**
```bash
# 确认已构建前端
cd frontend && npm install && npm run build && cd ..

# 确认 static/frontend/ 目录存在且 Nginx 已配置
ls -la static/frontend/

# 查看错误日志
tail -f logs/error.log
```

---

## 📊 性能影响

### 图片优化
- **CPU 使用：** 后台线程池（4 个 worker）
- **存储空间：** 约 2-3 倍原图大小
- **优化效果：** WebP 格式减少 30-50% 文件大小

### 草稿同步
- **数据库：** 每次编辑写入一次（30 秒间隔）
- **网络流量：** 每次约 1-5KB
- **影响：** 几乎无影响

### 静态资源版本化
- **首次加载：** 需读取 manifest.json（~5KB）
- **后续请求：** 无额外开销
- **缓存效果：** 显著改善

### 知识库编辑器
- **构建产物：** 输出到 `static/frontend/`
- **Nginx 配置：** 需要直接服务 `/static/frontend/` 目录
- **首次加载：** 需下载 React 运行时与编辑器资源
- **缓存策略：** 哈希文件名可长期缓存

---

## 📝 更新日志

### v3.0.0 - 当前版本

#### 新增功能
- ✨ 多角色访问控制（admin/editor/author）
- ✨ 文章类型扩展（post/knowledge）
- ✨ AI 标签、摘要、推荐、续写
- ✨ 草稿服务器自动同步
- ✨ 图片自动压缩优化（3 尺寸 + WebP）
- ✨ 静态资源自动版本化
- ✨ 知识库编辑器（React + Vite）
- ✨ Passkey / WebAuthn 无密码登录

#### 技术改进
- 🔧 Python 3.11+ 推荐
- 🔧 密码最小长度强制 10 位
- 🔧 统一脚本入口 `scripts/`
- 🔧 数据库迁移脚本标准化
- 🔧 Vite 前端构建集成

#### 安全性
- 🔒 Passkey 认证支持
- 🔒 设备记住时长配置
- 🔒 草稿 API 需要认证
- 🔒 CSRF 保护已启用
- 🔒 输入验证和清理

---

## 🆘 获取帮助

如果遇到问题：

1. **查看日志**
   ```bash
   tail -f logs/app.log
   tail -f logs/error.log
   tail -f logs/login.log
   tail -f logs/operation.log
   tail -f logs/sql.log
   ```

2. **运行验证脚本**
   ```bash
   ./scripts/verify_upgrade.sh
   ```

3. **检查文档**
   - README.md - 项目总体说明
   - docs/ - 详细技术文档
   - QUICKSTART.md - 快速启动指南
   - DEPLOYMENT.md - 部署指南

4. **回滚**
   ```bash
   ./scripts/rollback.sh backups/upgrade_<timestamp>
   ```

---

## ✅ 升级前检查清单

在运行升级脚本前，请确认：

- [ ] 已备份重要数据
- [ ] 有足够的磁盘空间（至少 1GB）
- [ ] Python 3.11+ 已安装
- [ ] Node.js 18+ 已安装（构建知识库编辑器）
- [ ] 有 sudo/root 权限（如果需要）
- [ ] 了解回滚方法
- [ ] 已通知用户（如果是生产环境）

---

## 🎉 升级后

升级成功后，您可以：

1. 享受更快的编辑体验（键盘快捷键）
2. 更好的导航体验（面包屑）
3. 不再担心数据丢失（自动保存）
4. 更快的图片加载（自动优化）
5. 解决浏览器缓存问题（资源版本化）
6. 使用现代化知识库编辑器
7. 使用 Passkey 安全登录

祝您使用愉快！🚀
