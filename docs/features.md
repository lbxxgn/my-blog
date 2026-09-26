# 功能总览（Feature Catalog）

**适用版本**: 2026-09
**最后更新**: 2026-09-26

本文档是系统的完整功能清单，按模块整理，标注**访问入口**与**使用前置条件**，方便你发现尚未用起来的能力。

**图例**
- 🔧 = 需要先配置才能使用（AI Key / Embedding / HTTPS 等，见文末「配置前置」）
- ⭐ = 容易被忽略、值得一试
- 路径均为站点相对路径

---

## 一、内容创作与发布

| 功能 | 入口 | 说明 |
|---|---|---|
| 博客文章 | `/admin/new`、`/admin/edit/<id>` | Quill 富文本编辑器，支持粘贴保留格式、代码块、表格 |
| 笔记（note） | 新建时选「笔记」 | 轻量便签式内容，与文章混排在首页 |
| 笔记转文章 | 文章管理「转文章」 | 把 note 升级为正式文章 |
| 访问控制 | 编辑页 | 公开 / 登录可见 / 密码保护 / 私密 四档 |
| 草稿 ⭐ | 编辑页「保存草稿」 | 多设备草稿自动同步与冲突检测（`/api/drafts`） |
| 文章归档 | `/archive` | 按最近 N 天 / 年份 / 月份筛选 |
| 分类页 | `/category/<id>` | 分类聚合 |
| 标签页 | `/tags`、`/tag/<id>` | 标签云与标签文章列表 |
| 作者页 | `/author/<id>` | 按作者聚合 |
| 评论 | 文章页底部 | 支持后台可见性开关 |
| 发布防重 | — | 60 秒内相同标题+内容自动去重，避免重复提交 |
| 知识沉淀 | 文章页「沉淀到知识库」 | 把文章转成知识库文档（`/post/<id>/precipitate`） |
| 导入 | `/admin/import` | ⭐ 支持 JSON / Markdown 批量导入 |
| 导出 | `/admin/export` | ⭐ Markdown / JSON，打包为 ZIP 下载 |

## 二、AI 能力 🔧

在后台 **AI 设置**（`/admin/ai/configure`）配置提供商与 Key 后可用。

- **提供商**：阿里百炼（通义千问）/ DeepSeek / 自定义 OpenAI 兼容接口
- ⭐ **标签生成**：自动为文章生成相关标签
- ⭐ **摘要生成**：一键生成文章摘要
- ⭐ **标题建议**
- ⭐ **AI 续写**：按上下文续写
- ⭐ **内容整理 / 结构重排**：重整段落结构与表达
- ⭐ **相关推荐**：基于内容推荐相关文章
- ⭐ **AI 导师点评**：为文章生成点评
- ⭐ **卡片合并**：把多张卡片手动或 AI 合并成文章
- ⭐ **AI 历史与用量**：`/admin/ai/history`

## 三、搜索

| 功能 | 入口 | 说明 |
|---|---|---|
| 全文搜索 | `/search` | SQLite FTS5 关键词检索 |
| 统一搜索 API | `GET /api/search/all` | 跨 文章 / 卡片 / 知识文档 / 网页批注 分组返回 |
| 语义搜索 🔧⭐ | `/search?source=semantic&q=` | 按语义相似度排序，结果带相似度徽标 |
| 命令面板 ⭐ | 桌面 `Ctrl/⌘+K` | 跨库搜索 + 快捷动作（写文章 / 写文档 / 快速记录 / 去回顾 / 切主题） |

## 四、知识管理

### 知识库空间 `/knowledge`
- 分类目录树 + 文档，目录支持拖拽排序
- 新版 **React + BlockNote** 编辑器；右侧栏四个面板：**AI / 元信息 / 🔗相关 / 目录**
- 文档自动保存、图片上传、草稿
- 文档搜索：`/knowledge/search`
- 卡片归档为文档：`/knowledge/card/<id>/archive`

### 卡片 / 想法 `/knowledge_base`
- 卡片状态：想法 / 孵化中 / 草稿 / 已发布
- ⭐ **网页批注（annotations）**：采集网页时连同高亮一起保存
- **卡片 → 文章**、**文章 → 知识库文档**
- **卡片合并**：手动或 AI 合并（`/api/cards/merge`、`/api/cards/ai-merge`）

### 快捷捕捉 `/quick-capture`
- 大号输入框，一键「存为卡片」/「存为快速记事」，保存后清空、适合连续录入
- ⭐ **语音速记**：麦克风按钮，浏览器 Web Speech API 实时转文字（Chrome/Edge/Safari）
- ⭐ **PWA 分享直达**：手机「分享」→ 你的博客 → 直达本页，标题/正文/链接自动预填（🔧 需 HTTPS）

## 五、回顾与统计 `/review` ⭐

| 模块 | 说明 |
|---|---|
| 写作热力图 | GitHub 风格近 53 周热力图，5 档强度；含连续记录天数 / 总量 / 活跃天数 |
| 那年今日 | 历年今天发布的内容（按本地时区月日匹配） |
| 随机漫步 | 随机抽取 5 张卡片，「换一批」重抽 |
| 每周 AI 回顾 🔧 | 汇总近 7 天写作活动 + 积压想法 + 超期孵化卡片，生成周报文档 |

- 首页侧边栏另有「那年今日」小组件
- 每周回顾可**手动生成**，也可用服务器 crontab 自动：`flask weekly-review`（每周一）

## 六、媒体处理

- 图片上传：支持 **HEIC/HEIF**（iPhone 直传）
- 自动压缩 + 多尺寸：`thumbnail(150) / medium(600) / large(1200) / feed`，统一转 **WebP**
- 文章图片**灯箱**查看、代码块**一键复制**
- ⭐ 图片清理工具（CLI）：`python backend/image_cleanup_tool.py` 检查/清理失效图片
- 站点自定义图标（favicon / iOS 主屏 / PWA）：`/admin/site`

## 七、用户、认证与安全

- **多用户 + 角色**：`admin` / `editor` / `author`
- 用户管理：`/admin/users`
- ⭐ **Passkey / WebAuthn**：Face ID / Touch ID 免密登录（🔧 需 HTTPS）
- ⭐ **受信任设备记住登录**（默认 90 天）
- 修改密码：`/change-password`
- ⭐ **API Key**：供浏览器扩展调用（生成脚本见文末）
- 安全：CSRF、速率限制、CSP、HttpOnly / SameSite Cookie

## 八、采集与集成

- **浏览器扩展**（Chrome/Edge）/ **Safari 扩展**：一键采集网页 → 卡片，可加标签/笔记，保存高亮批注
- **PWA**：可「添加到主屏幕」，支持系统分享目标（🔧 需 HTTPS）
- **分享**：分享按钮 + 二维码（`/api/share/qrcode`）

## 九、个性化与体验

- 暗色模式、响应式布局
- **移动端**：底部导航（首页/发现/+/文章/我的）、下拉刷新、无限滚动、移动端专属投稿面板与编辑器
- 阅读进度条、滚动动画、图片懒加载
- **全站键盘快捷键**（`Ctrl/⌘+/` 查看帮助）；完整列表见文末

## 十、后台管理 `/admin`

- 仪表盘、文章 / 分类 / 标签 / 评论管理
- ⭐ **批量操作**：批量改分类 / 删除 / 发布 / 加标签 / 改访问权限
- 导入 / 导出（JSON / Markdown）
- 用户管理、站点图标设置
- AI 设置（`/admin/ai/configure`）、AI 历史（`/admin/ai/history`）

## 十一、运维与部署

- 数据库迁移运行器：`python -m backend.migrations`（`status` 查看状态）
- 运维脚本：
  - `scripts/start.sh` 启动 · `scripts/install-service.sh` 装 systemd
  - `scripts/upgrade.sh` 升级 · `scripts/rollback.sh` 回滚 · `scripts/verify_upgrade.sh` 校验
  - `scripts/generate_manifest.py` 生成静态资源清单
- HTTPS 方案：
  - `scripts/setup-https-selfsigned.sh`：IP + 自签证书（大陆云、免域名备案）
  - `scripts/setup-https-sslip.sh`：sslip.io + Let's Encrypt（海外）
  - `scripts/cleanup-https-sslip.sh`：清理 Let's Encrypt 残留
- 诊断：`python scripts/diagnostics/api_perf_check.py`
- 静态资源版本管理 + manifest（`backend/utils/asset_version.py`）

---

## 附一：键盘快捷键

| 快捷键 | 作用 | 生效页面 |
|---|---|---|
| `Ctrl/⌘ + K` | 打开命令面板 | 全站 |
| `Ctrl/⌘ + /` | 快捷键帮助 | 全站 |
| `Ctrl/⌘ + N` | 新建文章 | 首页 / 后台 |
| `Ctrl/⌘ + Shift + N` | 快速记事 | 全站 |
| `ESC` | 关闭弹窗 / 退出编辑器 | 全站 |
| `Ctrl/⌘ + S` | 保存 / 快速保存 | 编辑器 / 快速记事 |
| `Ctrl/⌘ + Shift + S` | 保存草稿 | 编辑器 |
| `Ctrl/⌘ + P` | 切换预览 | 编辑器 |
| `Ctrl/⌘ + Shift + T` | AI 生成标签 | 编辑器 |
| `Ctrl/⌘ + B` / `I` | 加粗 / 斜体 | 编辑器 |
| `Ctrl/⌘ + D` | 插入日期 | 编辑器 |
| `Ctrl/⌘ + Shift + K` | 插入代码 | 编辑器 |
| `Ctrl/⌘ + Alt + L` / `O` | 无序 / 有序列表 | 编辑器 |
| `Ctrl/⌘ + R` | 刷新内容 | 后台 / 时间线 |

## 附二：配置前置

| 能力 | 前置 | 入口 |
|---|---|---|
| AI 标签/摘要/续写/推荐/点评/合并 | 配置 chat 提供商 + API Key | 后台 AI 设置 `/admin/ai/configure` |
| 语义搜索 / 编辑器「相关」 | 配置 Embedding + 重建向量索引 | AI 设置「Embedding 服务」区块 |
| Passkey / PWA / 分享目标 | 站点运行在 **HTTPS** | 见 `DEPLOYMENT.md` HTTPS 章节 |
| 浏览器 / Safari 扩展 | 生成 API Key 并在扩展中填写 | `python browser-extension/generate-api-key.py` |
| 每周 AI 回顾自动执行 | crontab 定时 | `flask weekly-review` |

> Embedding 配置与排查详见 [`personal-features.md`](personal-features.md)。

## 附三：入口速查

| 路径 | 页面 |
|---|---|
| `/` | 首页（文章流，无限滚动） |
| `/post/<id>` | 文章详情 |
| `/archive` | 归档 |
| `/search` | 搜索（关键词 / 语义） |
| `/review` | 回顾页 |
| `/knowledge` | 知识库空间 |
| `/quick-capture` | 快捷捕捉 |
| `/admin` | 后台仪表盘 |
| `/admin/export` `/admin/import` | 导出 / 导入 |
| `/admin/ai/configure` `/admin/ai/history` | AI 设置 / 历史 |
| `/admin/site` | 站点图标设置 |
| `/login` `/change-password` | 登录 / 改密 |
