# 测试文档

## 📊 测试覆盖情况

### 现有测试文件

| 文件 | 描述 |
|------|------|
| `conftest.py` | pytest 配置和共享 fixtures |
| `test_admin_features.py` | 管理后台功能 |
| `test_ai_merger.py` | AI 卡片合并 |
| `test_db_check.py` | 数据库完整性检查 |
| `test_drafts.py` | 草稿同步 |
| `test_image_cleanup_tool.py` | 图片清理工具 |
| `test_image_edge_cases.py` | 图片边界情况 |
| `test_image_processing.py` | 图片处理与优化 |
| `test_import_blog.py` | 博客导入 |
| `test_import_posts.py` | 文章导入 |
| `test_kb_editor_api.py` | 知识库编辑器后端 API（图片上传、自动保存、目录排序） |
| `test_knowledge_base.py` | 旧版知识库 |
| `test_migrate_db.py` | 数据库迁移 |
| `test_models.py` | 核心数据模型 |
| `test_models_edge_cases.py` | 模型边界情况 |
| `test_routes.py` | 路由行为 |
| `test_routes_edge_cases.py` | 路由边界情况 |
| `test_security.py` | 安全（CSRF、XSS、速率限制、CSP、Cookie） |
| `e2e_kb_editor.py` | 端到端知识库编辑器测试（CDP + Chrome） |

**当前测试总数**: 271 个单元/集成测试（运行 `pytest` 统计），外加 1 个 E2E 脚本。

### 已覆盖的功能模块

#### ✅ 核心功能
- 用户认证（登录、登出、密码修改）
- 文章管理（CRUD、发布、编辑、删除）
- 分类和标签管理
- 评论系统
- 全文搜索

#### ✅ 新增功能测试
- **草稿同步** - 多设备自动保存、冲突检测
- **知识库** - 卡片管理、目录树、文档 CRUD、拖拽排序、编辑器 API
- **浏览器扩展API** - 卡片提交、标注同步
- **AI辅助** - 标签生成、智能合并、内容续写、整理建议
- **图片优化** - 多尺寸生成、WebP 转换、HEIC 支持、清理工具
- **批量操作** - 批量更新分类、删除、发布、添加标签
- **导入导出** - JSON/Markdown 格式
- **用户管理** - CRUD、角色管理
- **Passkey / WebAuthn** - 注册、认证
- **安全** - CSRF、XSS、速率限制、CSP

## 🚀 运行测试

### 基础命令

```bash
# 运行所有测试
make test

# 运行特定测试文件
pytest tests/test_drafts.py -v
pytest tests/test_knowledge_base.py -v
pytest tests/test_admin_features.py -v

# 运行关键快速检查
make check

# 查看测试覆盖率
pytest --cov=backend --cov-report=html
pytest --cov=backend --cov-report=term-missing
```

### 按类型运行

```bash
# 只运行单元测试
pytest tests/ -v -m "not integration"

# 只运行集成测试
pytest tests/ -v -m integration

# 排除慢速测试
pytest tests/ -v -m "not slow"

# 只运行图片相关测试
pytest tests/ -v -k "image"
```

### 详细输出

```bash
# 显示详细输出
pytest tests/ -v -s

# 显示测试的打印输出
pytest tests/ -v -s --capture=no

# 显示最慢的10个测试
pytest tests/ --durations=10
```

## 📝 测试组织

### Pytest Marks

```python
@pytest.mark.unit          # 单元测试
@pytest.mark.integration    # 集成测试
@pytest.mark.slow          # 慢速测试
```

### Fixtures

**测试客户端与认证**:
- `client` - Flask 测试客户端
- `csrf_client` - 已注入 CSRF token 的测试客户端
- `limited_client` - 用于测试速率限制的客户端
- `test_admin_user` - 管理员用户
- `test_user` - 普通用户

**数据库与数据**:
- `init_database` / `temp_db` - 临时数据库
- `test_post` - 测试文章
- `test_category` - 测试分类
- `test_tag` - 测试标签

## 🎯 测试最佳实践

1. **隔离性**: 每个测试独立运行，不依赖其他测试
2. **可重复性**: 测试结果应该可重复
3. **快速性**: 单元测试应该快速运行
4. **清晰性**: 测试名称清晰描述测试内容

## 📈 覆盖率目标

- **总体覆盖率**: 目标 80%+
- **核心模块**: 目标 90%+
- **新增功能**: 目标 85%+

## 🔧 故障排查

### 测试失败时

```bash
# 查看详细错误
pytest tests/ -v --tb=long

# 只运行失败的测试
pytest tests/ --lf

# 进入调试模式
pytest tests/ --pdb
```

### 数据库问题

```bash
# 清理测试数据库
rm -f tests/*.db

# 重新初始化
python -c "from backend.app import app; from backend.models import init_db; init_db()"
```

### 依赖问题

```bash
# 重新安装测试依赖
pip install -r requirements.txt

# 检查pytest版本
pip list | grep pytest
```

## 📚 相关文档

- [pytest文档](https://docs.pytest.org/)
- [Flask测试文档](https://flask.palletsprojects.com/)
- [项目API文档](api-documentation.md)
