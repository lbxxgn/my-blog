# 工程化优化待办（2026-11）

本文记录 2026-11 审计后**尚未实施**的工程性优化项，供后续按需挑选。
已完成部分见「本次已修复」一节。

## 本次已修复（供对照）

- 卡片合并写 IDOR、语义检索越权、session 角色不刷新、媒体库删除权限、示例默认密码。
- CSRF 豁免端点校验用户状态、`TRUST_PROXY_HEADERS` 支持、HTTPS 未启用告警、AI 请求超时/重试。
- 新增 `/healthz`、`/readyz`。
- 日志文件单一写入者；systemd 示例改用 journald。
- 新增 `scripts/backup.sh`（SQLite Online Backup + 完整性校验）。
- 修复 drafts 遗留唯一索引（迁移 014）。
- 测试库改为 `init_db + 迁移` 生成，测试不再手写 DDL。
- CI 增加前端构建、依赖缓存、依赖审计；拆分 dev 依赖；补 ruff 配置；pytest 不再强制覆盖率。

---

## 一、安全（建议优先）

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|
| SEC-1 | 高 | 登录无限流/失败锁定，可撞库 | `backend/routes/auth.py:194`、`backend/app.py:334` | 对 `auth.login` 按 IP + 用户名双维度限流，失败退避/短期锁定 | 连续失败触发 429/锁定；正常登录不受影响 |
| SEC-2 | 高 | 限流 `memory://`，多 worker 各自计数 | `backend/app.py:334`、`simple-blog.service.example:60` | 生产用 Redis 存储，或固定 `workers=1` | 多 worker 下限流计数一致 |
| SEC-3 | 中 | CSP 含 `unsafe-inline`，iframe 允许任意 https | `backend/app.py:295`、`backend/utils/markdown_renderer.py:36` | 迁移到 nonce/hash；iframe 域名白名单 + `sandbox` | CSP 无 `unsafe-inline`；外部 iframe 受限 |
| SEC-4 | 中 | SSRF 防护存在 DNS 重绑定窗口 | `backend/ai_services/url_guard.py:66`、`openai_compatible.py:80` | 连接层固定已校验 IP，或出站代理白名单 | 私网/元数据地址不可达 |
| SEC-5 | 中 | CSRF 豁免端点仍接受 session，未校验 Origin | `backend/auth_decorators.py:52`、`backend/app.py:589` | 豁免端点只接受 API Key，或校验 Origin/Referer | 跨站请求无法触发状态变更 |
| SEC-6 | 中 | `SESSION_COOKIE_SECURE` 依赖手工 `FORCE_HTTPS` | `backend/config.py:174`、`.env.example:42` | 生产默认 Secure，按 `X-Forwarded-Proto` 判断；启动强制校验 | 生产 HTTPS 下 Cookie 必带 Secure |
| SEC-7 | 中 | Pillow 缺失时上传退化为扩展名校验；大图全量读内存 | `backend/routes/admin/media.py:50`、`knowledge.py:450` | Pillow 改硬依赖；流式落盘；`MAX_IMAGE_PIXELS` 限制 | 无 Pillow 拒绝上传；超大图被拒绝 |
| SEC-8 | 低 | 媒体引用判断用 `LIKE '%name%'`，可能误判 | `backend/routes/admin/media.py:318` | 建媒体引用关联表或精确匹配 URL | 引用判断可精确回滚 |
| SEC-9 | 低 | 登出是 GET，可被 `<img>` 触发 | `backend/routes/auth.py:231` | 改 POST + CSRF token | 登出仅接受 POST |
| SEC-10 | 低 | 依赖审计仅非阻塞，无 Dependabot/Renovate | `.github/workflows/ci.yml` | 启用 Dependabot/Renovate，修复后把 `pip-audit` 设为阻塞 | 高危依赖升级有自动 PR |

## 二、后端架构与数据层

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|
| BE-1 | 中 | 无 app factory；导入即启动调度器、做配置校验 | `backend/app.py:115,1133` | 引入 `create_app(config)`，副作用移到启动入口 | 测试可创建多个隔离 app |
| BE-2 | 中 | `models` 与 `backend.models` 双身份，可能重复加载 | `backend/app.py:44`、文档 `from backend.models` | 统一 `backend.*` 绝对导入，移除 `sys.path` hack | 全仓库只有一种导入路径 |
| BE-3 | 中 | 数据库连接/事务管理不统一，异常路径可能泄漏 | `get_db_connection` 125 处 vs `get_db_context` 77 处；`models/cards.py` 已修一处 | 全面改用 `get_db_context`，禁止裸 `commit/close` | 新增代码统一上下文管理器 |
| BE-4 | 中 | `init_db` 与迁移双份 schema；gunicorn 启动不自动迁移 | `backend/models/db.py:110`、`backend/migrations/` | 迁移作为唯一 schema 来源；启动/升级脚本自动执行 | 空库 + 旧库均可自动升级 |
| BE-5 | 中 | 后台任务为进程内 daemon 线程，多 worker 不一致、重启丢任务 | `backend/routes/review.py:202`、`admin/posts.py:298`、`services/backup.py:387` | 外置 RQ/Celery；或至少持久化任务 + 幂等 + 重试 | 重启不丢任务；多 worker 只执行一次 |
| BE-6 | 中 | 语义检索全表加载向量到 Python，O(N) | `backend/models/embeddings.py:145` | 引入向量索引/外部向量库，或先加缓存与分页 | 数据量增长后 P95 可控 |
| BE-7 | 低 | `app.py` 保留 61 个路由，其中大量兼容别名 | `backend/app.py:688-960` | 模板改用 blueprint endpoint，删除别名 | 删除后模板/旧链接仍可访问（301） |
| BE-8 | 低 | 日志无 request id/结构化字段 | `backend/logger.py` | JSON 日志 + `X-Request-ID` + 用户/耗时字段 | 可按请求串联排障 |
| BE-9 | 低 | CGI 时代的调试 `print` 仍散落 | `backend/routes/ai/generation.py:102`、导入/迁移脚本 | CLI 保留 print，Web 路径改 logger | Web 请求无 print 输出 |

## 三、测试与 CI

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|
| QA-1 | 中 | E2E 未进 CI、依赖 Chrome、无法自动跑 | `tests/e2e_kb_editor.py`、`pytest.ini` | 迁 Playwright，放 `tests/e2e/`，CI 起服务后执行 | PR 自动跑核心编辑流程 |
| QA-2 | 中 | 迁移只验证“能跑”，无 schema 快照/回滚测试 | `tests/conftest.py` | 加 schema 快照对比；关键迁移加 down/回滚演练 | 迁移差异会在 CI 报警 |
| QA-3 | 中 | 测试未分层，固定 `sleep` 易 flaky | `tests/test_embeddings.py:66`、`test_ai_title_generation.py` | 用 `Event`/轮询；启用 `slow/integration` marker 分档 | CI 可分 unit/integration 两档 |
| QA-4 | 低 | 覆盖率已恢复显式执行，但门槛仅 40% | `Makefile:coverage` | 逐步提升到 60%+，按模块设阈值 | 覆盖率下降会失败 |
| QA-5 | 低 | 前端零测试 | `frontend/package.json:10` | 引入 Vitest + 关键组件测试 | `npm test` 可在 CI 运行 |
| QA-6 | 低 | `pytest-randomly`/xdist 未启用，顺序依赖不可见 | `tests/conftest.py` | 引入随机顺序测试，修复暴露的全局状态 | 随机顺序稳定通过 |

## 四、前端

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|
| FE-1 | 高 | Quill 与 BlockNote 两套编辑器并存，上传/草稿/AI 逻辑重复 | `templates/admin/editor.html`、`static/js/editor.js`、`frontend/src` | 明确唯一编辑器；先抽共享上传/草稿/AI 服务 | 同一功能只维护一份 |
| FE-2 | 高 | 知识库上传绕过图片优化，原图直接进正文 | `backend/routes/knowledge.py:428-494`、`routes/admin/media.py:121` | 统一上传服务，统一入队优化 + 懒加载 | 知识库图片同样生成 WebP/缩略图 |
| FE-3 | 中 | 构建产物入库、CI 已构建但不校验产物一致；`npm run dev` 不可用 | `static/frontend/`、`frontend/vite.config.ts` | 构建产物移出 Git；CI 校验；补 `server.proxy` | 源码改动未构建会被 CI 拦截 |
| FE-4 | 中 | 模板巨石与内联 CSS/JS 多 | `templates/admin/editor.html` 1706 行、`post.html` 973 行 | 抽页面级 CSS/JS 与 Jinja 宏 | 单模板 < 600 行，内联样式清零 |
| FE-5 | 中 | CSS 重复/覆盖严重 | `style.css` 与 `enhancements.css` 91 个重复选择器 | 按 tokens/base/components/pages 分层合并 | 无重复基础组件规则 |
| FE-6 | 中 | 静态资源版本化不一致，手工 `?v=` 不会更新 | `templates/post.html:8,648`、`app.py:145` | 统一走版本清单；加模板测试禁止无版本 js/css | 发布后所有资源自动失效 |
| FE-7 | 中 | `fetch` 无统一超时/取消/`response.ok` 校验 | `static/js/infinite-scroll.js:150`、`draft-sync.js:8` | 抽统一 `request()` 封装 | 401/500 有统一提示，分页可取消 |
| FE-8 | 低 | a11y/i18n 无基线，动态图片 alt 为空 | `base.html:571`、`infinite-scroll.js:315` | skip link、aria-label、alt 透传；按需引入 Babel | axe 基础检查通过 |
| FE-9 | 低 | 调试钩子暴露到生产 | `frontend/src/KbEditorApp.tsx:207` | 仅 `import.meta.env.DEV` 挂载 | 生产包无调试全局变量 |

## 五、仓库与运维

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|
| OPS-1 | 中 | `static/uploads` 用户图片与 `static/frontend` 构建产物仍被 Git 跟踪 | `git ls-files static/uploads` 9 个、`static/frontend` 23 个 | `git rm --cached`，补 ignore；必要时 `git filter-repo` 清理历史 | 仓库不再包含用户数据/构建产物 |
| OPS-2 | 低 | 工作区大文件堆积 | `exports` 153M、`backups` 360M、`static/uploads` 195M | 定期清理；CI 加“已跟踪但被忽略文件”检查 | clone/磁盘占用可控 |
| OPS-3 | 中 | SQLite 单写 + 2 worker，长期扩展性有限 | `simple-blog.service.example:60`、`models/db.py` | 评估迁移 PostgreSQL；或明确单 worker 部署 | 并发写入无锁等待 |
| OPS-4 | 低 | 无 Docker/容器化方案 | README 已注明 | 提供 Dockerfile + compose（含备份卷） | 一条命令可起完整服务 |
| OPS-5 | 低 | Nginx 无边缘限流、上传上限 4g、HSTS 注释 | `nginx.conf.example:181,228` | 加 `limit_req`、收紧上传、HTTPS 后启用 HSTS | 边缘层可挡暴力请求 |
| OPS-6 | 低 | systemd 安全加固有限 | `simple-blog.service.example` | 增加 `ProtectSystem`、`ReadWritePaths`、`PrivateDevices` | `systemd-analyze security` 评分提升 |
| OPS-7 | 低 | 备份缺恢复演练/加密/异地 | `scripts/backup.sh` | 增加恢复脚本、校验清单、加密与异地同步 | 每季度可完成一次恢复演练 |

## 六、文档

| ID | 优先级 | 问题 | 建议 |
|---|---|---|---|
| DOC-1 | 低 | 历史性能报告声称存在 `bundle.css/bundle.js`，实际不存在 | 归档并标注过期，或删除 |
| DOC-2 | 低 | 上传限制注释与代码不一致（5MB vs 50MB） | 由配置常量生成文档 |
| DOC-3 | 低 | 测试数量靠手写维护 | 加脚本自动更新 README/测试文档 |

## 建议选择顺序

1. **SEC-1 / SEC-2**：登录限流与共享存储，投入小、收益直接。
2. **FE-1 / FE-2**：统一上传与编辑器，避免继续双轨复制。
3. **BE-1 / BE-3 / BE-4**：app factory + 统一事务 + 迁移唯一化，为后续重构铺路。
4. **QA-1 / QA-2**：E2E 与迁移测试，防止回归。
5. **OPS-1**：清理仓库中的用户数据与构建产物。
