# 前端交互复核（2026-11）

> 复核范围：公开站点（首页 / 文章 / 搜索 / 归档 / 标签 / 作者 / 登录）、移动端外壳、知识库、回顾、后台管理、写作编辑器。
> 方法：通读模板 + 原生 JS + CSS，逐条核对 DOM 结构、事件绑定与后端实际行为；行号对应当前 `HEAD`（68e07e0）。
> 关联文档：[optimization-backlog.md](optimization-backlog.md)（P0/P1/P2 历史记录，本文只记录**尚未解决**的交互问题）。

---

## 一、一句话结论

问题不在于"某个页面做得糙"，而在于**交互层缺少统一的基础设施**：同一个能力有 3–5 套实现，全局监听各自为政，页面状态几乎都不落盘。每加一个功能，就顺手多出一处新的不一致——这正是"总感觉还能更好"的根源。

---

## 二、四个横向病因（先看这里，再看清单）

### 2.1 一份能力，多套实现

| 能力 | 分散在哪 |
|---|---|
| 轻提示 | `base.js:132` `showAppToast`、`utils.js:55` `SB.showToast`、`shortcuts.js` `showNotification`、`code-copy.js` 自建 `.code-copy-toast`、`share.js` 用 `.copy-toast`、移动端用 `.toast-message` |
| 主题切换 | `base.html:51` 首帧内联、`base.js:84-116`、`command-palette.js:43-56` |
| 弹层 | `base.js:168` confirm（有 `role`/焦点环）、`base.js:262` prompt（**无** `role`/`aria-modal`）、`post.html:528,540` 自建 modal、`dashboard.html` 4 个 `.modal`、`post.html:570` 分享弹窗、移动端编辑器面板、标签/分类选择器 |
| 折叠 | `knowledge-tree.js:201` 用 class，`knowledge-toc.js:51` 用 `style.display` |
| Esc 关闭 | `base.js:53`、`command-palette.js:87`、`shortcuts.js:10`（直接 `remove()` DOM） |

后果很直接：改一处只改一处，行为随页面而变，同一个 bug 要修 N 遍。**这是"提升空间"的绝大部分**。

### 2.2 全局监听没有归属（当前最危险的一类）

- `command-palette.js:84-100`：keydown 只在 `!overlay` 时返回；`close()`（259-263）只把 `display` 设为 `none`。**面板打开过一次之后**，全站 `↑/↓` 被 `preventDefault`（页面无法方向键滚动）、`Enter` 被吞掉并执行 `execute()`（真的会跳转页面）、`Esc` 被 `stopImmediatePropagation`（其他弹窗再也关不掉）。
- `shortcuts.js:10`：`esc` 的实现是 `document.querySelectorAll('.shortcut-help-modal, .modal, [role="dialog"]').forEach(m => m.remove())`——把"关闭"写成了"销毁"。命令面板的 `.cmdk-panel` 带 `role="dialog"`（`command-palette.js:62`），被删后 overlay 里什么都没有，只能刷新页面。
- `shortcuts.js:10` 还注册了 `ctrl+r` / `ctrl+n` / `ctrl+f`（后台、时间线页）——劫持浏览器保留键，用户想刷新/查找/开新窗口全部失效。
- 滚动监听有 4 处（`main.js:1`、`enhancements.js:65/211/240`），其中 `main.js` 每帧直接读写布局，没有 rAF 节流。

### 2.3 页面状态不落盘（"一回去就没了"）

| 场景 | 现状 |
|---|---|
| 首页无限滚动 | 页码只在内存（`infinite-scroll.js:37-53`），URL 永远是第 1 页；从文章返回列表，滚动位置和已加载条数全丢 |
| 后台批量选择 | `selectedPosts` 是内存 `Set`，翻页是普通 `<a>`（`dashboard.html:171`）→ 整页刷新即清空，且无任何提示 |
| 知识库树 | 全部分支硬编码 `collapsed`（`_tree.html:24,37`）→ 每次进页面逐级重新点开 |
| 筛选条件 | `archive.html:16` 写死"最新"高亮；知识库搜索必须点按钮提交 |
| 评论区 | 提交后 `location.reload()`（`post.html:785`），评论区重新折叠 |

### 2.4 移动端是"第二套产品"

- 底部导航**只在首页**渲染（`base.html:47` + `468-497`），而 `≤768px` 时 `header` 被 CSS 整块隐藏 → **文章页、搜索页、归档页在手机上没有站点导航**，只剩一枚悬浮返回键。
- 返回键在滚动 10px 后自动消失（`enhancements.js:238-246`），且用内联 `onclick` + `history.length>1` 判断（`base.html:56-58`）。
- 文章页把"上一篇 / 下一篇 / 返回首页"整块 `display:none`（`post.html:321-323`）。
- 后台在手机上同时存在侧边栏和底部导航两份，而分类 / 标签 / 回收站 / 备份 / AI 设置没有入口（`base.html:455-465`）。

---

## 三、P0：建议本周修

| # | 问题 | 位置 | 修法 |
|---|---|---|---|
| P0-1 | 命令面板关闭后仍劫持全站键盘，`Enter` 会直接跳转 | `command-palette.js:84-100`、`259-263` | 处理器首行加 `if (!overlay \|\| overlay.style.display === 'none') return;`；`close()` 时重置 `currentItems/activeIndex` |
| P0-2 | `Esc` 把弹层 DOM 删掉，命令面板再也打不开 | `shortcuts.js:10`、`command-palette.js:62` | 去掉通配 `[role="dialog"]` 的 `remove()`，改为分发 `close` 事件或调用各组件自己的 `close()` |
| P0-3 | 劫持 `Ctrl+R/N/F` | `shortcuts.js:10` | 只保留 `Ctrl+K`、`Ctrl+/`、编辑器内 `Ctrl+S`；`Ctrl+R/F` 交还浏览器 |
| P0-4 | 知识库文档页树折叠双绑定 → 点 ▸ 没反应，文档列表永不开 | `knowledge-toc.js:51-64` vs `knowledge-tree.js:201-214` | 删除 `knowledge-toc.js` 的折叠代码（50-63 行），统一由 `knowledge-tree.js` 用 class + `aria-expanded` 实现 |
| P0-5 | 批量删除把"移入回收站"描述成"不可撤销的彻底删除" | `dashboard.html:244` vs `backend/routes/admin/batch.py:143` | 文案改为"将移入回收站，可恢复"，成功 toast 附"去回收站"链接 |
| P0-6 | 评论提交后整页刷新且评论区重新折叠，用户看不到自己刚发的评论 | `post.html:581`、`785`、`enhancements.js:120-129` | AJAX 成功后把评论节点追加进 `.comments-list` 并展开评论区，不刷新页面 |
| P0-7 | 已登录用户仍需手填姓名 / 邮箱 | `post.html:607-608`、`post_detail.py:216` | 登录态隐藏身份字段，后端用 session 兜底（保留匿名评论的表单作为"未登录"分支） |
| P0-8 | "全选"语义与视觉不一致；翻页静默丢选择 | `admin-dashboard.js:217`、`dashboard.html:109/171` | `checked` 按"本页全选"判定，跨页选择用 `indeterminate`；选择集写 `sessionStorage` 并常驻显示"已选 N 篇（跨 X 页）" |
| P0-9 | 无限滚动生成的卡片 DOM 与模板不一致 | `index.html:85-125`（`a > article`）vs `infinite-scroll.js:253-266`（`article > a`） | 统一为模板结构；最好由后端返回渲染好的片段，前端只 insert |
| P0-10 | `escapeHtml` 在 `window.SB` 未就绪时退化为不转义 | `infinite-scroll.js:312-314` | 直接用本地实现或断言 `SB` 存在；`src` 属性优先 `element.src = url` 而非拼字符串 |
| P0-11 | 空正文点"保存草稿/立即发布"毫无反应（`required` 挂在被隐藏的 textarea 上） | `editor.html:45` + `editor.js:8` + `editor-page.js:3-16`（校验函数被 `editor.js:214` 覆盖成死代码） | 去掉 `required`，在提交处显式判空并 toast + 聚焦正文 |
| P0-12 | 提交瞬间就清空本地 + 服务端草稿，POST 失败即彻底丢失 | `editor.js:96-102` | 改为 fetch 提交，**成功返回后**再清草稿；失败保留并提示 |
| P0-13 | `Ctrl+S` 在已发布文章上会点到"取消发布"按钮 | `shortcuts.js:10` + `editor.html:127` | 给"更新"按钮加 `id="saveBtn"` 并前置选择器；`saveDraft()` 不再硬写 `is_published=false` |
| P0-14 | 状态浮标写"已保存"，实际只存了草稿表，文章本体没落库 | `editor.html:32-35` + `draft-sync.js:8-9` | 文案改"草稿已备份（正文未保存）"，仅 POST 成功后显示"已保存" |

---

## 四、按模块的改进点

### 4.1 移动端信息架构（影响面最大）

1. **导航断层**：`mobile_shell_enabled` 只对首页为真（`base.html:47`），但 header 是全站隐藏的。建议把底部导航提升到"全站壳"层级（登录页/密码页除外），文章页保留"返回 + 目录 + 搜索"三项。
2. **单篇文章的出口**：恢复移动端上一篇/下一篇（可折叠成一行），或在文末给"同分类其他文章"。
3. **返回键**：不要滚动即隐藏；改为"向下滚隐藏、向上滚出现"，并加 `aria-label` 与 44px 触区（当前 40px）。
4. **移动端快速发布没有标题**：`.mobile-editor-title-input{display:none}`，标题由 `buildTitleFromContent` 自动截取（`mobile-editor.js:104,178`）→ 发出去标题和预期不符，且用户全程无感。建议文本域上方保留一行可选的标题输入，或发布前用一行文字显示"标题将自动设为：…"。
5. **后台移动端**：侧边栏与底部导航二选一（推荐隐藏侧边栏），底部导航补"更多"收纳分类/标签/回收站，高亮判断从路径子串改为 `request.endpoint`（当前 `/admin/ai/settings` 匹配不到 `'/site'`，多页不高亮）。

### 4.2 阅读页

1. **评论区默认折叠，且折叠态没有"有没有人聊"的信息**（`post.html:581`）。建议折叠条上直接显示最新一条评论摘要 + 头像，展开后不再收起。
2. **评论能力单一**：无回复、无相对时间、无排序、无"作者回复"标记。至少补一层回复与"最新/最早"切换。
3. **评论区位置偏下**：读完正文要跨过标签、分享、AI 操作区才看到评论；建议在文末浮动"评论 (N)"锚点。
4. **分享与 AI 动作同级**："沉淀到知识库 / 导师点评"是低频管理动作，却和分享按钮并列在正文下方（`post.html:495` vs `525`）。建议收进"更多"菜单或标题区右侧。
5. **复制链接失败无反馈**：`share.js` 的 `catch` 只 `console.error` → 用户点了没反应。统一走 `showAppToast`。
6. **阅读模式不可发现**：`R` 单键切换（`enhancements.js:167`），没有出现在 `Ctrl+/` 的快捷键清单里，按钮字形还是 `&#x1D4D7;`（𝒗）。建议按钮用图标 + 首次进入给一次性提示。
7. **目录与锚点**：`.post-toc` 是 `≥1200px` 才出现的 fixed 浮层（`enhancements.css:1313`），但全站没有 `scroll-margin-top`，跳转后标题会被 sticky header 遮住。

### 4.3 首页信息流与无限滚动

1. **返回即重置**：补 `history.scrollRestoration = 'manual'` + `sessionStorage` 记录已加载页/滚动位置，或用 `?page=N` 同步 URL。
2. **没有尽头也没有出口**：滚到底只有"没有更多了"，没有"回到顶部"、没有 footer 可达。建议到底部时露出 footer + 一个"回到顶部"。
3. **加载态不连续**：`hideLoadingIndicator` 只是把文字换回"加载更多"（`infinite-scroll.js:355-367`），没有骨架屏；`skeleton-card` 样式已存在但没被使用。
4. **失败态弱**：加载失败给"点击重试"按钮是好的，但没有说明原因、没有自动重试。
5. **筛选丢失**：分类切换会整页跳转（`index.html:71-79`），与"无限滚动"的心智不连续；且移动端 `.category-filter` 被 CSS 隐藏，只能去"发现"页找分类。

### 4.4 搜索与命令面板

1. **访客用不了命令面板**：`command-palette.js:252` 的 `isLoggedIn()` 直接 return，而 `shortcuts.js` 对未登录用户根本不注册 `Ctrl+K` → 访客按了没反应。建议未登录时聚焦/跳转 `/search`。
2. **两套搜索心智**：命令面板即搜（`/api/search/all`），搜索页必须点按钮且整页刷新（`search.html:19`），也没有 `↑↓/Enter` 结果导航。建议抽出同源组件，或让搜索页复用 API 做局部刷新。
3. **空态缺失**：`/search` 不带 `q` 时 `posts is None` 分支什么都不渲染（`search.html:97`）——从命令面板"去搜索页搜索"落到这里的用户会以为页面坏了。建议渲染最近搜索 / 热门标签 / 可搜范围说明。
4. **嵌套 landmark**：`search.html:8` 的 `<main>` 套在 `base.html:233` 的 `<main>` 里（`tags.html:6`、`tag_posts.html:6`、`knowledge/*` 同样），读屏的 landmark 导航会错乱。
5. **归档筛选**：`archive.html:16-19` 的"最新"硬编码 active，`days=7/30/90` 无选中态，且 `href` 写死绝对路径（子路径部署会 404）。

### 4.5 写作编辑器

> 编辑器是交互密度最高的页面，也是"点了没反应"最集中的地方。P0-11～P0-14 已在上表，以下是其余问题。

1. **上传进度和自动保存抢同一个提示位**：两者都写 `#saveStatus`（`editor.js:131-181` vs `draft-sync.js:7`），上传结束的 `setTimeout` 3 秒后无条件清空，会把"保存失败，已保存到本地"一并抹掉。上传应该有自己的进度条 / toast。
2. **图片工作台绕过 Quill 文档模型**：`editor-workbench.js:53-56` 的"上移/下移/设为首图/移除"直接 `insertBefore`/`remove` DOM → `Ctrl+Z` 撤不了、移动后索引错位、重渲染可能抛错；"移除"也没有确认。
3. **AI 自动整理默认开启且会覆盖字段**：停止输入 1.4 秒即自动请求（`editor-workbench.js:17-31`），持续消耗 token 且无开关；"应用全部建议"直接覆盖标题/标签/分类，无确认无撤销。
4. **草稿恢复与冲突弹窗**：恢复会直接覆盖当前正文（`editor.html:20-29`），无确认、无撤销、横幅无 `aria-live`；冲突弹窗把设备名/标题未转义插入 `innerHTML`（`draft-sync.js:21`），且无 `role="dialog"`／Esc／焦点管理，自动保存每 15 秒可能反复叠出遮罩。
5. **标签输入与移动端割裂**：后台用 `datalist`（`editor.html:71-76`），只能补全输入框整体值，第二个标签起没有补全、也没有 chip；移动端却是"点选 + 回车创建"（`mobile-editor.js:38-47`）。
6. **格式切换失败会写坏正文**：`convert-format` 失败只 `console.warn`（`editor.js:326-357`），但 `contentFormat` 和下拉框已切到 Markdown → 保存后按 Markdown 渲染，整篇格式报废。失败必须回滚 select 与内部状态。
7. **移动端细节**：语音识别在关闭面板后仍在录（`mobile-editor.js:3` 未保存 stop 句柄）；标签浮层用 `window.innerHeight` 定位，被 iOS 键盘遮挡（`:169`）；工具栏 6 个图标只有 `title`；「首行缩进」「媒体库」被 `nowrap` 横向滚动推到可视区外（`editor.html:1534-1538`），按钮高度 28px 低于 44px 触控标准。
8. **知识库（React/BlockNote）编辑器**：未拦截 `Cmd/Ctrl+S`（`KbEditorApp.tsx:359-401`）→ 弹浏览器"另存为网页"，与博客编辑器不一致；发布切换先翻状态再保存（`:157-162`），保存失败时按钮已经变成"取消发布"；自动保存 3 秒防抖没有 `pagehide` flush（`useAutoSave.ts:61-108`），关标签页会丢最后几秒。
9. **无障碍**：标题 `<label>` 被 `display:none` 移出无障碍树（`editor.html:1112-1114`），`#title` 只剩 placeholder 作为名称，进页面也不自动聚焦。
10. **一致性债**：`editor.html:299-1670` 有约 1300 行内联 `<style>`，`.autosave-indicator`、`#content.source-mode`、`.markdown-preview` 重复定义，`@media(max-width:768px)` 出现 5 次、靠 `!important` 层层覆盖，深色主题靠硬编码兜底。建议抽成 `static/css/editor.css`。

### 4.6 后台管理（摘重点）

1. **列表不可排序**：表头全是纯文本，后端也没有 `sort` 参数（`dashboard.html:107` 起）；草稿一多只能肉眼扫。
2. **批量栏随页面滚走**：批量操作栏是普通文档流（`dashboard.html:95`），向下勾选后看不到"已选 N 篇"；改 `position: sticky`。
3. **状态色不分**：已定时与草稿共用 `.status.draft`（`dashboard.html:127`），类型/分类只靠 hover 气泡（触屏不可见）。
4. **点标题跳前台**（`dashboard.html:122`）：管理语境下预期是打开编辑，私密/密码文章还会撞权限页。
5. **弹层无 dialog 语义**：`dashboard.html:209` 起的 4 个 `.modal` 没有 `role/aria-modal`、Esc、焦点陷阱、点遮罩关闭。
6. **评论页一次性全量渲染**（`comments.html:15`）：无分页、无可见/已隐藏筛选，量大后既慢也无法批量处理。
7. **回收站只有单条操作**（`trash.html:11`）：无批量恢复/彻底删除/清空，也没有保留期说明。
8. **长任务没有进度**：导入（`import.html:47`）、AI 向量重建（`ai_settings.html:159`）、导出（`export.html:33`）都是同步等待或纯链接，按钮不禁用、可重复点击。
9. **不可逆操作缺确认**：分类/标签"合并"一键执行且不可回滚（`categories.html:49`、`tags.html:49`），而同页"删除"却有确认。
10. **恢复备份的保险级别不一致**：上传恢复要求手输 `RESTORE`，列表里的"恢复"只要点一次确认（`backup.html:125`）。

### 4.7 知识库与回顾（摘重点）

1. **树状态不持久化**（`_tree.html:24,37`）：深层目录每次重新点开，是"知识库不好用"最直接的体感来源。
2. **管理按钮只在 hover 出现**（`knowledge.css:113-121`）：触屏与键盘用户无法新建子目录 / 重命名 / 编辑。
3. **折叠箭头是 `<span>`**（`_tree.html:13`）：不可聚焦、无 `aria-expanded`，整棵树没有 `role="tree"` 语义。
4. **文档页没有"下一篇"**（`doc.html:64-73`）：读完只能回侧栏找，知识库无法顺藤摸瓜地串读。
5. **拖拽排序不可预期**：文档插入用 `Date.now() % 1e9`（`knowledge-tree.js:181`），且不允许文档之间排序。
6. **搜索不即时**（`knowledge/search.html:34`）：输入与筛选都要点按钮，空结果不回显筛选条件。
7. **回顾页只有聚合列表**（`review.html:250`）：没有逐条节奏（上一条/跳过/已看/进度），"回顾"退化成"浏览"。
8. **热力图不可访问**（`review.js:65`）：每格只有 `title`，无坐标轴、不可聚焦，手机与读屏都拿不到信息。

### 4.8 反馈层（toast / 确认 / 空态 / 加载）

1. **toast 会叠在一起**：`showAppToast`（`base.js:132`）固定同一坐标、无队列、无上限，连续操作时提示互相覆盖。
2. **flash 5 秒后自动消失且无关闭按钮**（`base.js:406-414`）：错误信息可能被用户错过；建议手动关闭 + 按等级延长。
3. **没有"撤销"**：删除、移入回收站、批量改分类都是"确认即执行"。回收站既然存在，就没有理由不给 5 秒撤销。
4. **确认框有两种保险级别**：`data-confirm` 是统一入口，但页面内自建弹窗（`post.html:528/540`、`dashboard.html` 4 个）完全绕过它，行为不一致。
5. **空态文案分裂**：`index.html:149`、`search.html:97`、`infinite-scroll.js:418` 各写一套，且"去知识库写一篇"这类引导只在首页出现。

### 4.9 无障碍与键盘

1. **全站没有 `:focus-visible` 样式**（`static/css/*.css` 0 命中），同时有 7 处 `outline:none` 未补替代焦点样式 → 键盘用户看不到焦点在哪。
2. **无 skip link**：Tab 要穿过整个导航才能到正文。
3. **`showAppPrompt` 无 `role`/`aria-modal`**（`base.js:262-360`），与 confirm 的实现标准不一致。
4. **纯图标按钮缺可读名称**：导航搜索按钮是 `🔍`（`base.html:76`）、移动端工具栏部分按钮只有 `title`，`title` 对触屏无效。
5. **树控件无键盘模型**（`_tree.html:13`）：`role="tree"` + `←/→/Enter` 缺失。
6. **主题只挂在 `<body>`**（`base.html:51` 与 `style.css` 的 `.dark-theme`），没有 `color-scheme` → 暗色模式下原生 `select`、滚动条、日期控件仍是亮的；且系统主题变化后不会跟随。

---

## 五、三个平台级改造（收益最高）

### 5.1 反馈层：一个 toast 队列 + 一个 dialog 栈 + 撤销

```js
// static/js/ui.js —— 唯一入口，其余实现逐步下线
UI.toast(msg, { type: 'success'|'error'|'info', action?: { label, onClick }, duration? })
UI.confirm(msg, { destructive?, confirmText?, detail? })   // 返回 Promise<boolean>
UI.prompt(msg, { defaultValue?, placeholder? })            // 补 role/aria-modal/焦点环
UI.dialog(node, { onClose })                                // 统一 Esc + 焦点陷阱 + 遮罩关闭
```

- toast 垂直堆叠、最多 3 条、超出排队；带 `action` 的 toast 支持"撤销"。
- 所有弹层注册进同一个栈：**Esc 只关闭最上层**，杜绝 `shortcuts.js` 那种 `remove()`。
- 迁移顺序：`showAppToast`（被 12 个文件调用）→ `.copy-toast`/`.code-copy-toast` → `showNotification`。

### 5.2 状态约定：URL 管"别人能看见的状态"，storage 管"临时手感"

| 状态 | 归属 | 规则 |
|---|---|---|
| 列表筛选 / 排序 / 页码 | URL query | 可分享、可后退；无限滚动同步 `page` |
| 已加载条数 / 滚动位置 | `sessionStorage` + `history.scrollRestoration='manual'` | 返回列表恢复现场 |
| 后台批量选择 | `sessionStorage`（按筛选条件分 key） | 翻页不丢，清空有提示 |
| 树/分组折叠 | `localStorage`（按用户 + 空间） | 知识库树、后台侧边栏分组 |
| 编辑器草稿 | 已有实现（服务端 + localStorage） | 保持 |

### 5.3 快捷键与弹层注册表

```js
Keys.register('mod+k', fn, { when: 'global', description: '打开命令面板' })
Keys.register('mod+s', fn, { when: '#editor' })   // 只在对应上下文生效
```

- 禁止注册 `mod+r` / `mod+f` / `mod+n`（浏览器保留键）。
- 只在当前上下文注册，命令面板关闭即注销（解决 P0-1）。
- `Ctrl+/` 的帮助面板由注册表自动生成，不再手写清单——顺带修掉"阅读模式 R 没被列出"。

---

## 六、路线图

| 阶段 | 内容 | 验收 |
|---|---|---|
| 第 1 周（止血） | P0-1～P0-14 | 面板关闭后方向键/回车正常；Esc 不再破坏弹层；文档页树可展开；评论发出即可见；批量删除文案与实际一致；空正文保存有提示；保存失败不丢草稿；`Ctrl+S` 不会下架文章 |
| 第 2 周（移动端壳 + 反馈层） | 全站底部导航、返回键、恢复上一篇/下一篇；`UI.toast/confirm` 上线并替换 `showAppToast` | 手机在任意页面都能到达搜索/知识库/我的；连续 5 次操作提示不互相覆盖 |
| 第 3 周（状态与列表） | 无限滚动 URL + 滚动恢复；后台批量选择持久化、排序、sticky 批量栏；知识库树折叠记忆 | 从文章返回首页仍在原位置；翻页后选择仍在 |
| 第 4 周（搜索与知识库） | 搜索页即搜 + 键盘导航 + 空态；文档页"下一篇/子文档"；回顾页逐条节奏 | 搜索从输入到结果 ≤ 1 次交互；文档可以连续读下去 |
| 持续 | 无障碍：`:focus-visible`、skip link、树 `role`、`color-scheme` | 全站 Tab 可见焦点；axe 无 landmark/tree 类错误 |

---

## 七、问题索引（按文件)

| 文件 | 相关问题 |
|---|---|
| `templates/base.html` | 2.4 移动端壳、P0-7、`prompt` 无障碍、图标按钮名称 |
| `templates/post.html` | P0-6、P0-7、4.2 阅读页全部 |
| `templates/index.html` | P0-9、4.3 |
| `templates/admin/dashboard.html` | P0-5、P0-8、4.6-1~5 |
| `templates/knowledge/_tree.html` | P0-4、4.7-1~3 |
| `static/js/command-palette.js` | P0-1、P0-2、4.4-1 |
| `static/js/shortcuts.js` | P0-2、P0-3、5.3 |
| `static/js/infinite-scroll.js` | P0-9、P0-10、4.3 |
| `static/js/knowledge-toc.js` | P0-4 |
| `static/js/base.js` | 2.1、4.8 |
| `static/js/enhancements.js` | 2.2、4.2-6、4.8 |
| `templates/admin/editor.html` | P0-11、P0-14、4.5-1/5/7/9/10 |
| `static/js/editor.js` | P0-11、P0-12、4.5-1/6 |
| `static/js/editor-workbench.js` | 4.5-2/3 |
| `static/js/draft-sync.js` | P0-14、4.5-4 |
| `frontend/src/KbEditorApp.tsx` | 4.5-8 |
| `static/css/style.css` | 2.2 滚动、4.9 焦点 |
| `templates/search.html` | 4.4-3~4 |
