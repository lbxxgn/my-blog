# 🚀 快速升级参考

## 一行命令升级

```bash
chmod +x upgrade.sh verify_upgrade.sh rollback.sh && ./upgrade.sh && ./verify_upgrade.sh
```

## 分步升级

```bash
# 1️⃣ 赋予权限
chmod +x *.sh

# 2️⃣ 执行升级
./upgrade.sh

# 3️⃣ 验证结果
./verify_upgrade.sh
```

## 如果失败，回滚

```bash
# 查看备份
ls -lt backups/

# 回滚
./rollback.sh backups/upgrade_<TIMESTAMP>
```

## 快速检查

```bash
# 应用状态
lsof -ti:5001

# 查看日志
tail -f /tmp/flask.log

# 访问测试
curl http://127.0.0.1:5001
```

## 访问地址

- 首页: http://127.0.0.1:5001
- 登录: http://127.0.0.1:5001/login
- 管理: http://127.0.0.1:5001/admin

## 新功能测试

| 功能 | 测试方法 | 预期结果 |
|------|----------|----------|
| ⌨️ 快捷键 | 按 `Ctrl+N` | 跳转新建文章 |
| 🍞 面包屑 | 访问文章页 | 显示: 首页 > 分类 > 标题 |
| 💾 草稿 | 登录后编辑 | 30秒自动保存 |
| 🖼️ 图片优化 | 上传图片 | 生成3个尺寸 |
| 🔍 资源版本 | 查看页面源 | CSS/JS带 ?v=hash |

## 文件清单

```
✓ upgrade.sh           - 升级脚本
✓ rollback.sh          - 回滚脚本
✓ verify_upgrade.sh    - 验证脚本
✓ UPGRADE_GUIDE.md     - 完整指南
```

## 常见问题

**Q: 升级失败？**
```bash
# 检查日志
tail -50 /tmp/flask.log

# 重试升级
./upgrade.sh
```

**Q: 静态资源404？**
```bash
# 重新生成manifest
python3 generate_manifest.py

# 重启应用
lsof -ti:5001 | xargs kill -9
./upgrade.sh  # 只执行启动部分
```

**Q: 应用无法启动？**
```bash
# 检查端口
lsof -ti:5001

# 检查Python
python3 --version

# 检查依赖
source .venv/bin/activate
pip list
```

## 获取帮助

```bash
# 查看完整文档
cat UPGRADE_GUIDE.md

# 运行详细验证
./verify_upgrade.sh
```

---

**升级愉快！** 🎉
