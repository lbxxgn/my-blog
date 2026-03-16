# 测试文档

## 📊 测试覆盖情况

### 现有测试文件（7个）

| 文件 | 描述 | 测试数量 |
|------|------|----------|
| conftest.py | pytest配置和fixture | - |
| test_ai_merger.py | AI卡片合并测试 | ~10 |
| test_image_processing.py | 图片处理测试 | ~40 |
| test_models.py | 数据模型测试 | ~50 |
| test_routes.py | 路由测试 | ~60 |
| test_drafts.py | 草稿同步测试 | ~40 |
| test_knowledge_base.py | 知识库测试 | ~35 |
| test_admin_features.py | 管理功能测试 | ~45 |

**总计**: 约280个测试用例

### 已覆盖的功能模块

#### ✅ 核心功能
- 用户认证（登录、登出、密码修改）
- 文章管理（CRUD、发布、编辑、删除）
- 分类和标签管理
- 评论系统
- 全文搜索

#### ✅ 新增功能测试
- **草稿同步** - 多设备自动保存、冲突检测
- **知识库** - 卡片管理、时间线、孵化器
- **浏览器扩展API** - 卡片提交、标注同步
- **AI辅助** - 标签生成、智能合并、内容续写
- **图片优化** - 多尺寸生成、WebP转换、HEIC支持
- **批量操作** - 批量更新分类、删除、发布、添加标签
- **导入导出** - JSON/Markdown格式
- **用户管理** - CRUD、角色管理

## 🚀 运行测试

### 基础命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_drafts.py -v
pytest tests/test_knowledge_base.py -v
pytest tests/test_admin_features.py -v

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

**测试客户端**:
- `client` - Flask测试客户端
- `test_admin_user` - 管理员用户
- `test_user` - 普通用户

**测试数据**:
- `temp_db` - 临时数据库
- `test_post` - 测试文章
- `test_category` - 测试分类

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
