# Simple Blog 测试

本目录包含 Simple Blog 项目的测试套件。

## 测试结构

```
tests/
├── __init__.py           # 测试模块初始化
├── conftest.py           # pytest 配置和共享 fixtures
├── test_models.py        # 数据模型测试
└── test_routes.py        # 路由测试
```

## 运行测试

### 运行所有测试

```bash
pytest
```

### 运行特定测试文件

```bash
pytest tests/test_models.py
pytest tests/test_routes.py
```

### 运行特定测试类或函数

```bash
pytest tests/test_models.py::TestUserModels::test_create_user
```

### 生成覆盖率报告

```bash
pytest --cov=backend --cov-report=html
```

覆盖率报告将生成在 `htmlcov/index.html`

### 运行测试并显示详细输出

```bash
pytest -v
```

### 跳过慢速测试

```bash
pytest -m "not slow"
```

## 编写测试

### 测试文件命名

- 所有测试文件应以 `test_` 开头
- 测试类应以 `Test` 开头
- 测试函数应以 `test_` 开头

### 使用 Fixtures

```python
def test_something(temp_db, test_user):
    # temp_db: 临时数据库
    # test_user: 测试用户
    pass
```

### 可用的 Fixtures

- `temp_db`: 临时数据库（每个测试独立）
- `test_admin_user`: 测试管理员用户
- `test_user`: 测试普通用户
- `test_post`: 测试文章
- `client`: Flask 测试客户端

## 测试覆盖

当前测试覆盖：

- ✅ 用户模型（创建、查询、更新、删除）
- ✅ 文章模型（创建、查询、更新、删除）
- ✅ 分类模型（创建、查询、更新、删除）
- ✅ 标签模型（创建、查询）
- ✅ 评论模型（创建、查询）
- ✅ 认证路由（登录、登出）
- ✅ 博客路由（首页、文章详情、搜索）
- ✅ 管理后台路由（仪表板、新建文章）
- ✅ API路由（文章列表、分页）

## 持续集成

测试可以集成到 CI/CD 流程中：

```yaml
# .github/workflows/test.yml 示例
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov=backend --cov-report=xml
```
