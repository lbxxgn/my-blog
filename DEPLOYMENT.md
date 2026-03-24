# 🚀 Simple Blog 部署指南

完整的部署和升级指南，涵盖systemd服务配置和远程服务器管理。

---

## 📑 目录

- [快速开始](#快速开始)
- [首次部署](#首次部署)
- [Systemd服务管理](#systemd服务管理)
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

# 3. 安装systemd服务
sudo cp simple-blog.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable simple-blog
sudo systemctl start simple-blog
```

---

## 📦 首次部署

### 1. 系统要求

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- **Python**: 3.8 或更高版本
- **内存**: 至少 512MB RAM
- **磁盘**: 至少 500MB 可用空间

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

# 数据库（可选，默认使用SQLite）
# DATABASE_URL=sqlite:///db/simple_blog.db

# AI功能（可选）
# AI_PROVIDER=openai
# AI_API_KEY=your-api-key
# AI_MODEL=gpt-3.5-turbo
```

### 3. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装Python依赖
pip install -r requirements.txt

# 初始化数据库
python3 -c "from backend.app import app; from backend.models import init_db; init_db()"
```

### 4. Systemd服务配置

创建服务文件 `/etc/systemd/system/simple-blog.service`：

```ini
[Unit]
Description=Simple Blog Flask Application
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/simple-blog
Environment="PORT=5001"
EnvironmentFile=-/var/www/simple-blog/.env
ExecStart=/usr/bin/python3 /var/www/simple-blog/backend/app.py

# 重启策略
Restart=always
RestartSec=10

# 资源限制
LimitNOFILE=65536

# 安全选项
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

安装并启动服务：

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable simple-blog

# 启动服务
sudo systemctl start simple-blog

# 查看状态
sudo systemctl status simple-blog
```

---

## 🔧 Systemd服务管理

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
# 实时查看systemd日志
sudo journalctl -u simple-blog -f

# 查看最近100条日志
sudo journalctl -u simple-blog -n 100

# 查看应用日志文件
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log
```

---

## 🔄 远程服务器升级

### SSH登录服务器

```bash
ssh user@your-server-ip
# 或
ssh your-server-domain
```

### 进入项目目录

```bash
cd /var/www/simple-blog
```

### 执行升级

#### 方法一：使用升级脚本

```bash
# 一键升级
chmod +x scripts/upgrade.sh
./scripts/upgrade.sh

# 验证结果
./scripts/verify_upgrade.sh
```

#### 方法二：手动升级步骤

```bash
# 1. 备份当前版本
BACKUP_DIR="backups/pre_upgrade_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp db/simple_blog.db "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"

# 2. 拉取最新代码
git fetch origin
git pull origin main

# 3. 更新依赖
source .venv/bin/activate
pip install -r backend/requirements.txt

# 4. 运行数据库迁移（如有）
python3 backend/migrations/migrate_drafts.py
python3 backend/migrations/migrate_image_optimization.py

# 5. 重启服务
sudo systemctl restart simple-blog

# 6. 验证升级
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
   - 检查CSS是否正常加载
   - 查看页面源代码，CSS/JS应该带版本参数

2. **文章页面**: http://your-server-ip:5001/post/1
   - 验证文章正常显示

3. **登录页面**: http://your-server-ip:5001/login
   - 测试登录功能
   - 验证草稿自动保存

---

## 🔍 故障排查

### 服务无法启动

1. **检查日志**：
   ```bash
   sudo journalctl -u simple-blog -n 50
   cat logs/error.log
   ```

2. **检查配置**：
   ```bash
   # 验证.env文件
   ls -la .env

   # 验证Python和依赖
   python3 --version
   pip3 list | grep -i flask
   ```

3. **手动测试**：
   ```bash
   sudo systemctl stop simple-blog
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

# 删除旧表重新创建（谨慎！）
sqlite3 db/simple_blog.db "DROP TABLE IF EXISTS drafts;"

# 重新运行迁移
python3 backend/migrations/migrate_drafts.py
```

### Git pull失败

```bash
# 暂存本地修改
git stash

# 拉取代码
git pull origin main

# 恢复修改（如需要）
git stash pop
```

### 静态资源404

```bash
# 检查文件权限
chmod -R 755 static/

# 重新生成manifest
python3 generate_manifest.py

# 重启服务
sudo systemctl restart simple-blog
```

---

## 🔒 安全配置

### 1. 使用专用用户运行

```bash
# 创建低权限用户
sudo useradd -r -s /bin/false simpleblog

# 修改项目所有者
sudo chown -R simpleblog:simpleblog /var/www/simple-blog

# 修改服务文件
# User=simpleblog
# Group=simpleblog
```

### 2. 配置防火墙

```bash
# UFW (Ubuntu)
sudo ufw allow 5001/tcp

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload
```

### 3. 配置HTTPS

使用Nginx反向代理：

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
}
```

### 4. 启用安全选项

在服务文件中确保启用：

```ini
NoNewPrivileges=true
PrivateTmp=true
```

### 5. 定期备份

配置自动备份：

```bash
# 添加到crontab
crontab -e

# 每天凌晨2点备份数据库
0 2 * * * /var/www/simple-blog/scripts/backup.sh
```

---

## 💾 备份与恢复

### 自动备份脚本

创建 `scripts/backup.sh`：

```bash
#!/bin/bash
BACKUP_DIR="/var/www/simple-blog/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# 备份数据库
cp /var/www/simple-blog/db/simple_blog.db \
   "$BACKUP_DIR/simple_blog_$TIMESTAMP.db"

# 保留最近30天的备份
find "$BACKUP_DIR" -name "simple_blog_*.db" -mtime +30 -delete

echo "Backup completed: simple_blog_$TIMESTAMP.db"
```

### 手动备份

```bash
# 备份数据库
cp db/simple_blog.db backups/simple_blog_$(date +%Y%m%d).db

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
cp backups/simple_blog_YYYYMMDD.db db/simple_blog.db

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
./scripts/rollback.sh backups/pre_upgrade_<timestamp>
```

### 手动回滚

```bash
# 1. 停止服务
sudo systemctl stop simple-blog

# 2. 恢复数据库
cp backups/pre_upgrade_YYYYMMDD_HHMMSS/simple_blog.db db/simple_blog.db

# 3. 回退代码
git log --oneline -10  # 查看提交历史
git reset --hard <old-commit-hash>

# 4. 恢复依赖
source .venv/bin/activate
pip install -r backend/requirements.txt

# 5. 重启服务
sudo systemctl start simple-blog
```

---

## 📋 升级清单

升级前确认：

- [ ] 已通知用户维护时间（生产环境）
- [ ] 服务器有足够磁盘空间（至少500MB）
- [ ] Python 3.8+ 已安装
- [ ] 已创建备份
- [ ] 知道如何回滚
- [ ] 测试环境已验证

升级后验证：

- [ ] 服务正常运行（端口5001）
- [ ] 首页可访问
- [ ] CSS/JS正常加载
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
   ```

2. **运行验证脚本**
   ```bash
   ./scripts/verify_upgrade.sh
   ```

3. **查看相关文档**
   - [完整API文档](docs/api-documentation.md)
   - [快速启动指南](QUICKSTART.md)
   - [升级指南](UPGRADE_GUIDE.md)

---

## 🎉 部署完成

部署成功后，您的博客将拥有：

- ✅ **自动启动**: 系统重启后自动运行
- ✅ **崩溃恢复**: 异常退出时自动重启
- ✅ **日志管理**: 集中化的systemd日志
- ✅ **安全运行**: 低权限用户和沙箱环境
- ✅ **易于升级**: 简单的git pull升级流程

祝您部署顺利！🚀
