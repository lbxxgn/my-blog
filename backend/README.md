# Backend 工具文档

`backend/` 目录包含 Simple Blog 的后端代码与若干运维工具。

## 模块概览

| 文件/目录 | 说明 |
|----------|------|
| `app.py` | Flask 应用入口，蓝图注册、安全中间件、Vite 清单读取 |
| `config.py` | 统一的配置入口（路径、安全、数据库、上传、AI、Passkey 等） |
| `auth_decorators.py` | `login_required`、`can_manage_users` 等装饰器 |
| `logger.py` | 结构化日志与操作/错误/登录日志记录 |
| `models/` | 数据模型与数据库操作 |
| `routes/` | Flask 蓝图路由 |
| `ai_services/` | AI 提供商适配器与标签/卡片合并服务 |
| `utils/` | 工具函数（静态资源版本、图片处理、模板助手等） |
| `tasks/` | 后台异步任务（图片优化） |
| `migrations/` | 数据库迁移脚本 |
| `image_cleanup_tool.py` | 统一的图片清理工具 |
| `db_check.py` | 数据库完整性检查 |
| `migrate_db.py` | 统一数据库迁移入口 |
| `export.py` | 数据导出（JSON/Markdown） |
| `import_blog.py` | 博客导入 |
| `import_posts.py` | 文章导入 |

## 图片清理工具

整合了多个独立脚本的功能，用于检查和清理失效的本地/外部图片引用。

### 使用方法

```bash
# 检查本地图片（快速，默认试运行）
python backend/image_cleanup_tool.py local --dry-run

# 完整检查（包括外部 URL）
python backend/image_cleanup_tool.py all --check-external --dry-run

# 快速清理已知失效域名
python backend/image_cleanup_tool.py fast-clean

# 检查外部图片可访问性
python backend/image_cleanup_tool.py check-external

# 执行实际清理（不试运行）
python backend/image_cleanup_tool.py local --force
```

### 参数说明

- `--dry-run`: 试运行模式（默认），不实际修改数据库
- `--force`: 执行实际修改
- `--check-external`: 检查外部 URL（仅 `all` 模式有效）
- `--no-progress`: 不显示进度条

## 数据库管理

### 初始化数据库

```bash
python -c "from backend.app import app; from backend.models import init_db; init_db()"
```

### 运行完整性检查

```bash
python backend/db_check.py
```

### 运行迁移脚本

```bash
python backend/migrations/migrate_drafts.py
python backend/migrations/migrate_image_optimization.py
python backend/migrations/migrate_knowledge_base.py
# ... 其他迁移脚本见 backend/migrations/
```

或使用统一入口：

```bash
python backend/migrate_db.py
```

## 配置说明

所有配置项在 `backend/config.py` 中：

- 数据库路径
- 上传文件夹
- 安全配置（密码、会话、CSRF、Passkey）
- AI 配置
- 静态资源优化配置

完整环境变量请参考项目根目录的 `.env.example`。

## 相关文档

- [完整 API 文档](../docs/api-documentation.md)
- [架构说明](../docs/ARCHITECTURE.md)
- [快速启动指南](../QUICKSTART.md)
- [部署指南](../DEPLOYMENT.md)

## 注意事项

⚠️ **重要提示**：

1. 运行清理工具前会自动备份数据库
2. 建议先使用 `--dry-run` 模式查看清理计划
3. 确认无误后使用 `--force` 执行实际清理
4. 备份文件保存在 `backups/` 目录（而非 `db/backups/`）
