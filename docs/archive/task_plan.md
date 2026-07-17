# Task Plan: 知识库编辑器升级设计与实现

## Goal
重新设计并实现一个对标主流知识库产品的现代化知识库文档编辑器，替代当前基于 Toast UI Editor 的基础 Markdown 编辑器，提升编辑体验、协作能力和知识组织效率。

## Current Phase
Phase 1

## Phases

### Phase 1: 现状分析与竞品调研
- [x] 理解用户意图：知识库刚重建，编辑器体验差，需要重新设计
- [x] 阅读当前知识库编辑器代码（templates/admin/knowledge_editor.html, static/css/knowledge.css, backend/routes/knowledge_base.py）
- [x] 调研主流知识库产品的编辑器特性（Notion、飞书、语雀、Obsidian、Outline、GitBook 等）
- [x] 总结竞品编辑器的核心能力、交互模式与优缺点
- [x] 记录 findings.md
- **Status:** complete

### Phase 2: 需求定义与方案设计
- [x] 定义新编辑器的功能范围（MVP vs 未来扩展）
- [x] 确定技术选型：Editor.js + 自定义 Markdown 转换层
- [x] 设计编辑器交互原型与关键页面结构
- [x] 确定数据模型兼容性（保留 Markdown 存储格式）
- [x] 输出设计文档 `design.md`
- **Status:** complete

### Phase 3: 实现
- [ ] 搭建新编辑器前端框架
- [ ] 实现核心编辑能力（富文本/Block 编辑、Markdown 双向支持、图片/表格/代码块等）
- [ ] 集成到现有知识库文档创建/编辑流程
- [ ] 保留并兼容原有后端 API 与数据模型
- [ ] 添加必要后端接口支持（如附件上传、自动保存、文档块操作等）
- **Status:** pending

### Phase 4: 测试与验证
- [ ] 功能测试：新建/编辑/保存/预览文档
- [ ] 兼容性测试：现有 Markdown 文档在新编辑器中的渲染与回写
- [ ] 移动端/响应式测试
- [ ] 运行现有测试套件，确保未破坏其他模块
- **Status:** pending

### Phase 5: 交付与文档
- [ ] 更新相关文档（README、AGENTS.md 如有涉及）
- [ ] 汇总变更清单与使用说明
- [ ] 向用户交付成果
- **Status:** pending

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| 无 | - | - |
