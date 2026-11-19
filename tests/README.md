# Simple Blog 测试

本目录包含 Simple Blog 项目的测试套件。

## 测试结构

```
tests/
├── __init__.py                    # 测试模块初始化
├── conftest.py                    # pytest 配置、临时数据库与共享 fixtures
├── schema_snapshot_utils.py       # schema 快照导出工具
├── e2e_kb_editor.py               # 知识库编辑器冒烟脚本（CDP + Chrome，手动运行）
├── test_admin_features.py         # 管理后台功能
├── test_ai_catalog.py             # AI 提供商与模型目录
├── test_ai_mentor_restructure.py  # AI 导师重构
├── test_ai_merger.py              # AI 卡片合并
├── test_ai_title_generation.py    # AI 标题生成（持久化任务队列）
├── test_app_factory.py            # create_app 工厂与配置隔离
├── test_asset_versioning.py       # 模板静态资源版本化检查
├── test_backup.py                 # 备份与恢复
├── test_db_check.py               # 数据库完整性检查
├── test_drafts.py                 # 草稿同步
├── test_editor_content_formats.py # 编辑器内容格式
├── test_embeddings.py             # Embedding / 语义搜索
├── test_image_cleanup_tool.py     # 图片清理工具
├── test_image_edge_cases.py       # 图片边界情况
├── test_image_processing.py       # 图片处理与优化
├── test_import_blog.py            # 博客导入
├── test_import_posts.py           # 文章导入
├── test_kb_editor_api.py          # 知识库编辑器后端 API
├── test_knowledge_base.py         # 知识库
├── test_logging_setup.py          # 日志文件与隔离
├── test_markdown_renderer.py      # Markdown 渲染与 HTML 清洗
├── test_migrate_content_format.py # 迁移 011（内容格式纠偏）
├── test_migrations_runner.py      # 版本化迁移运行器
├── test_models.py                 # 核心数据模型
├── test_models_edge_cases.py      # 模型边界情况
├── test_p0_hardening.py           # P0 安全/体验修复回归
├── test_p1_batch.py               # P1 批量修复回归
├── test_p1_features.py            # P1 功能（定时发布/软删除/修订等）
├── test_pwa.py                    # PWA / Service Worker / 卡片 API
├── test_review.py                 # 回顾页 / 每周回顾
├── test_routes.py                 # 路由行为
├── test_routes_edge_cases.py      # 路由边界情况
├── test_schema_snapshot.py        # schema 快照与迁移一致性
├── test_search_api.py             # 搜索 API
├── test_security.py               # 安全（CSRF、XSS、速率限制、CSP）
├── test_security_p0.py            # P0 安全修复回归
├── test_site_icon.py              # 站点图标
├── test_task_queue.py             # 持久化后台任务队列
├── test_timezone_utils.py         # 时区工具
└── e2e/                           # 浏览器端到端测试（pytest，opt-in）
    ├── __init__.py
    ├── conftest.py                # 临时数据库 + 独立 Flask 服务 + Headless Chrome fixtures
    ├── _server.py                 # 独立测试服务启动辅助
    ├── harness.py                 # CDP 封装（导航、填表、点击、fetch 断言）
    ├── test_public_site.py        # 首页、文章详情、搜索、分类/标签/归档、公开 API
    ├── test_auth.py               # 登录、登出、受保护页面跳转
    ├── test_admin_posts.py        # 文章创建/发布/编辑/草稿/下架/回收站恢复
    ├── test_comments.py           # 评论提交与后台审核
    ├── test_knowledge_base.py     # 知识库浏览/搜索、BlockNote 建文档、自动保存
    ├── test_personal_features.py  # 回顾页、统一搜索、快速笔记与卡片 API
    └── test_pwa_and_health.py     # 健康检查、manifest、Service Worker、404
```

当前共有 **527** 个单元/集成测试，外加 **26** 个浏览器 E2E 用例（默认跳过，需 `E2E=1` 开启）：
`pytest --collect-only -q` 共收集 **553** 个用例。

## 运行测试

### 运行所有测试

```bash
make test
# 或
pytest -q
```

### 运行特定测试文件

```bash
pytest tests/test_models.py
pytest tests/test_kb_editor_api.py
pytest tests/test_security.py
```

### 运行特定测试类或函数

```bash
pytest tests/test_models.py::TestUserModels::test_create_user
```

### 生成覆盖率报告

```bash
# 带 40% 覆盖率门槛，报告生成在 htmlcov/index.html
make coverage

# 日常快速检查（lint + 全部测试，不生成覆盖率）
make check
```

### 运行测试并显示详细输出

```bash
pytest -v
```

### E2E 测试

浏览器 E2E 测试默认跳过，不会影响 `make test` / `make check`。它们会自动启动一个使用临时数据库的 Flask 服务和 Headless Chrome：

```bash
# 推荐：通过 make 运行
make test-e2e

# 或直接运行
E2E=1 pytest tests/e2e -v

# 指定 Chrome/Chromium 路径（未自动找到时）
E2E_CHROME_BIN=/path/to/chrome E2E=1 pytest tests/e2e -v
```

测试覆盖：公开站点浏览/搜索、登录登出、后台文章全生命周期（创建/发布/编辑/草稿/下架/删除恢复）、评论提交与审核、知识库浏览/搜索/BlockNote 编辑器建文档/自动保存、回顾页与个人 API、PWA 与健康检查。

知识库编辑器的完整冒烟脚本（含图片上传与 AI 面板）仍可单独运行，需要先启动本地 Flask 服务：

```bash
python tests/e2e_kb_editor.py
```

## 编写测试

### 测试文件命名

- 所有测试文件应以 `test_` 开头
- 测试类应以 `Test` 开头
- 测试函数应以 `test_` 开头

### 使用 Fixtures

```python
def test_something(client, test_admin_user):
    # client: Flask 测试客户端
    # test_admin_user: 测试管理员用户
    pass
```

### 可用的 Fixtures

- `client`: Flask 测试客户端
- `csrf_client`: 已注入 CSRF token 的测试客户端
- `limited_client`: 用于测试速率限制的客户端
- `test_admin_user`: 测试管理员用户
- `test_user`: 测试普通用户
- `temp_db` / `init_database`: 临时数据库
- `test_post`: 测试文章

### schema 快照

`tests/schema_snapshot.json` 记录 `init_db + 全部迁移` 后的表/索引结构，`test_schema_snapshot.py` 会在 CI 中比对。
新增或修改迁移后需重新生成：

```bash
.venv/bin/python scripts/generate_schema_snapshot.py
```

## 测试覆盖

- ✅ 用户认证与授权（登录、登出、Passkey、角色）
- ✅ 文章与知识库文档 CRUD
- ✅ 分类、标签、评论
- ✅ 全文搜索
- ✅ 草稿同步
- ✅ 图片上传、优化、清理
- ✅ 导入导出
- ✅ AI 辅助功能
- ✅ 浏览器扩展 API
- ✅ 安全（CSRF、XSS、速率限制、CSP、Cookie）

更完整的测试运行说明见 [docs/testing.md](../docs/testing.md)。

## 持续集成

测试可以集成到 CI/CD 流程中：

实际 CI 配置见 [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)：backend job 运行 `make check`，frontend job 运行 `npm ci && npm run build` 并校验构建产物，e2e job 安装 Chrome 后运行 `E2E=1 pytest tests/e2e`，另有依赖审计 job。
