# Findings & Decisions: 知识库编辑器升级

## Requirements
<!-- 从用户需求中提取的具体要求 -->
- 系统刚完成知识库模块的重建
- 当前知识库编辑器体验较差（"太 low"）
- 需要调研主流知识库产品的编辑器
- 基于调研结果重新设计并修改现有编辑器

## Research Findings

### 一、当前系统实现
- 编辑器页面：`templates/admin/knowledge_editor.html`（后台，已失效链接） + `templates/knowledge/editor.html`（用户侧，实际使用）
- 当前使用 **Toast UI Editor v3.2.2**（CDN / esm.sh 引入）
- 用户侧编辑器配置：
  - 初始编辑模式：`markdown`
  - 预览样式：`vertical`（垂直分栏）
  - 高度：600px
  - 工具栏：heading、bold、italic、strike、hr、quote、ul、ol、task、indent、outdent、table、image、link、code、codeblock、scrollSync
- 内容通过隐藏字段在提交时调用 `editor.getMarkdown()` 保存为 Markdown
- 后端存储在 `posts` 表中，`post_type='knowledge'`，`content_format='markdown'`
- 知识库前端样式：`static/css/knowledge.css`
- `editor-workbench.js` 当前服务于博客 Quill 编辑器，未在知识库编辑器中使用

### 二、当前编辑器的问题
1. **功能基础**：缺少现代知识库编辑器的核心能力
2. **无 AI 辅助**：博客编辑器有的 AI 整理、标签、摘要、续写、推荐能力，知识库都没有
3. **无自动保存/草稿恢复**：误刷新会丢失内容
4. **无图片上传后端**：只能插入图片 URL
5. **无历史卡片/笔记引用**
6. **前后台编辑器代码重复且不统一**：`templates/knowledge/editor.html` vs `templates/admin/knowledge_editor.html`
7. **后台模板引用已删除的 admin 端点**，存在 stale 链接问题
8. **测试覆盖不足**：缺少对 `/knowledge/*` 新空间路由的测试

### 三、主流知识库产品编辑器特性调研

#### 1. Notion
- **Block-based 编辑器**：所有内容都是 Block，可拖拽重组
- **斜杠命令 `/`**：快速插入标题、列表、表格、代码块、嵌入、数据库等
- **拖拽排序**：左侧拖拽手柄，支持块级拖拽
- **嵌入丰富**：支持图片、视频、Figma、PDF、网页书签、CodePen 等
- **双向链接与页面引用**：`@` 提及页面，`[[` 链接页面
- **数据库视图**：表格、看板、日历、画廊视图（本项目暂不需要）
- **实时协作**：多人光标、评论、版本历史
- **模板与 AI**：Notion AI 可生成、续写、总结、翻译

#### 2. 语雀
- **可视化 Markdown 编辑器**：实时渲染，所见即所得
- **Markdown 输入法**：`# ` 标题、`- ` 列表、`> ` 引用、`` ``` `` 代码块等
- **丰富的内容块**：表格、画板、思维导图、高亮块、公式、代码块、文件卡片
- **斜杠命令**：插入语雀功能模块
- **文档模板**：支持模板快速创建
- **团队协作**：评论、@提及、权限管理
- **知识库组织**：目录树 + 文档 + 分组

#### 3. 飞书文档
- **块编辑器**：`/ 快速插入` 工具栏
- **浮动工具栏**：选中文本后弹出格式化选项
- **丰富的内容块**：图片、视频、表格、多维表格、高亮块、代码块、画板、投票、嵌入网页
- **Markdown 支持**：主流 Markdown 快捷键
- **实时协作**：多人编辑、评论、@同事
- **模板库**：上百种文档模板

#### 4. Obsidian
- **Markdown 原生**：所有内容都是本地 Markdown 文件
- **双向链接**：`[[笔记名]]` 链接，自动 backlinks
- **图谱视图**：知识网络可视化
- **插件生态**：700+ 社区插件
- **标签系统**：`#标签`
- **本地优先**：数据所有权

#### 5. Outline
- **开源团队 Wiki 编辑器**
- **Markdown 快捷键 + 斜杠命令**
- **块级操作**：拖拽、复制、删除块
- **嵌入支持**：视频、GitHub、Linear 等
- **实时协作**：多人编辑、评论
- **反向链接**：文档间链接追踪
- **AI 问答**：基于文档内容回答问题
- **数据格式**：存储为 Markdown，可导出

#### 6. GitBook
- **Block-based 编辑器**
- **斜杠命令 `/`** 插入块
- **Markdown 支持**：键盘友好
- **可复用内容块**： reusable content
- **Change Request 工作流**：类似 Git 的评审流程
- **集成丰富**：GitHub、GitLab、OpenAPI、表单等
- **AI Agent**：编辑器内直接调用 AI 修改内容
- **自定义主题与品牌**

### 四、主流开源编辑器技术方案对比

| 编辑器 | 类型 | 框架 | 块编辑 | 斜杠命令 | Markdown | 协作 | 许可证 | 体积 | 适用场景 |
|--------|------|------|--------|----------|----------|------|--------|------|----------|
| **Toast UI Editor** | WYSIWYG Markdown | Vanilla | ❌ | ❌ | ✅ 双向 | ❌ | MIT | 小 | 当前基础方案 |
| **Editor.js** | Block Editor | Vanilla | ✅ | ✅ | 需转换 | ❌ | Apache 2 | 中 | 块编辑，无协作 |
| **Tiptap** | Headless 富文本 | React/Vue/Vanilla | 可扩展 | 可扩展 | 可扩展 | ✅ (Yjs) | MIT | 中 | 自定义编辑器 |
| **BlockNote** | Notion-style Block | React | ✅ | ✅ | 可导出 | ✅ (Yjs) | MPL 2 | 较大 | 快速构建 Notion 风 |
| **Milkdown** | WYSIWYG Markdown | React/Vue/Angular | 部分 | ✅ | ✅ 原生 | 可扩展 | MIT | 中 | Markdown 优先 |
| **Slate / Plate** | 可定制框架 | React | 可扩展 | 可扩展 | 需转换 | ✅ (Yjs) | MIT | 中 | 高度定制 |
| **Lexical** | Meta 开源 | React/Vanilla | 可扩展 | 可扩展 | 需转换 | ✅ (Yjs) | MIT | 中 | 大规模应用 |

### 五、关键趋势总结
1. **块编辑（Block-based）已成主流**：Notion、飞书、GitBook、Outline 均采用块编辑器
2. **斜杠命令 `/` 是标准交互**：快速插入内容块，降低工具栏依赖
3. **Markdown 仍是知识库的重要存储格式**：Outline、Obsidian、GitBook 都保留 Markdown 导出/编辑
4. **AI 辅助写作成为标配**：生成、续写、总结、润色、标签推荐
5. **双向链接/页面引用增强知识关联**：`[[` 或 `@` 链接文档
6. **自动保存/草稿恢复是基本要求**
7. **图片/附件上传是必要能力**

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 待用户确认：完全迁移到 Block Editor 还是增强现有 Toast UI | Block Editor 体验更现代但改造成本大；增强 Toast UI 成本低但上限有限 |
| 待用户确认：是否保留 Markdown 作为主要存储格式 | 现有大量内容已存储为 Markdown，保留 Markdown 可降低迁移风险 |
| 待用户确认：是否引入 React/Vue 前端构建流程 | BlockNote/Tiptap 通常需要现代前端构建流程；当前项目以 Jinja2 + Vanilla JS 为主 |
| 待用户确认：是否复用博客编辑器的 AI 辅助能力 | 知识库文档也应享有 AI 整理、摘要、标签推荐等能力，但需做 Markdown 适配 |
| 待用户确认：是否需要块级拖拽、双向链接、模板库等高级能力 | 决定实现范围（MVP vs 完整重构） |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 后台模板引用已删除的 admin 端点 | 升级前需清理或统一编辑器模板 |
| editor-workbench.js 依赖 Quill | 若知识库编辑器改为非 Quill，需重写工作台或抽象通用接口 |
| AI 整理接口返回的是博客扁平分类 | 知识库需适配树形目录 |

## Resources
- 当前编辑器页面：`templates/knowledge/editor.html`
- 后台编辑器页面：`templates/admin/knowledge_editor.html`
- 知识库样式：`static/css/knowledge.css`
- 知识库路由：`backend/routes/knowledge.py`、`backend/routes/knowledge_base.py`
- 文章编辑器工作台：`static/js/editor-workbench.js`
- 调研参考：Notion、语雀、飞书、Obsidian、Outline、GitBook、Liveblocks editor comparison 2025

## Visual/Browser Findings
- 当前编辑器为传统 WYSIWYG Markdown 编辑器，工具栏位于编辑区上方，功能有限
- 主流产品普遍采用左侧目录树 + 中间编辑区 + 右侧辅助面板/TOC 的三栏布局
- 斜杠命令、块拖拽、浮动工具栏、AI 面板已成为现代编辑器标配

---
*Update this file after every 2 view/browser/search operations*
