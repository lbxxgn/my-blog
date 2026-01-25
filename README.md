# Simple Personal Blog System

一个简洁、优雅的个人博客系统，基于 Flask 和 SQLite 构建。适合记录日常随笔和个人思考。

## ✨ 功能特性

### 核心功能
- ✅ 简洁优雅的设计，专注于阅读体验
- ✅ 富文本编辑器（Quill WYSIWYG，支持粘贴保持格式）
- ✅ 图片上传功能，支持拖拽上传
- ✅ 响应式设计，完美适配 PC 和移动端
- ✅ 身份验证的管理后台
- ✅ 草稿和发布状态管理（前端自动保存）
- ✅ 一键发布功能
- ✅ 中国时区支持（UTC+8自动转换）

### 内容管理
- ✅ 文章分类管理
- ✅ 标签系统（多标签支持，热门标签展示）
- ✅ 批量设置分类
- ✅ 批量删除文章
- ✅ 后端分页（10/20/40/80 条可选）
- ✅ 分类筛选（前端+后端）
- ✅ 标签筛选
- ✅ 文章导出（Markdown + JSON格式）
- ✅ 修改密码功能
- ✅ 网易博客数据导入
- ✅ 智能头部（自动隐藏/显示）

### 用户互动
- ✅ 评论系统（支持评论管理）
- ✅ 文章分享（微博、微信二维码、复制链接）

### 用户体验
- ✅ 暗黑模式（支持主题切换）
- ✅ 增强图片懒加载（Intersection Observer）
- ✅ 骨架屏加载动画（渐进式淡入）
- ✅ AJAX 分页（加载更多按钮）
- ✅ 移动端优化（触摸友好、响应式布局）

### 搜索与安全
- ✅ FTS5 全文搜索
- ✅ CSRF 保护
- ✅ 密码强度验证
- ✅ Session 安全配置

### 开发与运维
- ✅ 完整日志系统（login.log, operation.log, error.log, sql.log）
- ✅ 友好错误页面
- ✅ 数据库索引优化
- ✅ 数据库备份工具（导出功能）

## 🛠 技术栈

- **后端**: Python Flask 3.0.0
- **数据库**: SQLite (FTS5 全文搜索)
- **前端编辑器**: Quill (富文本WYSIWYG)
- **前端框架**: 纯 CSS/JS (无框架依赖)
- **模板引擎**: Jinja2
- **Markdown**: markdown2 库
- **时区处理**: pytz (中国时区UTC+8)
- **安全**: Flask-WTF (CSRF 保护)
- **其他**: qrcode (微信分享二维码)
- **部署**: 简单的单命令启动

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

```bash
cd backend
python app.py
```

首次运行会自动：
- 创建数据库表
- 创建默认管理员账号（admin/admin123）

### 3. 访问博客

- 博客首页: http://localhost:5001
- 管理后台: http://localhost:5001/admin
- 登录页面: http://localhost:5001/login

**默认账号:**
- 用户名: `admin`
- 密码: `admin123`

⚠️ **重要**: 首次登录后请立即修改密码！

## 📁 项目结构

```
simple-blog/
├── backend/              # 后端代码
│   ├── app.py           # Flask 应用主文件
│   ├── models.py        # 数据库模型
│   ├── config.py        # 配置文件
│   ├── logger.py        # 日志系统
│   └── import_blog.py   # 网易博客导入工具
├── db/                  # 数据库文件
│   ├── posts.db         # SQLite 数据库（自动创建）
│   └── .gitkeep         # 保持目录被 git 跟踪
├── logs/                # 日志目录
│   ├── login.log        # 登录日志
│   ├── operation.log    # 操作日志
│   ├── error.log        # 错误日志
│   └── sql.log          # SQL 操作日志
├── static/              # 静态资源
│   ├── css/
│   │   └── style.css    # 样式表
│   ├── js/
│   │   ├── main.js      # 主要 JavaScript
│   │   └── editor.js    # 编辑器 JavaScript
│   └── uploads/         # 上传的图片
├── templates/           # HTML 模板
│   ├── base.html        # 基础模板
│   ├── index.html       # 首页
│   ├── post.html        # 文章详情页
│   ├── login.html       # 登录页
│   ├── change_password.html  # 修改密码页
│   ├── error.html       # 错误页面
│   └── admin/           # 管理后台模板
│       ├── dashboard.html    # 文章管理
│       ├── editor.html       # 文章编辑器
│       └── categories.html   # 分类管理
├── requirements.txt     # Python 依赖
└── README.md           # 项目文档
```

## 📝 使用指南

### 创建文章

1. 登录后台（`/login`）
2. 点击"管理"进入后台
3. 点击"新建文章"按钮
4. 输入标题和内容（支持 Markdown）
5. 可选：选择分类、添加标签
6. 点击"立即发布"直接发布，或"保存"存为草稿

### 编辑文章

1. 在文章管理页点击"编辑"
2. 修改内容后点击"保存"
3. 已发布的文章会保持发布状态

### 批量操作

1. 在文章管理页勾选多篇文章
2. 点击"批量设置分类"或"批量删除"
3. 批量删除需要二次确认

### 标签管理

1. 编辑文章时可以添加多个标签
2. 在首页点击标签可以筛选相关文章
3. 标签以多对多关系关联文章

### 评论管理

1. 游客可以在文章页发表评论
2. 管理员可以隐藏/显示评论
3. 支持删除不当评论

### 修改密码

1. 登录后点击顶部导航"修改密码"
2. 输入当前密码和新密码
3. 确认修改

### 导入网易博客

如果有网易博客的 XML 导出文件：

```bash
python backend/import_blog.py
```

会自动导入所有文章、分类和发布状态。

## 📖 Markdown 语法

```markdown
# 一级标题
## 二级标题

**粗体文本**
*斜体文本*

`行内代码`

[链接文字](url)

![图片描述](/static/uploads/image.jpg)

---

- 列表项 1
- 列表项 2

1. 有序列表 1
2. 有序列表 2
```

## ⚙️ 配置说明

编辑 `backend/config.py` 可自定义：

### 基础配置

- `SECRET_KEY`: Flask 密钥（生产环境请修改）
- `DATABASE_URL`: 数据库路径
- `DEBUG`: 调试模式（开发环境设为 True）

### 网站设置

- `SITE_NAME`: 网站名称（默认："我的博客"）
- `SITE_DESCRIPTION`: 网站描述（默认："一个简单的博客系统"）
- `SITE_AUTHOR`: 网站作者（默认："管理员"）

这些设置会在以下地方显示：
- 网站标题栏（浏览器标签）
- 导航栏的网站名称
- 页面元信息

### 文件上传配置

- `UPLOAD_FOLDER`: 图片上传目录（默认：`static/uploads/`）
- `MAX_CONTENT_LENGTH`: 最大上传大小（默认：16MB）
- `ALLOWED_EXTENSIONS`: 允许的图片类型（png, jpg, jpeg, gif, webp）

### 修改网站名称

**方法 1：直接修改配置文件**

编辑 `backend/config.py`：

```python
SITE_NAME = os.environ.get('SITE_NAME') or '你的博客名称'
SITE_DESCRIPTION = os.environ.get('SITE_DESCRIPTION') or '你的博客描述'
SITE_AUTHOR = os.environ.get('SITE_AUTHOR') or '你的名字'
```

修改后重启服务器即可生效。

**方法 2：使用环境变量（推荐）**

```bash
export SITE_NAME="技术博客"
export SITE_DESCRIPTION="分享技术与生活"
export SITE_AUTHOR="张三"
python backend/app.py
```

或者创建 `.env` 文件：

```bash
# .env
SITE_NAME=技术博客
SITE_DESCRIPTION=分享技术与生活
SITE_AUTHOR=张三
```

然后在启动时加载：

```bash
export $(cat .env | xargs)
python backend/app.py
```

### 日志系统

系统会自动记录以下日志（存储在 `logs/` 目录）：

- `login.log` - 登录成功/失败记录
- `operation.log` - 用户操作记录
- `error.log` - 错误信息和堆栈跟踪
- `sql.log` - SQL 操作记录

日志文件按天轮转，保留 30 天。

### 环境变量配置

可通过环境变量覆盖配置：

```bash
export SECRET_KEY="your-secret-key"
export ADMIN_USERNAME="your-username"
export ADMIN_PASSWORD="your-password"
```

## 🌐 部署

### 本地开发

```bash
cd backend
python app.py
```

访问: http://localhost:5001

**注意**: macOS 系统默认使用端口 5000（ControlCenter），因此本应用使用端口 5001。可以通过环境变量 `PORT` 修改端口。

### 远程服务器部署

**方法 1：使用启动脚本（推荐）**

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd simple-blog

# 2. 安装依赖
pip3 install -r requirements.txt

# 3. 使用启动脚本运行
chmod +x start.sh
./start.sh
```

**方法 2：直接运行**

```bash
# 1. 进入 backend 目录
cd backend

# 2. 设置环境变量
export FLASK_APP=app.py
export FLASK_ENV=production
export PYTHONPATH=$(pwd):$PYTHONPATH

# 3. 启动应用
python3 app.py
```

**访问地址**: `http://your-server-ip:5001`

**防火墙配置**：确保开放 5001 端口
```bash
# 阿里云 ECS 需要在安全组中开放 5001 端口
# 或者使用 iptables
sudo iptables -A INPUT -p tcp --dport 5001 -j ACCEPT
```

### 生产部署

推荐使用 Gunicorn + nginx：

```bash
# 安装 gunicorn
pip install gunicorn

# 启动服务
gunicorn -w 4 -b 0.0.0.0:5001 backend.app:app
```

**nginx 配置示例:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /path/to/simple-blog/static;
    }
}
```

## 💾 备份

备份博客数据：

```bash
# 备份数据库和上传文件
tar czf blog-backup-$(date +%Y%m%d).tar.gz db/posts.db static/uploads/

# 或使用 git
git add .
git commit -m "backup"
git push
```

## 🔧 常见问题

### 忘记密码？

使用环境变量设置新密码：

```bash
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="new_password"
python backend/app.py
```

### 数据库出错？

删除数据库文件重新初始化：

```bash
rm db/posts.db
python backend/app.py
```

### 图片上传失败？

检查 `static/uploads` 目录权限：

```bash
chmod 755 static/uploads
```

## 📊 功能截图

- 干净简洁的首页设计
- 响应式文章列表
- 实时预览编辑器
- 便捷的管理后台
- 分类管理界面
- 批量操作功能

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License

## 👨‍💻 作者

Created with ❤️ for personal blogging

**GitHub**: https://github.com/lbxxgn/my-blog

---

## 更新日志

### v1.2.0 (2025-01-24)
- ✨ 新增标签系统（多标签支持）
- ✨ 新增评论系统
- ✨ 新增文章分享功能（微博、微信、复制链接）
- ✨ 新增暗黑模式
- ✨ 新增图片懒加载和骨架屏动画
- ✨ 新增 AJAX 分页（加载更多按钮）
- ✨ 新增 FTS5 全文搜索
- ✨ 新增批量删除功能
- ✨ 新增日志系统（4种日志类型）
- ✨ 新增友好错误页面
- ✨ 新增 CSRF 保护
- ✨ 优化数据库索引
- ✨ 修复 FTS 触发器冲突问题

### v1.1.0 (2025-01-23)
- ✅ 批量设置分类功能
- ✅ 分类筛选功能
- ✅ 后端分页优化
- ✅ 网易博客导入功能

### v1.0.0 (2025-01-22)
- ✨ 初始版本发布
- ✅ 基础博客功能
- ✅ 文章 CRUD 操作
- ✅ 响应式设计

## ❓ 常见问题 (FAQ)

### 1. 如何修改默认密码？
登录后台后，访问 http://localhost:5001/admin/change-password 修改密码。

### 2. 如何导出文章备份？
访问管理后台 → 点击"数据导出" → 选择导出格式（Markdown或JSON）。

### 3. 图片存储在哪里？
图片默认存储在 `static/uploads/` 目录。

### 4. 如何从网易博客导入数据？
将网易博客导出的 XML 文件放在项目根目录，然后运行：
```bash
python backend/import_blog.py 网易博客日志列表.xml
```

### 5. 如何开启调试模式？
修改 `backend/config.py`，设置 `DEBUG = True`。

### 6. 数据库在哪里？
数据库文件位于 `db/posts.db`。

### 7. 如何备份数据库？
```bash
cp db/posts.db db/posts_backup_$(date +%Y%m%d).db
```

### 8. 如何查看日志？
日志文件位于 `logs/` 目录：
- `login.log` - 登录日志
- `operation.log` - 操作日志
- `error.log` - 错误日志
- `sql.log` - SQL查询日志

### 9. 时区显示不正确怎么办？
系统已内置中国时区（UTC+8）支持。如果仍有问题，检查系统时区设置。

### 10. 标签不显示文章数量？
标签管理页面已更新显示文章数量。如果为0，说明没有文章关联该标签。

## 🔧 进一步优化

详细的优化指南请参考：[OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md)

包含内容：
- 已完成的优化说明
- 数据库性能优化（游标分页）
- 代码重构建议
- 性能对比

## 📝 更新日志

### v3.3 (2026-01-25)
- ✅ 增强骨架屏加载动画
- ✅ 优化图片懒加载
- ✅ 添加文章导出功能（Markdown + JSON）
- ✅ 管理后台移动端优化
- ✅ 中国时区支持（UTC+8）
- ✅ 标签系统增强（显示文章数量）
- ✅ 首页热门标签侧边栏

### v3.0 (2025-01-24)
- 集成 Quill 富文本编辑器
- 移动端导航优化
- 暗黑模式改进

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**Made with ❤️ by Simple Blog Team**
