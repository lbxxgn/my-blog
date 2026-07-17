# 知识库编辑器升级设计方案（BlockNote 版）

## 1. 设计目标

将当前基于 Toast UI Editor 的知识库编辑器，升级为一个类似 Notion 的现代化块编辑器，同时：
- **保留 Markdown 作为底层存储格式**，确保现有知识库文档完全兼容
- 提供 **斜杠命令 `/`**、**块拖拽排序**、**浮动工具栏** 等现代编辑体验
- 补齐 **AI 辅助写作**、**自动保存/草稿恢复**、**图片上传** 等能力
- 统一前后台编辑器模板，清理失效链接
- 引入轻量级前端构建流程（React + Vite）

## 2. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 块编辑器核心 | **BlockNote** | 最接近 Notion 的开源块编辑器；基于成熟 ProseMirror/Tiptap；原生支持块、斜杠命令、拖拽排序、浮动工具栏；官方支持 Markdown 导入导出 |
| Markdown 转换 | **BlockNote 官方 @blocknote/markdown** | 内置 `blocksToMarkdownLossy()` / `tryParseMarkdownToBlocks()`，转换可靠性高 |
| 前端框架 | **React 18** | BlockNote 官方仅支持 React |
| 构建工具 | **Vite** | 轻量、快速、配置简单；输出 UMD/ESM 模块供 Flask 模板引入 |
| UI 组件库 | **shadcn/ui** 或自定义 | 用于 AI 面板、弹窗、工具栏等辅助 UI（也可用轻量自定义组件） |
| AI 辅助 | **复用现有 `/admin/ai/*` 接口** | 适配 Markdown 输入和知识库树形目录；新增前端 AI 面板 |
| 图片上传 | **复用博客上传机制** | 新增 `/knowledge/doc/upload-image` API，保存到 `static/uploads/` |
| 自动保存 | **新增 `/knowledge/doc/<id>/autosave`** | 定期保存 Markdown 草稿；支持恢复 |

### 为什么选 BlockNote？
- **Notion 体验最佳**：块拖拽、斜杠命令、嵌套块、浮动工具栏都是内置的
- **Markdown 支持官方化**：通过 `@blocknote/markdown` 实现 JSON↔Markdown 转换，比自己写转换器更可靠
- **生态成熟**：基于 ProseMirror/Tiptap，扩展性好，未来可做实时协作（Yjs）
- **AI 友好**：结构化 Block JSON 便于 AI 理解和操作

### 代价
- 必须引入 **React + npm + Vite**
- 部署流程需要增加 `npm run build` 步骤
- 需要学习 BlockNote API 和 ProseMirror 基础概念

## 3. 架构设计

```
┌──────────────────────────────────────────────────────────────────────┐
│                    templates/knowledge/editor.html                    │
│  ┌──────────────┐  ┌─────────────────────────────┐  ┌─────────────┐ │
│  │  左侧目录树   │  │   #kb-editor-root (React)   │  │ 右侧辅助面板 │ │
│  │  (已有)      │  │   BlockNote 编辑器           │  │ AI / 大纲   │ │
│  └──────────────┘  └─────────────────────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    frontend/src/kb-editor.tsx                         │
│  - React 根组件                                                        │
│  - 初始化 BlockNote editor                                             │
│  - 注册自定义块 / 斜杠命令                                              │
│  - 绑定 AI 面板、自动保存、图片上传                                     │
└──────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  BlockNote Core │ │ @blocknote/     │ │  Custom Plugins │
│  + Tiptap       │ │ markdown        │ │  (AI, upload)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       后端 API                                          │
│  /knowledge/doc/new                  POST 创建文档                     │
│  /knowledge/doc/<id>/edit            POST 更新文档                     │
│  /knowledge/doc/<id>/autosave        POST 自动保存草稿                 │
│  /knowledge/doc/<id>/draft           GET  恢复草稿                     │
│  /knowledge/doc/upload-image         POST 图片上传                     │
│  /admin/ai/organize-content          POST 适配 Markdown + 树目录        │
│  /admin/ai/generate-summary          POST 适配 Markdown                 │
│  /admin/ai/continue-writing          POST 适配 Markdown                 │
│  /api/cards                          GET  历史卡片列表                 │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       数据模型                                          │
│  posts.content          → Markdown（不变）                             │
│  posts.content_format   → 'markdown'（不变）                           │
│  posts.metadata         → 可扩展：编辑器版本、草稿时间等                  │
│  drafts                 → 自动保存草稿表（复用或新建）                    │
│  posts.excerpt          → AI 摘要                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## 4. 项目结构变更

```
my-blog/
├── frontend/                      # 新增：前端源码目录
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.tsx              # React 挂载入口
│   │   ├── KbEditor.tsx          # BlockNote 编辑器主组件
│   │   ├── KbEditorApp.tsx       # 包含左侧目录树、编辑器、右侧面板的完整页面
│   │   ├── hooks/
│   │   │   ├── useAutoSave.ts    # 自动保存逻辑
│   │   │   ├── useAiAssist.ts    # AI 辅助逻辑
│   │   │   └── useImageUpload.ts # 图片上传逻辑
│   │   ├── components/
│   │   │   ├── AiPanel.tsx       # AI 辅助面板
│   │   │   ├── TocPanel.tsx      # 目录大纲面板
│   │   │   ├── MetaPanel.tsx     # 文档元数据面板
│   │   │   └── SlashMenu.tsx     # 自定义斜杠菜单（可选）
│   │   ├── lib/
│   │   │   ├── markdown.ts       # Markdown 转换封装
│   │   │   ├── api.ts            # 后端 API 调用
│   │   │   └── utils.ts          # 工具函数
│   │   └── styles/
│   │       └── kb-editor.css     # 编辑器样式
│   └── dist/                     # Vite 构建输出
│       ├── kb-editor.js
│       └── kb-editor.css
├── static/                        # 原有静态资源
├── static_build/                  # 原有构建输出
├── templates/knowledge/editor.html # 修改：引入 Vite 构建产物
└── backend/routes/knowledge.py    # 修改：新增 API
```

## 5. 功能清单（MVP）

### 5.1 编辑器核心
- [ ] 块类型：标题（H1-H3）、段落、无序列表、有序列表、待办列表、引用、代码块、表格、图片、分隔线、提示块（callout）
- [ ] 斜杠命令 `/`：快速插入块，支持键盘导航和搜索
- [ ] 块拖拽：左侧拖拽手柄，支持块级上下移动
- [ ] 浮动工具栏：选中文本时弹出，支持加粗、斜体、删除线、行内代码、链接、高亮
- [ ] Markdown 快捷输入：`# ` 标题、`- ` 列表、`> ` 引用、`` ``` `` 代码块
- [ ] 撤销/重做

### 5.2 图片与附件
- [ ] 图片块支持本地上传
- [ ] 粘贴图片自动上传
- [ ] 图片块支持 URL 插入
- [ ] 上传接口：`/knowledge/doc/upload-image`

### 5.3 自动保存与草稿
- [ ] 编辑后 3 秒自动保存草稿
- [ ] 重新进入编辑器时提示恢复草稿
- [ ] 手动保存后清除草稿

### 5.4 AI 辅助面板
- [ ] **AI 整理**：推荐标题、摘要、标签、目录分类
- [ ] **AI 续写**：根据上下文续写段落
- [ ] **AI 摘要**：生成摘要并一键插入
- [ ] **历史卡片插入**：搜索历史卡片/笔记，插入为引用块

### 5.5 文档信息面板
- [ ] 目录大纲同步高亮
- [ ] 文档字数、块数统计
- [ ] 标签快捷编辑
- [ ] 发布/草稿状态切换

## 6. Markdown 转换策略

使用 BlockNote 官方 `@blocknote/markdown`：

```typescript
import { BlockNoteEditor } from "@blocknote/core";
import { blocksToMarkdownLossy, tryParseMarkdownToBlocks } from "@blocknote/markdown";

// 保存：blocks → markdown
const markdown = await editor.blocksToMarkdownLossy(editor.document);

// 读取：markdown → blocks
const blocks = await editor.tryParseMarkdownToBlocks(existingMarkdown);
editor.replaceBlocks(editor.document, blocks);
```

### 兼容性说明
- `blocksToMarkdownLossy` 是"有损"导出：复杂块可能无法完美转 Markdown
- 对无法精确表示的内容，使用 HTML 嵌入 Markdown 或降级为文本块
- 现有知识库 Markdown 文档可直接导入为 blocks
- 详情页渲染逻辑（`markdown2 + bleach`）保持不变

## 7. 后端 API 调整

### 7.1 新增接口

```
POST /knowledge/doc/<id>/autosave
Body: { content: string, title?: string }
Response: { success: true, saved_at: ISOString }
```

```
GET /knowledge/doc/<id>/draft
Response: { success: true, draft: { content, title, saved_at } | null }
```

```
POST /knowledge/doc/upload-image
Body: multipart/form-data, field: file
Response: { success: true, url: "/uploads/xxx.png" }
```

### 7.2 AI 接口适配
- `/admin/ai/organize-content`：
  - 输入从 Quill HTML 改为 Markdown
  - 分类建议改为知识库树形目录匹配
- `/admin/ai/generate-summary` / `/admin/ai/continue-writing`：
  - 输入改为 Markdown
  - 输出 Markdown

### 7.3 模型调整
- 复用 `drafts` 表保存知识库草稿，或扩展 `posts.metadata` JSON 字段
- `metadata` 中可记录 `editor_version: 'blocknote-v1'`

## 8. 构建与部署

### 8.1 开发构建
```bash
cd frontend
npm install
npm run dev        # Vite dev server，热更新
```

### 8.2 生产构建
```bash
cd frontend
npm run build      # 输出到 frontend/dist/
```

### 8.3 与 Flask 集成
- Vite 配置 `base: '/static/frontend/'`
- Flask 将 `frontend/dist/` 注册为静态文件目录，或构建后复制到 `static/frontend/`
- 模板中引入 `<script src="/static/frontend/kb-editor.js"></script>`

### 8.4 更新 Makefile
新增 `build-frontend` target：
```makefile
build-frontend:
	cd frontend && npm run build
	cp -r frontend/dist static/frontend

build-assets: build-frontend
	$(PYTHON) build.py --merge --minify
```

## 9. 模板调整

- **修改**：`templates/knowledge/editor.html`
  - 移除 Toast UI Editor CDN
  - 改为 React 挂载点 `<div id="kb-editor-root"></div>`
  - 通过 `window.__KB_EDITOR_INIT__` 传递初始数据（文档内容、目录树、标签等）
  - 引入 Vite 构建产物
- **删除/清理**：
  - `templates/admin/knowledge_editor.html` 等 stale 模板
- **保持**：`templates/knowledge/doc.html` 详情页渲染逻辑不变

## 10. 实施步骤

| 阶段 | 任务 | 预计耗时 |
|------|------|---------|
| Phase 2 | 完成设计文档、确认方案 | 已完成 |
| Phase 3.1 | 初始化 npm + Vite + React + BlockNote 项目 | 0.5 天 |
| Phase 3.2 | 配置 Vite 构建，与 Flask 静态资源集成 | 0.5 天 |
| Phase 3.3 | 实现 BlockNote 编辑器基础组件 + Markdown 转换 | 1 天 |
| Phase 3.4 | 实现块类型、斜杠命令、浮动工具栏、块拖拽 | 1 天 |
| Phase 3.5 | 实现图片上传、自动保存/草稿恢复 | 1 天 |
| Phase 3.6 | 实现 AI 辅助面板 | 1-2 天 |
| Phase 3.7 | 后端 API 新增与适配、模板调整 | 1 天 |
| Phase 4 | 功能测试、兼容性测试、现有测试回归 | 1 天 |
| Phase 5 | 文档更新、交付 | 0.5 天 |

**总计：约 7-9 个工作日**

## 11. 风险与回退方案

| 风险 | 影响 | 回退方案 |
|------|------|---------|
| BlockNote Markdown 转换有损失 | 中 | 复杂内容用 HTML 嵌入；持续测试并调整 |
| React + Vite 增加部署复杂度 | 中 | 提供 Makefile target 一键构建；CI 中集成 |
| BlockNote 对中文输入法兼容性 | 低 | BlockNote 基于 Tiptap/ProseMirror，中文输入已有成熟方案 |
| 构建产物体积过大 | 中 | Vite 按需打包 + gzip；仅编辑器页面加载 |
| 用户不适应新编辑器 | 中 | Markdown 源文件保留，可随时回退到旧版 Toast UI |

## 12. 后续可扩展方向

- 实时协作（Yjs + WebSocket）
- 双向链接 `[[文档名]]`
- 文档模板库
- 嵌入块（视频、Figma、PDF、书签）
- 评论与 @提及
- 文档版本历史
