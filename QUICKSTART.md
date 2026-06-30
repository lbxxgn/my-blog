# 🚀 快速参考

## 环境准备

```bash
git clone https://github.com/lbxxgn/my-blog.git
cd my-blog
cp .env.example .env
# 编辑 .env 设置管理员密码和 SECRET_KEY
pip install -r requirements.txt
```

## 构建新版知识库编辑器

首次运行或前端源码变更后需要构建：

```bash
cd frontend
npm install
npm run build
cd ..
```

构建产物输出到 `static/frontend/`，Flask 通过 `backend/app.py` 中的 `vite_asset()` 读取 `static/frontend/.vite/manifest.json`。

## 一行命令升级

```bash
chmod +x scripts/*.sh && ./scripts/upgrade.sh && ./scripts/verify_upgrade.sh
```

## 分步升级

```bash
# 1️⃣ 赋予权限
chmod +x scripts/*.sh

# 2️⃣ 执行升级
./scripts/upgrade.sh

# 3️⃣ 验证结果
./scripts/verify_upgrade.sh
```

## 如果失败，回滚

```bash
# 查看备份
ls -lt backups/

# 回滚
./scripts/rollback.sh backups/upgrade_<TIMESTAMP>
```

## 启动服务

```bash
./scripts/start.sh
# 或直接运行
python backend/app.py
```

## 快速检查

```bash
# 应用状态
lsof -ti:5001

# 查看日志
tail -f logs/app.log logs/error.log

# 访问测试
curl http://127.0.0.1:5001
```

## 访问地址

- 首页: http://127.0.0.1:5001
- 登录: http://127.0.0.1:5001/login
- 管理后台: http://127.0.0.1:5001/admin
- 新版知识库: http://127.0.0.1:5001/knowledge

## 新功能测试

| 功能 | 测试方法 | 预期结果 |
|------|----------|----------|
| ⌨️ 快捷键 | 按 `Ctrl+N` | 跳转新建文章 |
| 🍞 面包屑 | 访问文章页 | 显示: 首页 > 分类 > 标题 |
| 💾 草稿 | 登录后编辑 | 30 秒自动保存 |
| 🖼️ 图片优化 | 上传图片 | 生成多个尺寸 |
| 🔍 资源版本 | 查看页面源 | CSS/JS 带版本参数 |
| 📝 KB 编辑器 | 访问 `/knowledge` | 加载 React 编辑器并可新建文档 |

### 知识库编辑器冒烟测试

```bash
# API 测试
pytest tests/test_kb_editor_api.py -v

# E2E 测试
pytest tests/e2e_kb_editor.py -v
```

## 文件清单

```
✓ scripts/start.sh          - 启动脚本
✓ scripts/upgrade.sh        - 升级脚本
✓ scripts/rollback.sh       - 回滚脚本
✓ scripts/verify_upgrade.sh - 验证脚本
✓ scripts/install-service.sh - systemd 服务安装
✓ scripts/generate_manifest.py - 静态资源清单生成
```

## 常见问题

**Q: 升级失败？**
```bash
# 检查日志
tail -50 logs/error.log

# 重试升级
./scripts/upgrade.sh
```

**Q: 静态资源 404？**
```bash
# 重新生成 manifest
python3 scripts/generate_manifest.py

# 重启应用
lsof -ti:5001 | xargs kill -9
./scripts/upgrade.sh  # 只执行启动部分
```

**Q: 新版知识库编辑器空白？**
```bash
# 重新构建前端
cd frontend && npm install && npm run build && cd ..
# 确认 static/frontend/.vite/manifest.json 存在
ls static/frontend/.vite/manifest.json
```

**Q: 应用无法启动？**
```bash
# 检查端口
lsof -ti:5001

# 检查 Python
python3 --version

# 检查依赖
source .venv/bin/activate
pip list
```

## 获取帮助

```bash
# 运行详细验证
./scripts/verify_upgrade.sh

# 查看完整文档索引
cat docs/README.md
```

---

**升级愉快！** 🎉
