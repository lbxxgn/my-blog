# Passkey 升级手册

## 目标

本次升级为系统新增了第一版 `Passkey / WebAuthn` 快捷登录能力：

- `iPhone` 可用 `Face ID`
- `Mac` 可用 `Touch ID`
- 现有用户名密码登录继续保留

适用入口：

- [登录页](/Users/gn/simple-blog/templates/login.html)
- [修改密码页 / 快捷登录管理](/Users/gn/simple-blog/templates/change_password.html)

---

## 升级内容

### 新增依赖

已新增：

```txt
webauthn>=2.7,<3.0
```

见 [requirements.txt](/Users/gn/simple-blog/requirements.txt)

### 数据库变更

新增表：

```sql
CREATE TABLE IF NOT EXISTS user_passkeys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    credential_id BLOB NOT NULL UNIQUE,
    public_key BLOB NOT NULL,
    sign_count INTEGER DEFAULT 0,
    device_name TEXT,
    transports TEXT,
    credential_device_type TEXT,
    backup_eligible BOOLEAN DEFAULT 0,
    backup_state BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

初始化逻辑见 [backend/models/models.py](/Users/gn/simple-blog/backend/models/models.py)

### 新增接口

见 [backend/routes/auth.py](/Users/gn/simple-blog/backend/routes/auth.py)：

- `POST /passkeys/register/begin`
- `POST /passkeys/register/finish`
- `POST /passkeys/authenticate/begin`
- `POST /passkeys/authenticate/finish`
- `GET /passkeys`
- `DELETE /passkeys/<id>`

---

## 升级步骤

### 1. 备份

建议先备份数据库：

```bash
cp db/simple_blog.db db/simple_blog.db.backup.$(date +%Y%m%d_%H%M%S)
```

### 2. 安装依赖

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 检查配置

本地开发通常不需要额外配置，但生产环境建议显式设置：

```bash
export PASSKEY_RP_NAME="我的博客"
export PASSKEY_RP_ID="your-domain.com"
export PASSKEY_ALLOWED_ORIGINS="https://your-domain.com"
```

相关配置见 [backend/config.py](/Users/gn/simple-blog/backend/config.py)

### 4. 重启服务

如果你是手动启动：

```bash
./scripts/start.sh
```

如果你是 systemd：

```bash
sudo systemctl restart simple-blog
```

### 5. 升级验证

至少验证这几项：

1. 打开 `/login`，看到 `使用 Face ID / Touch ID 登录`
2. 正常密码登录仍可用
3. 打开 `/change-password`，看到“快捷登录”区域
4. 能成功绑定一台设备
5. 退出后能用 Passkey 登录

---

## 本地测试注意事项

### 推荐访问方式

本地请优先使用：

```txt
http://localhost:5005
```

不建议用：

```txt
http://127.0.0.1:5005
http://192.168.x.x:5005
```

原因：

- Passkey 在本地开发时更适合配合 `localhost`
- 直接用 IP 很容易触发浏览器的域名校验问题

---

## 回滚方法

如果你需要快速回滚：

1. 恢复旧代码版本
2. 保留 `user_passkeys` 表不影响原密码登录
3. 如果一定要删除表：

```sql
DROP TABLE IF EXISTS user_passkeys;
```

注意：

- 删除该表只会移除快捷登录能力
- 不会影响原有密码登录
