# 升级部署指南：个人效率功能版本（2026-09）

**适用版本**: commit `fb6c181`（`feat: 个人知识管理体验升级（9 项功能）`）
**最后更新**: 2026-09-25
**前置要求**: 已按 [部署指南](../DEPLOYMENT.md) 完成基础部署的旧版本

本指南说明如何升级到包含「命令面板 / 语义搜索 / 回顾页 / 快捷捕捉 / 语音速记」等 9 项个人效率功能的版本。功能使用说明见 [个人效率功能说明](personal-features.md)，API 明细见 [API 文档](api-documentation.md)（v2.4）。

---

## 📋 版本概述

| 类别 | 内容 |
|------|------|
| 搜索 | Cmd+K 命令面板、跨库统一搜索 API、语义搜索（embedding） |
| 写作辅助 | 两个编辑器的「相关卡片」语义推荐面板 |
| 回顾 | `/review` 页（写作热力图/那年今日/随机漫步）、每周 AI 回顾（CLI + crontab） |
| 输入 | `/quick-capture` 快捷捕捉、PWA 分享目标（share_target）、语音速记（Web Speech API） |
| 数据 | 迁移 009：`embeddings` 表 + users 表 4 个 embedding 配置列 |
| 依赖 | 新增 `numpy`（纯 wheel，无编译风险） |

**重要特性**：除 numpy 和迁移 009 外，所有功能开箱即用；语义搜索/相关卡片为可选能力（需在 AI 设置页配置 Embedding 后启用），不配置不影响任何现有功能。

---

## 🚀 升级步骤

### 方式一：自动升级（推荐）

`scripts/upgrade.sh` 已覆盖本版本全部升级动作（pip install、版本化迁移 `python -m backend.migrations`（含 009）、manifest 重生成、重启）：

```bash
chmod +x scripts/upgrade.sh scripts/verify_upgrade.sh
./scripts/upgrade.sh
./scripts/verify_upgrade.sh
```

### 方式二：手动升级

```bash
# 1. 备份（必做）
BACKUP_DIR="backups/upgrade_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp db/simple_blog.db "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"

# 2. 拉取代码
git fetch origin
git pull origin <你的分支>      # 本版本提交在 fix/ux-batch-1 分支，按你的仓库实际分支调整

# 3. 更新依赖（新增 numpy）
source .venv/bin/activate
pip install -r requirements.txt

# 4. 数据库迁移（幂等，含 009_embeddings）
export DATABASE_URL="sqlite:///db/simple_blog.db"   # 或来自 .env
python -m backend.migrations
python -m backend.migrations status                 # 验证：009_embeddings 显示 ✅

# 5. 前端构建（git 已包含构建产物 static/frontend/，仅当自行修改前端源码时需要）
cd frontend && npm install && npm run build && cd ..

# 6. 静态资源清单（新增 command-palette/review/quick-capture 等 JS/CSS）
python scripts/generate_manifest.py

# 7. 重启服务
sudo systemctl restart simple-blog
```

> 注意：`python -m backend.migrations` 与旧文档中逐个执行 `python3 backend/migrations/migrate_xxx.py` 的方式不同——本项目已切换到版本化迁移器，**不要再手动跑旧脚本**，重复执行旧脚本可能造成混乱。

---

## ⚙️ 部署后配置

### 必做（1 项）

**验证迁移与依赖**

```bash
source .venv/bin/activate
python -c "import numpy; print(numpy.__version__)"   # 确认 numpy 可用
python -m backend.migrations status                  # 确认 009 已应用
```

### 可选（2 项）

**1. 开启语义能力（语义搜索 + 相关卡片）**

1. 到 https://siliconflow.cn 注册免费 API Key
2. 登录博客 → 后台「AI 设置」→「Embedding 服务」：启用、填 Key（Base URL 与模型保持默认）
3. 点「测试连接」→ 通过后点「重建向量索引」（异步回填存量，几百篇约几分钟，期间服务正常使用）

**2. 每周 AI 回顾定时任务**

```bash
crontab -e
# 每周一 08:05 生成（路径换成实际部署路径）
5 8 * * 1 cd /path/to/my-blog && .venv/bin/flask weekly-review >> logs/weekly_review.log 2>&1
```

CLI 幂等（同周重复执行返回 exists）。AI 未配置时会为第一个管理员生成纯统计版回顾。

---

## 🧪 升级验证

### 快速冒烟（2 分钟）

```bash
BASE="https://your-domain.com"   # 或 http://127.0.0.1:端口

curl -s -o /dev/null -w "%{http_code}\n" $BASE/                 # 200
curl -s -o /dev/null -w "%{http_code}\n" $BASE/review           # 302（未登录跳登录页）
curl -s -o /dev/null -w "%{http_code}\n" $BASE/api/search/all?q=x   # 401
curl -s -o /dev/null -w "%{http_code}\n" $BASE/sw.js            # 200
curl -s $BASE/static/site.webmanifest | grep -o share_target    # 应有输出
```

登录后检查：

- [ ] 桌面端按 `Ctrl+K` 弹出命令面板，输入关键词能搜到文章/卡片
- [ ] 导航栏出现「回顾」「快捷捕捉」
- [ ] `/review` 显示热力图、那年今日、随机漫步
- [ ] 知识库编辑器右侧有「🔗 相关」tab（配置 embedding 后写 200+ 字有推荐）
- [ ] AI 设置页有「Embedding 服务」区块
- [ ] 手机安装 PWA 后系统分享菜单能直达快捷捕捉页

### 测试与构建（源码部署机）

```bash
source .venv/bin/activate
python -m pytest tests/ -q --ignore=tests/visual    # 期望 368 passed
python -m backend.migrations status
```

---

## 🔄 回滚

本版本的迁移 009 为**纯新增**（新表 + users 新列），旧代码完全不读这些对象，因此回滚**无需恢复数据库**：

```bash
sudo systemctl stop simple-blog
git reset --hard <上一个 commit>        # 如回滚本提交：git revert fb6c181
# requirements 里的 numpy 可留可删，旧代码不依赖
sudo systemctl start simple-blog
```

若升级中执行过「重建向量索引」，回滚后 `embeddings` 表残留数据无害；如确需清理：

```bash
sqlite3 db/simple_blog.db "DROP TABLE IF EXISTS embeddings;"
```

---

## 🐛 常见问题

### 1. `pip install` 安装 numpy 失败

服务器 pip 过旧或网络受限。升级 pip 后重试：`python -m pip install -U pip`，再 `pip install -r requirements.txt`。numpy 提供预编译 wheel，正常不需要编译工具链。

### 2. 语义搜索/相关面板提示「未配置 Embedding」

属于预期行为（功能默认关闭）。到「AI 设置 → Embedding 服务」配置并「测试连接」即可；若确认已配置仍提示，检查 `users.ai_embedding_enabled=1` 且密钥正确，服务日志会有 embedding 相关错误。

### 3. 「重建向量索引」后语义结果仍为空

任务异步执行。看日志确认 worker 没有静默跳过（未启用/未配置密钥时按设计跳过）。也可保存任意文章触发增量 embedding 验证链路。

### 4. `flask weekly-review` 报错或没有生成

`flask` 命令需要应用上下文与 `DATABASE_URL`：必须在项目根目录、虚拟环境激活状态下执行（crontab 示例已带 cd）。无任何用户配置 AI 时，仅第一个管理员会生成降级统计版；想生成 AI 版请先配置 AI 设置。

### 5. 手机「添加到主屏幕」后分享菜单里没有博客

两个前提：站点必须是 HTTPS；PWA 需完成安装（图标出现在主屏幕）。部分国产浏览器不支持 share_target，用 Chrome/Safari 验证。

### 6. 语音按钮置灰

浏览器不支持 Web Speech API（如部分安卓 WebView），换 Chrome/Edge/Safari 并授权麦克风。

### 7. 升级后静态 JS/CSS 404 或旧缓存

确认执行过 `python scripts/generate_manifest.py` 并重启；强制刷新（Ctrl+Shift+R）。`sw.js` 为纯透传，不会因缓存导致内容不更新。

---

## 📊 性能影响

| 项 | 影响 | 说明 |
|----|------|------|
| embedding 后台任务 | 保存文章/卡片时多一个线程池任务（max_workers=2），不阻塞请求 | API 调用失败静默跳过，不影响保存 |
| numpy | 进程内存 +约 30-50MB | 仅语义查询时计算 |
| 语义搜索响应 | 首次查询需调 embedding API（~300-500ms），之后纯本地余弦计算 | 个人数据规模下 <100ms |
| 每周回顾 | crontab 触发时一次 LLM 调用 | 对服务无常驻开销 |

---

## 📝 更新日志

- **2026-09-25**: 初版。对应 commit `fb6c181`，9 项个人效率功能 + 迁移 009 + numpy 依赖。
