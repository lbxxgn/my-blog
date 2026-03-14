# 🌐 远程服务器升级指南

## 代码已成功推送到GitHub！ ✅

```
提交: c1b5436
远程: git@github.com:lbxxgn/my-blog.git
分支: main
```

---

## 🚀 远程服务器升级步骤

### SSH登录到服务器

```bash
ssh user@your-server-ip
# 或
ssh your-server-domain
```

### 进入项目目录

```bash
cd /path/to/your/simple-blog
```

### 拉取最新代码

```bash
# 方法1: 使用git pull（推荐）
git pull origin main

# 方法2: 使用fetch + merge
git fetch origin
git merge origin/main
```

### 执行升级

```bash
# 一键升级
chmod +x upgrade.sh verify_upgrade.sh
./upgrade.sh

# 验证结果
./verify_upgrade.sh
```

---

## 📋 完整升级脚本

如果您希望自动化整个流程，可以使用以下脚本：

```bash
#!/bin/bash
# remote_upgrade.sh - 远程服务器升级脚本

set -e

echo "=========================================="
echo "  Simple Blog 远程服务器升级"
echo "=========================================="
echo ""

# 1. 备份当前版本
echo "1️⃣  备份当前版本..."
BACKUP_DIR="backups/pre_upgrade_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 备份数据库
[ -f db/simple_blog.db ] && cp db/simple_blog.db "$BACKUP_DIR/"

# 备份配置文件
[ -f .env ] && cp .env "$BACKUP_DIR/"
[ -f backend/config.py ] && cp backend/config.py "$BACKUP_DIR/"

echo "✓ 备份完成: $BACKUP_DIR"

# 2. 拉取最新代码
echo ""
echo "2️⃣  拉取最新代码..."
git fetch origin
git pull origin main
echo "✓ 代码更新完成"

# 3. 检查虚拟环境
echo ""
echo "3️⃣  检查虚拟环境..."
if [ ! -d .venv ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "✓ 虚拟环境已激活"

# 4. 安装/更新依赖
echo ""
echo "4️⃣  安装依赖..."
pip install -r backend/requirements.txt --quiet
echo "✓ 依赖安装完成"

# 5. 运行数据库迁移
echo ""
echo "5️⃣  运行数据库迁移..."
export DATABASE_URL="sqlite:///db/simple_blog.db"

python3 backend/migrations/migrate_drafts.py
python3 backend/migrations/migrate_image_optimization.py
echo "✓ 数据库迁移完成"

# 6. 生成静态资源manifest
echo ""
echo "6️⃣  生成静态资源manifest..."
python3 generate_manifest.py
echo "✓ Manifest生成完成"

# 7. 重启应用
echo ""
echo "7️⃣  重启应用..."
# 停止旧进程
if pgrep -f "python.*app.py" > /dev/null; then
    pkill -f "python.*app.py"
    sleep 3
fi

# 启动新进程
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-AdminPass123456}"
nohup python3 backend/app.py > /tmp/flask.log 2>&1 &
sleep 5

# 检查应用状态
if pgrep -f "python.*app.py" > /dev/null; then
    echo "✓ 应用启动成功"
else
    echo "✗ 应用启动失败，请检查日志"
    tail -50 /tmp/flask.log
    exit 1
fi

# 8. 验证升级
echo ""
echo "8️⃣  验证升级..."
chmod +x verify_upgrade.sh
./verify_upgrade.sh

echo ""
echo "=========================================="
echo "  升级完成！"
echo "=========================================="
echo ""
echo "访问地址: http://your-server-ip:5001"
echo "日志文件: tail -f /tmp/flask.log"
echo "备份位置: $BACKUP_DIR"
echo ""
```

使用方法：
```bash
# 在服务器上保存上述脚本为 remote_upgrade.sh
chmod +x remote_upgrade.sh
./remote_upgrade.sh
```

---

## 🔍 升级后验证

### 基础检查

```bash
# 1. 检查应用状态
curl http://localhost:5001

# 2. 检查进程
ps aux | grep "python.*app.py"

# 3. 检查端口
lsof -i:5001

# 4. 查看日志
tail -f /tmp/flask.log
```

### 功能验证

```bash
# 运行完整验证
./verify_upgrade.sh
```

### 手动测试

访问您的服务器并测试：

1. **首页**: http://your-server-ip:5001
   - 检查CSS是否正常加载
   - 查看页面源代码，CSS/JS应该带 `?v=hash` 参数

2. **文章页面**: http://your-server-ip:5001/post/1
   - 应该看到面包屑导航

3. **登录页面**: http://your-server-ip:5001/login
   - 登录后编辑文章，30秒应该自动保存

---

## 🆘 常见问题

### 1. Git pull失败

**问题**: 本地有未提交的修改

**解决**:
```bash
# 暂存本地修改
git stash

# 拉取代码
git pull origin main

# 恢复修改（如需要）
git stash pop
```

### 2. 虚拟环境问题

**问题**: Python版本不兼容或模块缺失

**解决**:
```bash
# 删除旧虚拟环境
rm -rf .venv

# 创建新虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 重新安装依赖
pip install -r backend/requirements.txt
```

### 3. 数据库迁移失败

**问题**: 表已存在或权限错误

**解决**:
```bash
# 检查数据库权限
ls -la db/simple_blog.db

# 手动检查表
sqlite3 db/simple_blog.db ".tables"

# 删除旧表重新创建（谨慎！）
sqlite3 db/simple_blog.db "DROP TABLE IF EXISTS drafts; DROP TABLE IF EXISTS optimized_images;"

# 重新运行迁移
python3 backend/migrations/migrate_drafts.py
python3 backend/migrations/migrate_image_optimization.py
```

### 4. 应用启动失败

**问题**: 端口被占用或依赖缺失

**解决**:
```bash
# 查看错误日志
tail -100 /tmp/flask.log

# 检查端口占用
lsof -i:5001
# 或
netstat -tlnp | grep 5001

# 杀死占用进程
kill -9 $(lsof -ti:5001)

# 重新启动
export DATABASE_URL="sqlite:///db/simple_blog.db"
nohup python3 backend/app.py > /tmp/flask.log 2>&1 &
```

### 5. 静态资源404

**问题**: CSS/JS文件无法加载

**解决**:
```bash
# 重新生成manifest
python3 generate_manifest.py

# 检查文件权限
chmod -R 755 static/

# 重启应用
pkill -f "python.*app.py"
# ... 启动应用
```

---

## 🔄 回滚方法

如果升级后出现问题：

```bash
# 1. 停止应用
pkill -f "python.*app.py"

# 2. 恢复数据库
cp backups/pre_upgrade_YYYYMMDD_HHMMSS/simple_blog.db db/simple_blog.db

# 3. 回退代码
git log --oneline -10  # 查看提交历史
git reset --hard <旧版本的commit-hash>

# 4. 重启应用
# ... 使用原来的启动命令
```

或使用回滚脚本：
```bash
./rollback.sh backups/pre_upgrade_<timestamp>
```

---

## 📊 升级清单

在远程服务器上执行升级前，请确认：

- [ ] 已通知用户维护时间（生产环境）
- [ ] 服务器有足够磁盘空间（至少500MB）
- [ ] Python 3.8+ 已安装
- [ ] 有数据库备份
- [ ] 知道如何回滚
- [ ] 已阅读 UPGRADE_GUIDE.md

---

## 🎯 升级后检查

升级完成后，请检查：

- [ ] 应用正常运行（端口5001）
- [ ] 首页可访问
- [ ] CSS/JS正常加载
- [ ] 文章页面显示面包屑
- [ ] 登录功能正常
- [ ] 草稿自动保存工作
- [ ] 日志无错误信息

---

## 📞 获取帮助

如果遇到问题：

1. **查看日志**
   ```bash
   tail -f /tmp/flask.log
   ```

2. **运行验证**
   ```bash
   ./verify_upgrade.sh
   ```

3. **查看完整文档**
   ```bash
   cat UPGRADE_GUIDE.md
   ```

4. **回滚**
   ```bash
   ./rollback.sh backups/upgrade_<timestamp>
   ```

---

## ✨ 升级完成后的新功能

升级成功后，您将拥有：

1. **⌨️ 更快的编辑体验** - 键盘快捷键
2. **🍞 更好的导航** - 面包屑导航
3. **💾 数据安全** - 自动保存草稿
4. **🖼️ 更快的加载** - 图片自动优化
5. **🔝 无缓存问题** - 静态资源版本化

祝您升级顺利！🚀
