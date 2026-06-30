# Simple Blog 启动指南

**版本**: 3.0
**更新日期**: 2026-06-28
**Python 要求**: 3.11+（推荐）

---

## 快速启动

### 1. 环境准备

#### 检查 Python 版本
```bash
python3 --version
# 推荐使用 Python 3.11 或更高版本
```

#### 安装依赖
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

所需依赖（详见 `requirements.txt`）：
- Flask 3.0+
- Flask-WTF
- Flask-Limiter
- bleach
- markdown2
- Pillow
- pytz
- python-dotenv
- webauthn

### 2. 设置环境变量

**必须设置的环境变量**：

```bash
export ADMIN_USERNAME="admin"           # 管理员用户名
export ADMIN_PASSWORD="AdminPass123!"   # 管理员密码（至少 10 位；建议 12 位以上，包含大小写字母和数字）
```

> 当前系统强制密码最小长度为 **10 位**，文档建议配置 **12 位或更长** 的强密码。

**可选环境变量**：

```bash
export DEBUG="False"                    # 生产环境设置为 False
export PORT="5001"                      # 应用端口（默认 5001，避免与 macOS AirPlay 冲突）
export SITE_NAME="我的博客"             # 网站名称
export SITE_DESCRIPTION="一个简单的博客系统"  # 网站描述
export SITE_AUTHOR="管理员"             # 网站作者
export FORCE_HTTPS="False"              # 是否强制 HTTPS（有 SSL 证书时设为 True）

# Passkey / WebAuthn
export PASSKEY_RP_NAME="Simple Blog"
export PASSKEY_RP_ID="your-domain.com"
export PASSKEY_ALLOWED_ORIGINS="https://your-domain.com"

# 设备记住时长
export REMEMBER_DEVICE_DAYS="90"

# 静态资源
export USE_MINIFIED_ASSETS="True"
# export ASSET_BUILD_VERSION=""

# AI 默认配置
export AI_DEFAULT_PROVIDER="openai"
export AI_DEFAULT_MODEL="gpt-3.5-turbo"
export AI_RATE_LIMIT_PER_HOUR="10"
export AI_CONTENT_MAX_LENGTH="500"
```

完整环境变量请参见 `.env.example`。

### 3. 初始化数据库

```bash
python -c "from backend.app import app; from backend.models import init_db; init_db()"
```

### 4. 构建知识库编辑器前端

知识库编辑器基于 React + Vite，需要 Node.js 18+：

```bash
cd frontend
npm install
npm run build
cd ..
```

构建产物输出到 `static/frontend/`，Nginx 需要直接服务该目录。

### 5. 启动应用

```bash
# 方式一：直接启动（开发环境）
cd /path/to/my-blog
python3 backend/app.py

# 方式二：后台运行（推荐开发/测试）
nohup python3 backend/app.py > logs/app.log 2>&1 &

# 方式三：使用环境变量启动
ADMIN_USERNAME="admin" ADMIN_PASSWORD="AdminPass123!" python3 backend/app.py

# 方式四：使用启动脚本
./scripts/start.sh
```

### 6. 访问应用

- **主页**: http://localhost:5001/
- **登录**: http://localhost:5001/login
- **管理后台**: http://localhost:5001/admin
- **知识库编辑**: http://localhost:5001/knowledge/edit

---

## 详细配置说明

### 端口配置

应用默认使用 **5001 端口**，避免与 macOS 系统的 AirPlay Receiver（占用 5000 端口）冲突。

如果需要修改端口：

```bash
export PORT="8000"  # 使用其他端口
python3 backend/app.py
```

### 数据库配置

数据库文件位置：`db/simple_blog.db`

首次启动会自动：
1. 创建数据库表结构
2. 创建默认管理员账号（使用环境变量中的用户名和密码）
3. 初始化全文搜索索引

如需手动初始化：

```bash
python -c "from backend.app import app; from backend.models import init_db; init_db()"
```

### 文件上传配置

- **上传目录**: `static/uploads/`
- **允许格式**: PNG, JPG, JPEG, GIF, WEBP, HEIC
- **单文件大小**: 最大 5MB
- **图片尺寸**: 最大 4096x4096 像素

### 日志系统

日志文件位置：`logs/`

- `app.log` - 应用日志
- `login.log` - 登录日志
- `operation.log` - 操作日志
- `error.log` - 错误日志
- `sql.log` - SQL 查询日志

---

## 生产环境部署

### 使用 Gunicorn（推荐）

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动应用
gunicorn -w 4 -b 0.0.0.0:5001 backend.app:app
```

参数说明：
- `-w 4`: 4 个工作进程
- `-b 0.0.0.0:5001`: 绑定所有网络接口的 5001 端口
- `backend.app:app`: 应用模块路径

### 使用 systemd（Linux）

#### 方式一：使用安装脚本

```bash
sudo ./scripts/install-service.sh
```

#### 方式二：使用 Python 运行

1. **准备环境变量文件**
```bash
# 在项目目录创建 .env 文件
cd /path/to/my-blog
cp .env.example .env
vim .env  # 修改配置
```

2. **创建服务文件**
```bash
sudo vim /etc/systemd/system/simple-blog.service
```

配置示例：
```ini
[Unit]
Description=Simple Blog Flask Application
Documentation=https://github.com/lbxxgn/my-blog
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/my-blog
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="FLASK_APP=app.py"
Environment="FLASK_ENV=production"
Environment="PYTHONPATH=/path/to/my-blog"
Environment="PORT=5001"

# 从 .env 文件加载环境变量（重要！）
EnvironmentFile=-/path/to/my-blog/.env

ExecStart=/path/to/my-blog/.venv/bin/python /path/to/my-blog/backend/app.py
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

StandardOutput=append:/path/to/my-blog/logs/app.log
StandardError=append:/path/to/my-blog/logs/error.log

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

> 项目仓库中**不存在** `simple-blog.service` 文件，服务文件需手动创建或使用 `scripts/install-service.sh` 生成。

3. **启动和管理服务**
```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start simple-blog

# 设置开机自启
sudo systemctl enable simple-blog

# 查看服务状态
sudo systemctl status simple-blog

# 查看日志
sudo journalctl -u simple-blog -f

# 停止服务
sudo systemctl stop simple-blog

# 重启服务
sudo systemctl restart simple-blog
```

#### 方式二：使用 Gunicorn（推荐生产环境）

1. **安装 Gunicorn**
```bash
pip install gunicorn
```

2. **创建服务文件**
```bash
sudo vim /etc/systemd/system/simple-blog.service
```

配置示例：
```ini
[Unit]
Description=Simple Blog (Gunicorn)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/my-blog
Environment="PATH=/path/to/my-blog/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="FLASK_APP=app.py"
Environment="FLASK_ENV=production"

# 从 .env 文件加载环境变量
EnvironmentFile=-/path/to/my-blog/.env

ExecStart=/path/to/my-blog/.venv/bin/gunicorn \
    -w 4 \
    -b 0.0.0.0:5001 \
    --error-logfile /path/to/my-blog/logs/error.log \
    backend.app:app

Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

3. **启动服务**
```bash
sudo systemctl daemon-reload
sudo systemctl start simple-blog
sudo systemctl enable simple-blog
```

#### 服务管理常用命令

```bash
# 查看服务状态
sudo systemctl status simple-blog

# 实时查看日志
sudo journalctl -u simple-blog -f

# 查看最近 100 条日志
sudo journalctl -u simple-blog -n 100

# 重启服务
sudo systemctl restart simple-blog

# 停止服务
sudo systemctl stop simple-blog

# 禁用服务（开机不启动）
sudo systemctl disable simple-blog

# 重新加载配置（修改服务文件后）
sudo systemctl daemon-reload
```

### Nginx 反向代理配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态文件直接服务
    location /static/ {
        alias /path/to/my-blog/static/;
        expires 30d;
    }

    # 知识库编辑器前端（Vite 哈希资源）
    location /static/frontend/ {
        alias /path/to/my-blog/static/frontend/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 故障排查

### 端口被占用

**错误信息**: `Address already in use`

**解决方法**:
```bash
# macOS 用户：5000 端口被 AirPlay 占用
# 使用 5001 端口（已默认配置）
export PORT="5001"

# 或者查找并停止占用进程
lsof -nP -iTCP:5001 | grep LISTEN
```

### 密码不满足要求

**错误信息**: `Password must be at least 10 characters`

**解决方法**:
```bash
# 密码要求：
# - 系统强制至少 10 位长度
# - 文档建议至少 12 位长度
# - 包含大小写字母
# - 包含数字
# - 不能是常见弱密码

export ADMIN_PASSWORD="SecurePass123456!"
```

### 数据库错误

**错误信息**: `sqlite3.OperationalError: no such table`

**解决方法**:
```bash
# 删除旧数据库并重新初始化（注意：会丢失数据）
rm db/simple_blog.db
python -c "from backend.app import app; from backend.models import init_db; init_db()"
```

### Python 3.13 兼容性

**问题**: Python 3.13 移除了 `imghdr` 模块

**解决方法**: 代码已修复，使用 Pillow 进行图片类型检测，无需额外操作。

---

## 开发环境设置

### 启用调试模式

```bash
export DEBUG="True"
python3 backend/app.py
```

调试模式提供：
- 详细错误信息
- 自动重载（代码修改后自动重启）
- Flask 调试工具

### 查看日志

```bash
# 实时查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看登录日志
cat logs/login.log

# 查看操作日志
cat logs/operation.log

# 查看 SQL 日志
cat logs/sql.log
```

---

## 安全建议

### 生产环境必做

1. **设置强密码**
   ```bash
   export ADMIN_PASSWORD="VeryStrongPassword123!@#"
   ```

2. **关闭调试模式**
   ```bash
   export DEBUG="False"
   ```

3. **配置 HTTPS**
   - 使用 Let's Encrypt 免费证书
   - 设置 `FORCE_HTTPS="True"`

4. **设置防火墙**
   ```bash
   # 只允许必要的端口
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

5. **定期备份数据库**
   ```bash
   cp db/simple_blog.db backups/simple_blog-$(date +%Y%m%d_%H%M%S).db
   ```

6. **更新依赖**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

---

## 性能优化

### 数据库优化

```bash
# 定期重建 FTS 索引
python3 -c "
from backend.models import get_db_connection
conn = get_db_connection()
conn.execute('INSERT INTO posts_fts(posts_fts) VALUES(\"rebuild\")')
conn.commit()
conn.close()
"
```

### 使用 Redis 缓存（可选）

```bash
# 安装 Redis
brew install redis  # macOS
sudo apt install redis-server  # Ubuntu

# 启动 Redis
redis-server

# 修改 Flask-Limiter 配置（在 app.py 中）
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",  # 使用 Redis
    strategy="fixed-window"
)
```

---

## 多用户管理

### 创建新用户

1. 登录管理员账号
2. 访问 http://localhost:5001/admin/users/new
3. 填写用户信息：
   - 用户名
   - 密码（至少 10 位，建议 12 位以上）
   - 显示名称
   - 角色（author/editor/admin）
   - 个人简介

### 角色权限

- **admin (管理员)**: 完全权限
  - 管理所有用户
  - 创建/编辑/删除所有文章
  - 管理评论

- **editor (编辑)**: 内容管理
  - 创建/编辑所有文章和评论
  - 不能删除文章
  - 不能管理用户

- **author (作者)**: 基本创作
  - 只能创建/编辑自己的文章
  - 不能删除文章
  - 不能管理用户

---

## 常用命令

```bash
# 启动应用
python3 backend/app.py

# 停止应用
# 按 Ctrl+C 或找到进程 ID 并 kill
ps aux | grep "python.*app.py"
kill <PID>

# 重启应用
kill <PID> && python3 backend/app.py

# 查看日志
tail -f logs/app.log

# 检查端口占用
lsof -nP -iTCP:5001 | grep LISTEN

# 测试 API
curl http://localhost:5001/api/posts

# 数据库备份
cp db/simple_blog.db db/simple_blog.db.backup

# 查看数据库内容
sqlite3 db/simple_blog.db "SELECT id, title, created_at FROM posts LIMIT 10;"

# 运行数据库迁移
python3 backend/migrations/migrate_knowledge_base.py

# 生成静态资源 manifest
python3 scripts/generate_manifest.py

# 构建知识库编辑器前端
cd frontend && npm install && npm run build && cd ..
```

---

## AI 功能配置

系统集成了 AI 功能，支持多个 AI 提供商。配置方式有两种：

### 方式一：通过 Web 界面配置（推荐）

1. 启动应用并登录管理员账号
2. 访问 AI 设置页面：http://localhost:5001/admin/ai/configure
3. 选择 AI 提供商并配置 API 密钥
4. 测试连接
5. 保存设置

**支持的 AI 提供商：**

#### 1. OpenAI
- **模型**: GPT-3.5-turbo, GPT-4o, GPT-4-turbo, GPT-4
- **成本**: ~$0.001-0.002/次
- **适用场景**: 英文内容，高质量要求
- **密钥获取**: https://platform.openai.com/api-keys

#### 2. 火山引擎（豆包）
- **模型**: doubao-pro-32k, doubao-pro-4k, doubao-lite-4k
- **成本**: ~¥0.00001-0.00004/次（最低）
- **适用场景**: 中文内容，成本敏感
- **密钥获取**: https://console.volcengine.com/ark

#### 3. 阿里百炼（通义千问）
- **模型**: qwen-flash, qwen-turbo, qwen-plus, qwen-max
- **成本**: ~¥0.0001-0.002/次
- **适用场景**: 中文内容，性价比高
- **密钥获取**: https://dashscope.console.aliyun.com/

### 方式二：通过环境变量配置

编辑 `.env` 文件：

```bash
# AI 默认提供商和模型
AI_DEFAULT_PROVIDER=openai
AI_DEFAULT_MODEL=gpt-3.5-turbo

# 对应的 API 密钥
OPENAI_API_KEY=sk-xxxxx
# 或
VOLCENGINE_API_KEY=xxxxx
# 或
DASHSCOPE_API_KEY=sk-xxxxx

# 限流与长度限制
AI_RATE_LIMIT_PER_HOUR=10
AI_CONTENT_MAX_LENGTH=500

# 启用 AI 标签生成（可选）
AI_TAG_GENERATION_ENABLED=1
```

### AI 功能说明

**1. AI 标签生成**
- 在文章编辑器中点击 "AI 生成" 按钮
- 自动分析文章内容并生成 3-5 个相关标签
- 支持中英文内容识别

**2. AI 摘要生成**
- 在 AI 工具栏点击 "生成摘要" 按钮
- 生成 200 字以内的文章摘要
- 可选择添加到文章开头

**3. AI 相关文章推荐**
- 保存文章后点击 "推荐相关文章" 按钮
- 基于主题、技术栈、领域智能推荐
- 最多推荐 3 篇相关文章

**4. AI 内容续写**
- 在 AI 工具栏点击 "AI 续写" 按钮
- 保持原有写作风格续写约 500 字
- 需至少先写 100 字才能使用

### 查看 AI 使用情况

- 访问：http://localhost:5001/admin/ai/history
- 查看所有 AI 功能调用记录
- 查看 tokens 使用统计
- 查看费用统计（区分 CNY 和 USD）

### 成本优化建议

1. **中文内容优先使用国内模型**
   - 火山引擎：成本最低（¥0.00001/次）
   - 阿里百炼：性价比高（¥0.0001/次）

2. **英文内容或高质量要求使用 OpenAI**
   - GPT-3.5-turbo：速度快，质量好（$0.001/次）
   - GPT-4o：质量最高（$0.002/次）

3. **批量操作成本控制**
   - 使用火山引擎批量生成标签
   - 重要文章使用 OpenAI 或阿里百炼

---

## 技术栈

- **后端**: Flask 3.0, Python 3.11+
- **数据库**: SQLite 3 + FTS5 全文搜索
- **前端**: 原生 JavaScript, CSS3, React + Vite（知识库编辑器）
- **Markdown**: markdown2
- **安全**: Flask-WTF (CSRF), bleach (XSS 防护), webauthn (Passkey)
- **图片处理**: Pillow

---

## 支持

如遇问题，请检查：

1. **日志文件**: `logs/` 目录
2. **环境变量**: 确认必需变量已设置
3. **端口占用**: 确认 5001 端口未被占用
4. **数据库权限**: 确认 `db/` 目录可写
5. **Python 版本**: 推荐 Python 3.11+
6. **前端构建**: 确认已运行 `cd frontend && npm install && npm run build`

---

**祝使用愉快！** 🎉
