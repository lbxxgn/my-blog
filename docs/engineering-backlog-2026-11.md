# 工程化优化待办（2026-11）

本文记录 2026-11 审计后**尚未实施**的工程性优化项，供后续按需挑选。
已完成部分见「本次已修复」一节。

> 说明：证据列中的行号会随代码移动而失效，排查时以文件与函数名为准。

## 本次已修复（供对照）

- 卡片合并写 IDOR、语义检索越权、session 角色不刷新、媒体库删除权限、示例默认密码。
- CSRF 豁免端点校验用户状态、`TRUST_PROXY_HEADERS` 支持、HTTPS 未启用告警、AI 请求超时/重试。
- 新增 `/healthz`、`/readyz`。
- 日志文件单一写入者；systemd 示例改用 journald。
- 新增 `scripts/backup.sh`（SQLite Online Backup + 完整性校验）。
- 修复 drafts 遗留唯一索引（迁移 014）。
- 测试库改为 `init_db + 迁移` 生成，测试不再手写 DDL。
- 移除 40 个重复 legacy 别名路由，模板统一使用 blueprint endpoint；保留 12 个旧客户端路径入口。
- 导入统一为 `backend.*`，移除 `backend/` 的 `sys.path` 注入，消除 `models` / `backend.models` 双模块身份。
- 引入 `create_app(config_overrides=None)`，保留模块级 `app = create_app()` 兼容 gunicorn 与测试；扩展改为 `init_app`。
- 新增基线迁移 000 + `AUTO_MIGRATE` 启动自动迁移；后台任务落库（review/ai title）；embedding 增加进程内向量缓存；legacy 路径迁移到独立 blueprint。
- 静态资源版本化补齐；E2E 接入 CI；schema 快照测试；测试 marker 分层；构建产物/用户上传移出 Git；SQLite 示例收敛为单 worker。
- CI 增加前端构建、依赖缓存、依赖审计、E2E；拆分 dev 依赖；补 ruff 配置；pytest 不再强制覆盖率。
- 生产部署统一为 `gunicorn --workers 1`（SQLite 单写 + `memory://` 限流），并在安装脚本/示例/文档中固定该值。
- 2026-11 第二批：基线迁移 000、`AUTO_MIGRATE`、`background_tasks` 持久化队列（review / AI 标题 / embedding）、embedding 进程内缓存、legacy 蓝图、schema 快照、E2E 接入 CI、模板内联 CSS 抽出、静态资源版本化检查、构建产物/上传移出 Git、单 worker 收敛、`scripts/build-frontend.sh`。

---

## 一、安全（建议优先）

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|
| SEC-1 | 高 | 登录无限流/失败锁定，可撞库 | `backend/routes/auth.py`（login 未挂限流）、`backend/app.py`（`app_limiter`） | 对 `auth.login` 按 IP + 用户名双维度限流，失败退避/短期锁定 | 连续失败触发 429/锁定；正常登录不受影响 |
| SEC-3 | 中 | CSP 含 `unsafe-inline`，iframe 允许任意 https | `backend/app.py`（CSP after_request）、`backend/utils/markdown_renderer.py` | 迁移到 nonce/hash；iframe 域名白名单 + `sandbox` | CSP 无 `unsafe-inline`；外部 iframe 受限 |
| SEC-4 | 中 | SSRF 防护存在 DNS 重绑定窗口 | `backend/ai_services/url_guard.py`、`openai_compatible.py` | 连接层固定已校验 IP，或出站代理白名单 | 私网/元数据地址不可达 |
| SEC-5 | 中 | CSRF 豁免端点仍接受 session，未校验 Origin | `backend/auth_decorators.py`、`backend/app.py` | 豁免端点只接受 API Key，或校验 Origin/Referer | 跨站请求无法触发状态变更 |
| SEC-6 | 中 | `SESSION_COOKIE_SECURE` 依赖手工 `FORCE_HTTPS` | `backend/config.py`（`FORCE_HTTPS`）、`.env.example` | 生产默认 Secure，按 `X-Forwarded-Proto` 判断；启动强制校验 | 生产 HTTPS 下 Cookie 必带 Secure |
| SEC-7 | 中 | Pillow 缺失时上传退化为扩展名校验；大图全量读内存 | `backend/routes/admin/media.py`、`backend/routes/knowledge.py` | Pillow 改硬依赖；流式落盘；`MAX_IMAGE_PIXELS` 限制 | 无 Pillow 拒绝上传；超大图被拒绝 |
| SEC-8 | 低 | 媒体引用判断用 `LIKE '%name%'`，可能误判 | `backend/routes/admin/media.py` | 建媒体引用关联表或精确匹配 URL | 引用判断可精确回滚 |
| SEC-9 | 低 | 登出是 GET，可被 `<img>` 触发 | `backend/routes/auth.py`（`/logout`） | 改 POST + CSRF token | 登出仅接受 POST |
| SEC-10 | 低 | 依赖审计仅非阻塞，无 Dependabot/Renovate | `.github/workflows/ci.yml` | 启用 Dependabot/Renovate，修复后把 `pip-audit` 设为阻塞 | 高危依赖升级有自动 PR |

## 二、后端架构与数据层

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|


| BE-6 | 中 | embedding 已加进程内缓存，但仍是线性扫描 | `backend/models/embeddings.py` | 引入 sqlite-vec/外部向量库实现 ANN | 数据量增长后 P95 可控 |
| BE-7 | 低 | legacy 路径已移入 blueprint，但仍为视图包装 | `backend/routes/legacy.py` | 更新浏览器插件后改为 301/307 或删除 | 旧路径仅保留重定向 |
| BE-8 | 低 | 日志无 request id/结构化字段 | `backend/logger.py` | JSON 日志 + `X-Request-ID` + 用户/耗时字段 | 可按请求串联排障 |
| BE-9 | 低 | CGI 时代的调试 `print` 仍散落 | `backend/routes/ai/generation.py`、导入/迁移脚本 | CLI 保留 print，Web 路径改 logger | Web 请求无 print 输出 |

## 三、测试与 CI

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|
| QA-4 | 低 | 覆盖率已恢复显式执行，但门槛仅 40% | `Makefile`（`coverage` 目标） | 逐步提升到 60%+，按模块设阈值 | 覆盖率下降会失败 |
| QA-5 | 低 | 前端零测试 | `frontend/package.json` | 引入 Vitest + 关键组件测试 | `npm test` 可在 CI 运行 |
| QA-6 | 低 | `pytest-randomly`/xdist 未启用，顺序依赖不可见 | `tests/conftest.py` | 引入随机顺序测试，修复暴露的全局状态 | 随机顺序稳定通过 |

## 四、前端

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|
| FE-1 | 高 | Quill 与 BlockNote 两套编辑器并存，上传/草稿/AI 逻辑重复 | `templates/admin/editor.html`、`static/js/editor.js`、`frontend/src` | 明确唯一编辑器；先抽共享上传/草稿/AI 服务 | 同一功能只维护一份 |
| FE-2 | 高 | 知识库上传绕过图片优化，原图直接进正文 | `backend/routes/knowledge.py`（`upload_image`）、`backend/routes/admin/media.py` | 统一上传服务，统一入队优化 + 懒加载 | 知识库图片同样生成 WebP/缩略图 |
| FE-4 | 低 | 内联 CSS 已抽出；post 页仍有内联 JS | `templates/post.html` | 继续抽页面级 JS 与 Jinja 宏 | 内联脚本清零 |
| FE-5 | 中 | CSS 重复/覆盖严重 | `style.css` 与 `enhancements.css` 91 个重复选择器 | 按 tokens/base/components/pages 分层合并 | 无重复基础组件规则 |
| FE-7 | 中 | `fetch` 无统一超时/取消/`response.ok` 校验 | `static/js/infinite-scroll.js`、`static/js/draft-sync.js` | 抽统一 `request()` 封装 | 401/500 有统一提示，分页可取消 |
| FE-8 | 低 | a11y/i18n 无基线，动态图片 alt 为空 | `templates/base.html`、`static/js/infinite-scroll.js` | skip link、aria-label、alt 透传；按需引入 Babel | axe 基础检查通过 |
| FE-9 | 低 | 调试钩子暴露到生产 | `frontend/src/KbEditorApp.tsx` | 仅 `import.meta.env.DEV` 挂载 | 生产包无调试全局变量 |

## 五、仓库与运维

| ID | 优先级 | 问题 | 证据 | 建议 | 验收标准 |
|---|---|---|---|---|---|
| OPS-2 | 低 | 工作区大文件堆积 | `exports`、`backups`、`static/uploads` 合计约 700MB | 定期清理；CI 加“已跟踪但被忽略文件”检查 | clone/磁盘占用可控 |
| OPS-4 | 低 | 无 Docker/容器化方案 | README 已注明 | 提供 Dockerfile + compose（含备份卷） | 一条命令可起完整服务 |
| OPS-5 | 低 | Nginx 无边缘限流、上传上限 4g、HSTS 注释 | `nginx.conf.example` | 加 `limit_req`、收紧上传、HTTPS 后启用 HSTS | 边缘层可挡暴力请求 |
| OPS-6 | 低 | systemd 安全加固有限 | `simple-blog.service.example` | 增加 `ProtectSystem`、`ReadWritePaths`、`PrivateDevices` | `systemd-analyze security` 评分提升 |
| OPS-7 | 低 | 备份缺恢复演练/加密/异地 | `scripts/backup.sh` | 增加恢复脚本、校验清单、加密与异地同步 | 每季度可完成一次恢复演练 |

## 六、文档

| ID | 优先级 | 问题 | 建议 |
|---|---|---|---|
| DOC-2 | 低 | 上传限制注释与代码不一致（5MB vs 50MB） | 由配置常量生成文档 |
| DOC-3 | 低 | 测试数量靠手写维护 | 加脚本自动更新 README/测试文档 |

## 建议选择顺序

1. **SEC-1**：登录限流与失败退避。
2. **FE-1 / FE-2**：统一上传与编辑器，避免继续双轨复制。
3. **BE-6**：embedding 向量检索改 ANN 索引。
4. **SEC-3 / SEC-4**：CSP 与 SSRF 加固。
5. **OPS-2 / OPS-5**：工作区清理与 Nginx 边缘防护。
