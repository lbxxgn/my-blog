# 知识库重构说明

从 v2.3 开始，项目引入了独立的**知识空间**（`/knowledge`），与旧的**知识卡片收集**（`/knowledge_base`）并存。

## 两个模块的区别

| 特性 | `/knowledge_base`（旧） | `/knowledge`（新） |
|------|------------------------|-------------------|
| 定位 | 灵感卡片、快速记事、时间线 | 独立知识空间，目录树 + 文档 |
| 数据组织 | 卡片、状态、标签、时间线 | 树形目录 + 富文本文档 |
| 编辑器 | 传统表单/Quill | React + BlockNote |
| 与博客关系 | 可孵化成文章 | 完全独立，不与博客混用 |

## 技术实现

- 后端蓝图：`backend/routes/knowledge.py`（`knowledge_bp`，前缀 `/knowledge`）
- 编辑器源码：`frontend/src/`
- 编辑器构建产物：`static/frontend/`
- 模板入口：`templates/knowledge/`

## 使用前准备

新版编辑器需要构建前端资源：

```bash
cd frontend && npm install && npm run build && cd ..
```

## 测试

```bash
# API 测试
pytest tests/test_kb_editor_api.py -v

# E2E 测试
pytest tests/e2e_kb_editor.py -v
```

## 迁移说明

- 旧版 `/knowledge_base` 数据保留，功能不变
- 新版 `/knowledge` 使用独立的数据表，不与旧卡片数据冲突
- 如需将旧卡片迁移到新知识空间，请手动导出后再导入
