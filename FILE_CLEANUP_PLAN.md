# 根目录文件清理方案

## 📊 当前问题

根目录有太多文件，包括：
- **脚本文件散落**: 6个shell/python脚本
- **敏感文件泄露风险**: cookies.txt 已被git跟踪
- **临时文件未清理**: 1.8MB的XML文件、日志等
- **生成文件被跟踪**: simple-blog.service 应从模板生成

## 🔍 详细分析

### ✅ 应该保留（核心文件）

| 文件 | 大小 | 说明 |
|------|------|------|
| README.md | 4.4KB | 项目主页 |
| QUICKSTART.md | 1.8KB | 快速开始 |
| DEPLOYMENT.md | 10KB | 部署指南 |
| requirements.txt | 210B | Python依赖 |
| pytest.ini | 530B | 测试配置 |
| .gitignore | 988B | Git配置 |
| .env.example | 2.8KB | 环境变量模板 |
| simple-blog.service.example | 2.4KB | systemd服务模板 |

### 📦 应该移到 scripts/（脚本整理）

| 文件 | 大小 | 用途 |
|------|------|------|
| start.sh | 3.9KB | 启动脚本 |
| install-service.sh | 4.1KB | 服务安装 |
| upgrade.sh | 12KB | 升级脚本 |
| rollback.sh | 6.4KB | 回滚脚本 |
| verify_upgrade.sh | 11.9KB | 验证脚本 |
| generate_manifest.py | 1.7KB | 生成manifest |

**操作**: 创建 scripts/ 目录，使用 `git mv` 移动

### ❌ 应该从Git删除（敏感/临时文件）

| 文件 | 大小 | 问题 | 处理方式 |
|------|------|------|----------|
| cookies.txt | 131B | **敏感信息** | `git rm --cached` |
| simple-blog.service | 1.1KB | 生成文件 | `git rm` |
| generate-icon.html | 3.7KB | 临时工具 | `git rm` |

### 🗑️ 应该删除（本地临时文件）

| 文件 | 大小 | 说明 |
|------|------|------|
| 网易博客日志列表.xml | 1.8MB | **巨大临时文件！** |
| blog.db | 0B | 空数据库文件 |
| server-test.log | 10.6KB | 日志文件 |
| .coverage | 53KB | 测试覆盖率 |
| .DS_Store | 12.3KB | macOS系统文件 |

## 🎯 清理方案

### 步骤1: 创建 scripts/ 并移动脚本

```bash
# 创建目录
mkdir -p scripts

# 移动脚本文件
git mv start.sh scripts/
git mv install-service.sh scripts/
git mv upgrade.sh scripts/
git mv rollback.sh scripts/
git mv verify_upgrade.sh scripts/
git mv generate_manifest.py scripts/
```

### 步骤2: 从Git删除敏感/临时文件

```bash
# 从Git删除但仍保留本地（如需要）
git rm --cached cookies.txt
git rm simple-blog.service
git rm generate-icon.html

# 删除本地临时文件
rm -f 网易博客日志列表.xml
rm -f blog.db
rm -f server-test.log
rm -f .coverage
rm -f .DS_Store
```

### 步骤3: 更新 .gitignore

确保以下条目已存在（已有）：
- `.env`
- `*.db`
- `server-test.log`
- `.coverage`
- `.DS_Store`
- `*.xml`
- `网易博客日志列表.xml`

### 步骤4: 创建 scripts/README.md

```markdown
# 项目脚本

此目录包含项目维护和部署相关的脚本。

## 脚本说明

### 🚀 启动和安装
- `start.sh` - 快速启动开发服务器
- `install-service.sh` - 安装systemd服务

### 🔄 升级和维护
- `upgrade.sh` - 系统升级脚本
- `rollback.sh` - 回滚到上一版本
- `verify_upgrade.sh` - 验证升级结果

### 🔧 工具脚本
- `generate_manifest.py` - 生成静态资源manifest

## 使用方法

详见 [部署指南](../DEPLOYMENT.md)
```

### 步骤5: 更新文档引用

在以下文档中更新脚本路径：
- DEPLOYMENT.md: `./upgrade.sh` → `./scripts/upgrade.sh`
- docs/startup.md: 更新所有脚本路径
- docs/upgrade.md: 更新所有脚本路径

## ⚠️ 安全警告

**cookies.txt** 已被Git跟踪，可能包含敏感信息！

**紧急操作**：
```bash
# 1. 立即从Git历史删除
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch cookies.txt" HEAD

# 2. 强制推送（⚠️ 谨慎操作）
git push origin --force --all
```

或者如果只是最近提交：
```bash
# 从最新提交删除
git rm --cached cookies.txt
git commit --amend --no-edit
git push origin --force
```

## 📊 清理效果

| 指标 | 清理前 | 清理后 | 改进 |
|------|--------|--------|------|
| 根目录文件 | 25个 | 8个 | ↓68% |
| 脚本分散 | 6个位置 | 1个目录 | 集中化 |
| Git仓库大小 | ~2MB | ~200KB | ↓90% |
| 敏感文件风险 | 高 | 无 | 安全 |

## ✅ 清理后根目录

只保留：
- README.md
- QUICKSTART.md
- DEPLOYMENT.md
- requirements.txt
- pytest.ini
- .gitignore
- .env.example
- simple-blog.service.example

## 🚀 执行建议

建议执行顺序：
1. **紧急**: 删除 cookies.txt（安全问题）
2. **重要**: 创建 scripts/ 并移动脚本
3. **可选**: 删除临时文件
4. **最后**: 更新文档引用
