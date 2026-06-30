# 🚀 Simple Blog 部署指南

完整的部署和升级指南，涵盖 systemd 服务配置和远程服务器管理。

---

## 📑 目录

- [快速开始](#快速开始)
- [首次部署](#首次部署)
- [Systemd 服务管理](#systemd服务管理)
- [远程服务器升级](#远程服务器升级)
- [故障排查](#故障排查)
- [安全配置](#安全配置)
- [备份与恢复](#备份与恢复)

---

## 🎯 快速开始

### 方法一：自动安装脚本（推荐）

```bash
# 克隆项目
git clone https://github.com/lbxxgn/my-blog.git
cd my-blog

# 运行自动安装
sudo ./scripts/install-service.sh
```

### 方法二：手动安装

```bash
# 1. 创建环境变量
cp .env.example .env
vi .env  # 修改配置

# 2. 创建必要目录
mkdir -p logs db static/uploads backups

# 3. 安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. 初始化数据库
python -c "from backend.app import app; from backend.models import init_db; init_db()"

# 5. 构建知识库编辑器前端（需要 Node.js）
cd frontend && npm install && npm run build && cd ..

# 6. 安装 systemd 服务
sudo ./scripts/install-service.sh
# 或者手动编写服务文件（见下文示例）
```

---

## 📦 首次部署

### 1. 系统要求

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- **Python**: 3.11 或更高版本（推荐）
- **Node.js**: 18+（构建知识库编辑器前端需要）
- **内存**: 至少 512MB RAM
- **磁盘**: 至少 1GB 可用空间

### 2. 环境配置

创建 `.env` 文件：

```bash
# 基础配置
DEBUG=False
PORT=5001
SECRET_KEY=your-random-secret-key-here

# 管理员账户
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password-here

# 数据库（可选，默认使用 SQLite）
# DATABASE_URL=sqlite:///db/simple_blog.db

# Passkey / WebAuthn 配置
PASSKEY_RP_NAME=Simple Blog
PASSKEY_RP_ID=your-domain.com
PASSKEY_ALLOWED_ORIGINS=https://your-domain.com

# 设备记住时长（天）
REMEMBER_DEVICE_DAYS=90

# 静态资源
USE_MINIFIED_ASSETS=True
ASSET_BUILD_VERSION=

# AI 功能（可选）
# AI_DEFAULT_PROVIDER=openai
# AI_DEFAULT_MODEL=gpt-3.5-turbo
# OPENAI_API_KEY=your-api-key
# AI_RATE_LIMIT_PER_HOUR=10
# AI_CONTENT_MAX_LENGTH=500
```

完整环境变量请参见 `.env.example`。

### 3. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt

# 初始化数据库
python -c "from backend.app import app; from backend.models import init_db; init_db()"
```

### 4. 构建知识库编辑器前端

```bash
cd frontend
npm install
npm run build
cd ..
```

构建产物输出到 `static/frontend/`，Nginx 需要直接服务该目录下的哈希资源（见 Nginx 配置示例）。

### 5. Systemd 服务配置

推荐使用安装脚本自动生成服务文件：

```bash
sudo ./scripts/install-service.sh
```

如需手动编写，创建服务文件 `/etc/systemd/system/simple-blog.service`：

```ini
[Unit]
Description=Simple Blog Flask Application
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/my-blog
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="FLASK_APP=app.py"
Environment="FLASK_ENV=production"
Environment="PYTHONPATH=/var/www/my-blog"
Environment="PORT=5001"
EnvironmentFile=-/var/www/my-blog/.env

ExecStart=/var/www/my-blog/.venv/bin/python /var/www/my-blog/backend/app.py

# 重启策略
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# 日志配置
StandardOutput=append:/var/www/my-blog/logs/app.log
StandardError=append:/var/www/my-blog/logs/error.log

# 资源限制
LimitNOFILE=65536

# 安全选项
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

> **注意**：项目仓库中**不存在** `simple-blog.service` 文件，请勿直接 `cp simple-blog.service /etc/systemd/system/`。

安装并启动服务：

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable simple-blog

# 启动服务
sudo systemctl start simple-blog

# 查看状态
sudo systemctl status simple-blog
```

---

## 🔧 Systemd 服务管理

### 日常管理命令

```bash
# 启动服务
sudo systemctl start simple-blog

# 停止服务
sudo systemctl stop simple-blog

# 重启服务
sudo systemctl restart simple-blog

# 查看服务状态
sudo systemctl status simple-blog

# 重新加载配置（修改服务文件后）
sudo systemctl daemon-reload
sudo systemctl restart simple-blog
```

### 日志查看

```bash
# 实时查看 systemd 日志
sudo journalctl -u simple-blog -f

# 查看最近100条日志
sudo journalctl -u simple-blog -n 100

# 查看应用日志文件
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看登录日志
tail -f logs/login.log

# 查看操作日志
tail -f logs/operation.log

# 查看 SQL 日志
tail -f logs/sql.log
```

---

## 🔄 远程服务器升级

### SSH 登录服务器

```bash
ssh user@your-server-ip
# 或
ssh your-server-domain
```

### 进入项目目录

```bash
cd /var/www/my-blog
```

### 执行升级

#### 方法一：使用升级脚本

```bash
# 一键升级（脚本会自动备份、安装依赖、运行迁移、重启服务）
chmod +x scripts/upgrade.sh scripts/verify_upgrade.sh scripts/rollback.sh
./scripts/upgrade.sh

# 验证结果
./scripts/verify_upgrade.sh
```

#### 方法二：手动升级步骤

```bash
# 1. 备份当前版本
BACKUP_DIR="backups/upgrade_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp db/simple_blog.db "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"

# 2. 拉取最新代码
git fetch origin
git pull origin main

# 3. 更新依赖
source .venv/bin/activate
pip install -r requirements.txt

# 4. 运行数据库迁移（根据版本需要选择）
python3 backend/migrations/migrate_add_access_control.py
python3 backend/migrations/migrate_add_post_type.py
python3 backend/migrations/migrate_ai_features.py
python3 backend/migrations/migrate_drafts.py
python3 backend/migrations/migrate_image_optimization.py
python3 backend/migrations/migrate_knowledge_base.py
python3 backend/migrations/migrate_multiauthor.py

# 5. 构建前端（如前端有更新）
cd frontend && npm install && npm run build && cd ..

# 6. 重启服务
sudo systemctl restart simple-blog

# 7. 验证升级
curl http://localhost:5001
sudo systemctl status simple-blog
```

### 升级后验证

**基础检查**：

```bash
# 检查应用状态
curl http://localhost:5001

# 检查进程
ps aux | grep "python.*app.py"

# 检查端口
lsof -i:5001
```

**功能验证**：

1. **首页**: http://your-server-ip:5001
   - 检查 CSS 是否正常加载
   - 查看页面源代码，CSS/JS 应该带版本参数

2. **文章页面**: http://your-server-ip:5001/post/1
   - 验证文章正常显示

3. **登录页面**: http://your-server-ip:5001/login
   - 测试登录功能
   - 验证草稿自动保存

4. **知识库编辑器**: http://your-server-ip:5001/knowledge/edit
   - 验证 React/Vite 前端资源正常加载

---

## 🔍 故障排查

### 服务无法启动

1. **检查日志**：
   ```bash
   sudo journalctl -u simple-blog -n 50
   cat logs/error.log
   cat logs/app.log
   ```

2. **检查配置**：
   ```bash
   # 验证 .env 文件
   ls -la .env

   # 验证 Python 和依赖
   python3 --version
   source .venv/bin/activate
   pip list | grep -i flask
   ```

3. **手动测试**：
   ```bash
   sudo systemctl stop simple-blog
   source .venv/bin/activate
   python3 backend/app.py
   ```

### 端口被占用

```bash
# 查看占用进程
lsof -i:5001
# 或
netstat -tlnp | grep 5001

# 修改端口
echo "PORT=5002" >> .env
sudo systemctl restart simple-blog
```

### 数据库迁移失败

```bash
# 检查数据库权限
ls -la db/simple_blog.db

# 手动检查表
sqlite3 db/simple_blog.db ".tables"

# 重新运行迁移（谨慎操作）
python3 backend/migrations/migrate_drafts.py
python3 backend/migrations/migrate_knowledge_base.py
```

### Git pull 失败

```bash
# 暂存本地修改
git stash

# 拉取代码
git pull origin main

# 恢复修改（如需要）
git stash pop
```

### 静态资源 404

```bash
# 检查文件权限
chmod -R 755 static/

# 重新生成 manifest
python3 scripts/generate_manifest.py

# 重新构建前端（知识库编辑器）
cd frontend && npm install && npm run build && cd ..

# 重启服务
sudo systemctl restart simple-blog
```

---

## 🔒 安全配置

### 1. 使用专用用户运行

```bash
# 创建低权限用户
sudo useradd -r -s /bin/false simpleblog

# 修改项目所有者（将 /var/www/my-blog 替换为实际路径）
sudo chown -R simpleblog:simpleblog /var/www/my-blog

# 修改服务文件中的用户
# User=simpleblog
# Group=simpleblog

sudo systemctl daemon-reload
sudo systemctl restart simple-blog
```

生产环境建议使用 `www-data` 或专用用户 `simpleblog`。

### 2. 配置防火墙

```bash
# UFW (Ubuntu)
sudo ufw allow 5001/tcp

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload
```

### 3. 配置 HTTPS

使用 Nginx 反向代理：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/blog.pem;
    ssl_certificate_key /etc/ssl/private/blog.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态资源（传统资源）
    location /static/ {
        alias /var/www/my-blog/static/;
        expires 30d;
    }

    # 知识库编辑器前端（Vite 哈希资源）
    location /static/frontend/ {
        alias /var/www/my-blog/static/frontend/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 4. 启用安全选项

在服务文件中确保启用：

```ini
NoNewPrivileges=true
PrivateTmp=true
```

### 5. 定期备份

配置自动备份（项目未提供 `scripts/backup.sh`，请自行编写）：

```bash
# 添加到 crontab
crontab -e

# 每天凌晨 2 点备份数据库
0 2 * * * /bin/bash -c 'cp /var/www/my-blog/db/simple_blog.db /var/www/my-blog/backups/simple_blog_$(date +\%Y\%m\%d_\%H\%M\%S).db && find /var/www/my-blog/backups -name "simple_blog_*.db" -mtime +30 -delete'
```

---

## 💾 备份与恢复

### 手动备份

```bash
# 备份数据库
cp db/simple_blog.db backups/simple_blog_$(date +%Y%m%d_%H%M%S).db

# 备份配置
cp .env backups/.env.$(date +%Y%m%d)

# 备份上传文件
tar -czf backups/uploads_$(date +%Y%m%d).tar.gz static/uploads/
```

### 恢复数据

```bash
# 1. 停止服务
sudo systemctl stop simple-blog

# 2. 恢复数据库
cp backups/simple_blog_YYYYMMDD_HHMMSS.db db/simple_blog.db

# 3. 恢复配置（如需要）
cp backups/.env.YYYYMMDD .env

# 4. 重启服务
sudo systemctl start simple-blog
```

---

## 🔄 回滚方法

如果升级后出现问题：

### 自动回滚

```bash
# 使用回滚脚本
./scripts/rollback.sh backups/upgrade_<timestamp>
```

### 手动回滚

```bash
# 1. 停止服务
sudo systemctl stop simple-blog

# 2. 恢复数据库
cp backups/upgrade_YYYYMMDD_HHMMSS/simple_blog.db db/simple_blog.db

# 3. 回退代码
git log --oneline -10  # 查看提交历史
git reset --hard <old-commit-hash>

# 4. 恢复依赖
source .venv/bin/activate
pip install -r requirements.txt

# 5. 重启服务
sudo systemctl start simple-blog
```

---

## 📋 升级清单

升级前确认：

- [ ] 已通知用户维护时间（生产环境）
- [ ] 服务器有足够磁盘空间（至少 1GB）
- [ ] Python 3.11+ 已安装
- [ ] 已创建备份
- [ ] 知道如何回滚
- [ ] 测试环境已验证

升级后验证：

- [ ] 服务正常运行（端口 5001）
- [ ] 首页可访问
- [ ] CSS/JS 正常加载
- [ ] 知识库编辑器资源正常
- [ ] 文章页面正常
- [ ] 登录功能正常
- [ ] 日志无错误信息

---

## 📞 获取帮助

遇到问题时：

1. **查看日志**
   ```bash
   sudo journalctl -u simple-blog -f
   tail -f logs/app.log
   tail -f logs/error.log
   ```

2. **运行验证脚本**
   ```bash
   ./scripts/verify_upgrade.sh
   ```

3. **查看相关文档**
   - [API 文档](docs/api-documentation.md)
   - [快速启动指南](QUICKSTART.md)
   - [启动指南](docs/startup.md)
   - [升级指南](docs/upgrade.md)

---

## 🎉 部署完成

部署成功后，您的博客将拥有：

- ✅ **自动启动**: 系统重启后自动运行
- ✅ **崩溃恢复**: 异常退出时自动重启
- ✅ **日志管理**: 集中化的 systemd 日志与文件日志
- ✅ **安全运行**: 低权限用户和沙箱环境
- ✅ **易于升级**: 简单的 git pull 升级流程

祝您部署顺利！🚀
