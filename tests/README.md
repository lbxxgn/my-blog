# Simple Blog 测试

本目录包含 Simple Blog 项目的测试套件。

## 测试结构

```
tests/
├── __init__.py                # 测试模块初始化
├── conftest.py                # pytest 配置和共享 fixtures
├── test_admin_features.py     # 管理后台功能
├── test_ai_merger.py          # AI 卡片合并
├── test_db_check.py           # 数据库完整性检查
├── test_drafts.py             # 草稿同步
├── test_image_cleanup_tool.py # 图片清理工具
├── test_image_edge_cases.py   # 图片边界情况
├── test_image_processing.py   # 图片处理与优化
├── test_import_blog.py        # 博客导入
├── test_import_posts.py       # 文章导入
├── test_kb_editor_api.py      # 知识库编辑器后端 API
├── test_knowledge_base.py     # 旧版知识库
├── test_migrate_db.py         # 数据库迁移
├── test_models.py             # 核心数据模型
├── test_models_edge_cases.py  # 模型边界情况
├── test_routes.py             # 路由行为
├── test_routes_edge_cases.py  # 路由边界情况
├── test_security.py           # 安全（CSRF、XSS、速率限制、CSP）
└── e2e_kb_editor.py           # 端到端知识库编辑器测试（CDP + Chrome）
```

当前共有 **271** 个 pytest 测试用例，外加一个独立的 E2E 脚本。

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
pytest --cov=backend --cov-report=html

# 或先跑项目默认快速检查
make check
```

覆盖率报告将生成在 `htmlcov/index.html`。

### 运行测试并显示详细输出

```bash
pytest -v
```

### E2E 测试

```bash
python tests/e2e_kb_editor.py
```

需要本地启动 Flask 服务，并安装 Chrome 浏览器。

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
- `test_category`: 测试分类
- `test_tag`: 测试标签

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

```yaml
# .github/workflows/test.yml 示例
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov=backend --cov-report=xml
```
