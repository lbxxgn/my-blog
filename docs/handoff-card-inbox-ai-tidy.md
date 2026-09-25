# 交接文档：个人版优化清单第 7–11 项

**创建**: 2026-09-25
**状态**: 第 7–9 项已于 2026-09-25 完成（见下，**不要重做**）；本文档要实现的是 **第 10、11 项**
**目标读者**: 负责实现的 Agent（请先完整阅读本文，再动代码）

---

## 0. 项目速览

- 路径：`/Users/gn/Documents/MyWorkplace/my-blog`
- 技术栈：Flask 3 + SQLite（`db/simple_blog.db`）+ Jinja2 模板 + vanilla JS；React 19 + Vite 仅用于知识库编辑器（`frontend/`，构建产物输出 `static/frontend/`）
- 环境：Python 3.11，venv 在 `.venv/`（`.venv/bin/python -m pytest`、`flask` 命令同理）
- 测试：pytest（`tests/`，先看 `conftest.py` 的 fixtures）；新增测试不许联网（mock LLM/embedding）
- Lint 标准：`ruff check --select E9,F821,F811 backend/ tests/`（完整默认规则在基线上有大量历史错误，不是你们的责任，别去修）
- 数据库迁移：版本化注册表 `backend/migrations/__init__.py`（当前到 `009_embeddings`），新迁移要求幂等，执行 `python -m backend.migrations`
- **不要 git commit**（由用户决定）；新增静态 JS/CSS 后运行 `python scripts/generate_manifest.py`；动了 React 后 `cd frontend && npm run build`

## 1. 第 7–9 项已完成（衔接用，禁止重复实现）

| 项 | 成果 | 关键文件 / 端点 |
|---|---|---|
| 7. 那年今日 + 随机漫步 | 回顾页 + 首页侧边栏 widget | `backend/routes/review.py`、`templates/review.html`、`static/js/review.js`；`GET /api/review/today`、`GET /api/review/random` |
| 8. 每周 AI 回顾 | 汇总 7 天动态 → AI 生成回顾存为知识文档（同周幂等） | `backend/services/weekly_review.py`；`POST /api/review/weekly/generate`、`GET /api/review/weekly/status`、`flask weekly-review` CLI |
| 9. 写作热力图 | GitHub 风格 7×53 热力图 + 连续天数统计 | `GET /api/review/activity?days=371`，渲染在 `/review` |

实现第 10、11 项时直接复用上面的页面/端点模式与基础设施。

## 2. 要实现：第 10 项 —— 收件箱式批处理界面

**痛点**：浏览器扩展剪藏、分享、语音速记来的卡片会积压在 `status='idea'`，需要一个邮件客户端式（Superhuman 风格）的全键盘快速过件界面，把收件箱清空。

### 2.1 功能规格

- 新页面 `GET /inbox`（`@login_required`），入口三处：`templates/base.html` 导航（登录可见）、`/review` 页按钮、知识库卡片页空态提示
- 列表：当前用户 `status='idea'` 的卡片，按 `created_at` 倒序；每行显示标题、摘要（前 120 字）、来源徽标（source: web/share/voice/plugin/mobile）、时间、标签；`source_url` 存在的显示可点链接
- **键盘操作**（仿 Superhuman，必须有）：
  - `j` / `k`：上下移动选中
  - `p`：升级为孵化（`status='idea' → 'incubating'`）
  - `d`：删除（调现有 `delete_card`，前端移除并 toast 可撤销不必做）
  - `e`：归档——**需要给卡片状态机新增 `'archived'` 状态**（见 2.2）
  - `Enter`：打开该卡片的编辑界面（知识库现有卡片编辑入口，复用其 URL/弹层）
  - 顶部显示「剩余 N 件」；清空后显示庆祝空态
- 操作全部走现有 API：`PUT /api/cards/<id>`（更新 status）、卡片删除端点（在 `backend/routes/knowledge_base.py` 找现有的）；若现有端点不满足（如批量、archived 校验），再新增最小端点
- 移动端：不提供键盘，每行渲染对应操作按钮（升级/归档/删除），点按即可
- 每完成一个操作立即本地移除该行并显示剩余计数，不等整页刷新

### 2.2 新增 `'archived'` 状态（必要的小改动）

- 卡片状态机当前取值 `idea/draft/incubating/published`，校验在 `backend/routes/knowledge_base.py`（约 :403 附近）与卡片页查询处
- 放行 `'archived'`；`/knowledge_base` 卡片页默认**不显示** archived，提供「已归档」筛选 tab（与现有状态筛选风格一致）
- 数据迁移不需要（SQLite 文本列），但要全库搜一遍 `status` 判断/过滤的地方一起改

### 2.3 测试要求

`tests/test_inbox.py`：archived 状态校验放行与卡片页过滤、inbox 页渲染与登录跳转、（若新增端点）其权限与行为。前端 `node --check`。

## 3. 要实现：第 11 项 —— AI 主动给整理建议

**痛点**：现有 AI（`backend/ai_services/card_merger.py`、标签生成等）都是被动等指令。要让 AI **周期性主动扫描**卡片库，输出可以一键采纳的整理建议。

### 3.1 建议类型（四类）

| type | 内容 | 采纳动作（必须幂等、事务化） |
|---|---|---|
| `merge_cards` | N 张（2–5）主题相近的卡片可合并，附建议标题与理由 | 复用 `card_merger.py` 的合并落库逻辑：新建合并卡片，来源卡置 `archived` 并记录来源；若任一来源卡已不存在则建议失效 |
| `merge_tags` | 多个同义/近义标签建议合并为一个目标标签 | 重写涉及卡片的 `cards.tags` JSON 字段；同时更新博客侧标签表（如该标签也被文章使用，先确认现有标签模型关系再动） |
| `promote` | 孵化中的卡片（或 idea 积压很久的）内容已足够，「可以动笔成文」 | 卡片 `status → 'draft'`（进入写作就绪），可在采纳后给跳转编辑器链接 |
| `duplicates`（可选） | 内容高度重复的卡片对 | 复用 embedding：`backend/models/embeddings.py` 的 `search_similar` 找同类型余弦 > 0.95 的对；**用户未配置 embedding 时跳过此类**，其余三类不依赖 embedding 必须可用 |

### 3.2 后端

- 新服务 `backend/services/card_tidy.py`：按用户收集卡片/标签 → 分批调 LLM（批次建议 ≤20 张卡片/批，控制 token）→ 解析建议 → 落库
- **新表存建议**（迁移 `010`，幂等）：`card_suggestions(id, user_id, type, payload TEXT(JSON), status TEXT['pending'|'accepted'|'dismissed'|'stale'], created_at, decided_at)`；建议引用的卡片 id 集合放 payload，采纳前校验卡片仍存在
- 端点（均 `@login_required`，模式照抄 `/api/review/weekly/generate`）：
  - `POST /api/suggestions/generate`：异步生成（后台 daemon 线程 + `app.app_context()` + 内存 running 状态防重入），202 + status 轮询
  - `GET /api/suggestions`：`pending` 列表（带卡片摘要快照，前端不用二次查询）
  - `POST /api/suggestions/<id>/accept`：按 type 执行采纳动作 + 标记 accepted；任一前置不满足 → 409 并标记 stale
  - `POST /api/suggestions/<id>/dismiss`：标记 dismissed
- CLI：`flask card-tidy`，可挂进 crontab（与 `flask weekly-review` 同一行并列即可）；手动触发入口放 `/inbox` 页

### 3.3 前端

- 在 `/inbox` 页顶部加「AI 整理建议」区块（也可放 `/review`，二选一以体验顺为准）：
  - 「生成建议」按钮 + 生成中状态轮询
  - 建议卡片列表：类型徽标 + 理由 + 涉及的卡片标题（可点击预览）+「采纳」/「忽略」按钮
  - 采纳成功后该行消失并 toast；涉及卡片从收件箱列表同步移除（合并/归档的情况）
- 样式：页面级内联 `<style>` 或追加 `static/css/style.css` 末尾，**必须用 CSS 变量**（`:root` 里 `--primary-color` 等，暗色自动适配）

### 3.4 测试要求

`tests/test_suggestions.py`：四类建议生成（mock LLM，验证 prompt 组装与解析容错——LLM 返回非法 JSON 要能跳过不炸）、accept 各类型后卡片/标签的真实变化、幂等（重复 accept）、卡片已删 → 409+stale、dismiss、未配置 embedding 时 duplicates 类跳过、generate 防重入。不联网。

## 4. 共享约定（务必遵守）

- **认证/CSRF**：装饰器在 `backend/auth_decorators.py`（`login_required` 等）；前端 fetch 带 `X-CSRFToken` 头（`window.getCsrfToken()`，见 `static/js/base.js`）
- **AI provider**：`get_user_ai_config(user_id)`（`backend/models/users.py`）→ `TagGenerator.create_provider(...)`；自由文本生成用 `provider.generate_text(prompt)`（`backend/ai_services/openai_compatible.py`，本次新增）
- **embedding（可选能力）**：`backend/ai_services/embeddings.py` 的 `get_embedding_config/embed_text`；未配置必须优雅降级，不得报错
- **异步长任务**：后台线程 + 内存 running 字典 + status 轮询，参考 `backend/routes/review.py` 的 weekly generate
- **模板**：`extends "base.html"`，block：`title`/`page_type`/`head`/`content`/`scripts`；`page_type` 参考现有页面取值
- **时间口径**：created_at 是 UTC 字符串；面向用户的日期比较用 SQLite `datetime(created_at, '+8 hours')`（见 `backend/routes/review.py` 的 today 实现）
- **前端 JS**：vanilla，语法验证 `node --check <file>`；toast 用 `window.showAppToast()`

## 5. 验收标准

1. `.venv/bin/python -m pytest tests/ -q -x --ignore=tests/visual` 全量通过、无回归（当前基线 368 个测试）
2. `ruff check --select E9,F821,F811 backend/ tests/` 通过；新增 JS 全部 `node --check` 通过
3. 冒烟：登录后 `/inbox` 可用键盘完整过一遍收件箱（升级/归档/删除）；「生成建议」→ 采纳一条 merge 建议 → 确认卡片真实合并、来源卡归档
4. `python scripts/generate_manifest.py` 已重跑；若动了 React 则 `npm run build` 成功
5. 完成后输出：改动文件清单、每个文件做了什么、测试/lint/构建结果、问题与决策（**不要 git commit**）
