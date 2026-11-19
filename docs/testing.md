# 测试文档

## 📊 测试覆盖情况

### 现有测试文件

| 文件 | 描述 |
|------|------|
| `conftest.py` | pytest 配置、临时数据库与共享 fixtures |
| `schema_snapshot_utils.py` | schema 快照导出工具 |
| `test_admin_features.py` | 管理后台功能 |
| `test_ai_catalog.py` | AI 提供商与模型目录 |
| `test_ai_mentor_restructure.py` | AI 导师重构 |
| `test_ai_merger.py` | AI 卡片合并 |
| `test_ai_title_generation.py` | AI 标题生成（持久化任务队列） |
| `test_app_factory.py` | create_app 工厂与配置隔离 |
| `test_asset_versioning.py` | 模板静态资源版本化检查 |
| `test_backup.py` | 备份与恢复 |
| `test_db_check.py` | 数据库完整性检查 |
| `test_drafts.py` | 草稿同步 |
| `test_editor_content_formats.py` | 编辑器内容格式 |
| `test_embeddings.py` | Embedding / 语义搜索 |
| `test_image_cleanup_tool.py` | 图片清理工具 |
| `test_image_edge_cases.py` | 图片边界情况 |
| `test_image_processing.py` | 图片处理与优化 |
| `test_import_blog.py` | 博客导入 |
| `test_import_posts.py` | 文章导入 |
| `test_kb_editor_api.py` | 知识库编辑器后端 API（图片上传、自动保存、目录排序） |
| `test_knowledge_base.py` | 知识库 |
| `test_logging_setup.py` | 日志文件与测试隔离 |
| `test_markdown_renderer.py` | Markdown 渲染与 HTML 清洗 |
| `test_migrate_content_format.py` | 迁移 011（内容格式纠偏） |
| `test_migrations_runner.py` | 版本化迁移运行器 |
| `test_models.py` | 核心数据模型 |
| `test_models_edge_cases.py` | 模型边界情况 |
| `test_p0_hardening.py` | P0 安全/体验修复回归 |
| `test_p1_batch.py` | P1 批量修复回归 |
| `test_p1_features.py` | P1 功能（定时发布/软删除/修订等） |
| `test_pwa.py` | PWA / Service Worker / iOS 图标 / 卡片 API |
| `test_review.py` | 回顾页 / 每周回顾 |
| `test_routes.py` | 路由行为 |
| `test_routes_edge_cases.py` | 路由边界情况 |
| `test_schema_snapshot.py` | schema 快照与迁移一致性 |
| `test_search_api.py` | 搜索 API |
| `test_security.py` | 安全（CSRF、XSS、速率限制、CSP、Cookie） |
| `test_security_p0.py` | P0 安全修复回归 |
| `test_site_icon.py` | 站点图标 |
| `test_task_queue.py` | 持久化后台任务队列 |
| `test_timezone_utils.py` | 时区工具 |
| `e2e_kb_editor.py` | 知识库编辑器冒烟脚本（CDP + Chrome，手动运行） |
| `e2e/conftest.py` | 临时数据库 + 独立 Flask 服务 + Headless Chrome fixtures |
| `e2e/_server.py` | 独立测试服务启动辅助 |
| `e2e/harness.py` | CDP 封装（导航、填表、点击、fetch 断言） |
| `e2e/test_public_site.py` | 首页、文章详情、搜索、分类/标签/归档、公开 API |
| `e2e/test_auth.py` | 登录、登出、受保护页面跳转 |
| `e2e/test_admin_posts.py` | 文章创建/发布/编辑/草稿/下架/回收站恢复 |
| `e2e/test_comments.py` | 评论提交与后台审核 |
| `e2e/test_knowledge_base.py` | 知识库浏览/搜索、BlockNote 建文档、自动保存 |
| `e2e/test_personal_features.py` | 回顾页、统一搜索、快速笔记与卡片 API |
| `e2e/test_pwa_and_health.py` | 健康检查、manifest、Service Worker、404（共 26 个用例，默认跳过） |

**当前测试总数**: 527 个单元/集成测试，外加 26 个浏览器 E2E 用例；`pytest --collect-only -q` 共收集 **553** 个用例。

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

# 只跑单元测试 / 只跑集成（线程、异步等）
make test-unit
make test-integration

# 查看测试覆盖率（含 40% 门槛，报告在 htmlcov/）
make coverage

# 浏览器端到端测试（自动启动临时服务 + Headless Chrome，默认不在 make check 中运行）
make test-e2e
```

### 浏览器 E2E 测试

`tests/e2e/` 下的用例默认跳过，只有设置 `E2E=1` 时才会启动独立的 Flask 服务和 Headless Chrome：

```bash
E2E=1 pytest tests/e2e -v
E2E=1 pytest tests/e2e/test_admin_posts.py -v

# 未自动找到 Chrome 时显式指定
E2E_CHROME_BIN=/path/to/chrome E2E=1 pytest tests/e2e -v
```

覆盖范围：公开站点与搜索、登录/登出、后台文章创建/发布/编辑/草稿/下架/回收站恢复、评论提交与审核、知识库浏览/搜索/BlockNote 编辑器建文档/自动保存、回顾页与个人 API、PWA 与健康检查。

E2E 已在 CI 中通过 `E2E=1 pytest tests/e2e` 执行（需要 Chrome）；本地未设置 `E2E=1` 时会自动跳过。

### schema 快照

`tests/schema_snapshot.json` 记录 `init_db + 全部迁移` 后的表/索引结构，`tests/test_schema_snapshot.py` 会与之逐项比对。新增或修改迁移后必须重新生成，否则 CI 会失败：

```bash
.venv/bin/python scripts/generate_schema_snapshot.py
```

## 按类型运行

```bash
# 只运行单元测试（等价于 make test-unit）
pytest tests/ -v -m "not integration and not e2e"

# 只运行集成测试（线程、异步、持久化队列等；等价于 make test-integration）
pytest tests/ -q -m "integration and not e2e"

# 只运行浏览器 E2E（等价于 make test-e2e）
E2E=1 pytest tests/e2e -v

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
pip install -r requirements-dev.txt

# 检查pytest版本
pip list | grep pytest
```

## 📚 相关文档

- [pytest文档](https://docs.pytest.org/)
- [Flask测试文档](https://flask.palletsprojects.com/)
- [项目API文档](api-documentation.md)
