# Simple Blog Systemd 服务部署指南

## 快速部署

### 方法一：使用自动安装脚本（推荐）

```bash
# 克隆项目后，在项目根目录执行
sudo ./install-service.sh
```

安装脚本会引导你完成以下步骤：
1. 输入部署路径（默认当前目录）
2. 配置运行用户（默认 root）
3. 配置监听端口（默认 5001）
4. 自动创建必要的目录
5. 生成并安装 systemd 服务文件
6. 启用并启动服务

### 方法二：手动安装

#### 1. 创建环境变量文件

```bash
cp .env.example .env
vi .env  # 修改配置，特别是密码和密钥
```

#### 2. 创建必要目录

```bash
mkdir -p logs db static/uploads backups
```

#### 3. 修改服务文件

编辑 `simple-blog.service`，将所有 `/root/my-blog` 替换为你的实际部署路径：

```bash
sed -i 's|/root/my-blog|/your/actual/path|g' simple-blog.service
```

#### 4. 安装服务

```bash
# 复制服务文件
sudo cp simple-blog.service /etc/systemd/system/

# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable simple-blog

# 启动服务
sudo systemctl start simple-blog
```

## 服务管理

### 常用命令

```bash
# 启动服务
sudo systemctl start simple-blog

# 停止服务
sudo systemctl stop simple-blog

# 重启服务
sudo systemctl restart simple-blog

# 查看服务状态
sudo systemctl status simple-blog

# 查看实时日志
sudo journalctl -u simple-blog -f

# 查看最近100条日志
sudo journalctl -u simple-blog -n 100

# 重新加载配置（修改服务文件后）
sudo systemctl daemon-reload
sudo systemctl restart simple-blog
```

### 日志文件

除了 systemd journal，应用还会写入文件日志：

- **应用日志**: `logs/app.log`
- **错误日志**: `logs/error.log`

查看文件日志：

```bash
# 实时查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log
```

## 配置说明

### 环境变量

服务会从 `.env` 文件加载环境变量。主要配置项：

```bash
# 基础配置
DEBUG=False              # 生产环境必须为 False
PORT=5001               # 监听端口
SECRET_KEY=xxx          # Flask 密钥

# 管理员账户
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password

# AI 配置（可选）
AI_PROVIDER=openai      # openai, volcengine, dashscope
AI_API_KEY=xxx
AI_MODEL=gpt-3.5-turbo
```

### 服务文件配置

`simple-blog.service` 中的关键配置：

```ini
[Service]
Type=simple
User=root                           # 运行用户
Group=root
WorkingDirectory=/root/my-blog      # 项目目录
Environment="PORT=5001"             # 环境变量
EnvironmentFile=-/root/my-blog/.env # .env 文件（可选）
ExecStart=/usr/bin/python3 /root/my-blog/backend/app.py

# 重启策略
Restart=always                      # 崩溃后自动重启
RestartSec=10                       # 重启前等待10秒

# 资源限制
LimitNOFILE=65536                   # 最大文件描述符数量
```

## 故障排查

### 服务无法启动

1. **检查日志**：
   ```bash
   sudo journalctl -u simple-blog -n 50
   cat logs/error.log
   ```

2. **检查配置**：
   ```bash
   # 验证 .env 文件是否存在
   ls -la .env

   # 验证 Python 和依赖
   python3 --version
   pip3 list | grep -i flask
   ```

3. **手动测试**：
   ```bash
   # 停止服务
   sudo systemctl stop simple-blog

   # 手动运行查看错误
   python3 backend/app.py
   ```

### 端口被占用

如果端口 5001 被占用，修改配置：

```bash
# 方法1：修改 .env 文件
echo "PORT=5002" >> .env
sudo systemctl restart simple-blog

# 方法2：修改服务文件
vi simple-blog.service  # 修改 PORT=5002
sudo systemctl daemon-reload
sudo systemctl restart simple-blog
```

### 权限问题

如果遇到权限错误：

```bash
# 检查文件权限
ls -la backend/app.py
ls -la logs/

# 修改所有者（如果使用 root 用户）
sudo chown -R root:root /root/my-blog

# 或使用其他用户
sudo chown -R www-data:www-data /root/my-blog
```

## 安全建议

### 1. 使用专用用户运行

创建低权限用户运行服务：

```bash
# 创建用户
sudo useradd -r -s /bin/false simpleblog

# 修改项目所有者
sudo chown -R simpleblog:simpleblog /root/my-blog

# 修改服务文件
# User=simpleblog
# Group=simpleblog
```

### 2. 启用安全选项

在 `simple-blog.service` 中取消注释：

```ini
NoNewPrivileges=true
PrivateTmp=true
```

### 3. 配置防火墙

```bash
# UFW (Ubuntu)
sudo ufw allow 5001/tcp

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-port=5001/tcp
sudo firewall-cmd --reload
```

### 4. 配置 HTTPS

使用 Nginx 或 Caddy 反向代理：

**Nginx 示例**：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. 定期备份

配置自动备份：

```bash
# 添加到 crontab
crontab -e

# 每天凌晨 2 点备份数据库
0 2 * * * /root/my-blog/scripts/backup.sh
```

## 升级部署

```bash
# 1. 停止服务
sudo systemctl stop simple-blog

# 2. 备份数据
cp db/simple_blog.db db/simple_blog.db.backup

# 3. 更新代码
git pull

# 4. 更新依赖
pip3 install -r requirements.txt

# 5. 运行数据库迁移（如果有）
python3 backend/migrations/migrate_xxx.py

# 6. 重启服务
sudo systemctl start simple-blog

# 7. 验证
sudo systemctl status simple-blog
```

## 卸载服务

```bash
# 停止并禁用服务
sudo systemctl stop simple-blog
sudo systemctl disable simple-blog

# 删除服务文件
sudo rm /etc/systemd/system/simple-blog.service

# 重载 systemd
sudo systemctl daemon-reload

# （可选）删除项目文件
# sudo rm -rf /root/my-blog
```
