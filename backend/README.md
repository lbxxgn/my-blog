# Backend 工具文档

## 图片清理工具

统一的图片清理工具，整合了之前多个独立脚本的功能。

### 使用方法

```bash
# 检查本地图片（快速）
python backend/image_cleanup_tool.py local --dry-run

# 完整检查（包括外部URL）
python backend/image_cleanup_tool.py all --check-external --dry-run

# 快速清理已知失效域名
python backend/image_cleanup_tool.py fast-clean

# 检查外部图片可访问性
python backend/image_cleanup_tool.py check-external

# 执行实际清理（不试运行）
python backend/image_cleanup_tool.py local --force
```

### 功能说明

- **local**: 只检查本地图片文件，不检查外部URL
- **all**: 完整检查，包括本地和外部图片
- **fast-clean**: 快速清理已知失效域名（126.net, blog.163.com）
- **check-external**: 检查所有外部图片URL的可访问性

### 参数说明

- `--dry-run`: 试运行模式（默认），不实际修改数据库
- `--force`: 执行实际修改
- `--check-external`: 检查外部URL（仅all模式有效）
- `--no-progress`: 不显示进度条

## 数据库管理

### 初始化数据库

```bash
cd backend
python -c "from app import app; from models import init_db; init_db()"
```

### 检查数据库完整性

```bash
python backend/db_check.py
```

## 配置说明

所有配置项在 `backend/config.py` 中：

- 数据库路径
- 上传文件夹
- 安全配置
- 环境变量

## 相关文档

- [完整API文档](../docs/api-documentation.md)
- [快速启动指南](../QUICKSTART.md)
- [部署指南](../docs/deployment/)

## 注意事项

⚠️ **重要提示**：

1. 运行清理工具前会自动备份数据库
2. 建议先使用 `--dry-run` 模式查看清理计划
3. 确认无误后使用 `--force` 执行实际清理
4. 备份文件保存在 `db/backups/` 目录
