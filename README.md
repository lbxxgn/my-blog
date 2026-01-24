# Simple Personal Blog System

一个简洁、优雅的个人博客系统，基于 Flask 和 SQLite 构建。适合记录日常随笔和个人思考。

## ✨ 功能特性

### 核心功能
- ✅ 简洁优雅的设计，专注于阅读体验
- ✅ Markdown 格式支持，写作更方便
- ✅ 图片上传功能，支持拖拽上传
- ✅ 响应式设计，完美适配 PC 和移动端
- ✅ 身份验证的管理后台
- ✅ 草稿和发布状态管理
- ✅ 一键发布功能

### 增强功能
- ✅ 文章分类管理
- ✅ 批量设置分类
- ✅ 后端分页（10/20/40/80 条可选）
- ✅ 分类筛选（前端+后端）
- ✅ 修改密码功能
- ✅ 网易博客数据导入
- ✅ 智能头部（自动隐藏/显示）
- ✅ 实时预览编辑器

## 🛠 技术栈

- **后端**: Python Flask 3.x
- **数据库**: SQLite
- **前端**: Jinja2 模板, 纯 CSS/JS
- **Markdown**: markdown2 库
- **部署**: 简单的单命令启动

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

```bash
python backend/app.py
```

首次运行会自动：
- 创建数据库表
- 创建默认管理员账号（admin/admin123）

### 3. 访问博客

- 博客首页: http://localhost:5000
- 管理后台: http://localhost:5000/admin
- 登录页面: http://localhost:5000/login

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
│   └── import_blog.py   # 网易博客导入工具
├── db/                  # 数据库文件
│   ├── posts.db         # SQLite 数据库（自动创建）
│   └── .gitkeep         # 保持目录被 git 跟踪
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
5. 可选：选择分类
6. 点击"立即发布"直接发布，或"保存"存为草稿

### 编辑文章

1. 在文章管理页点击"编辑"
2. 修改内容后点击"保存"
3. 已发布的文章会保持发布状态

### 批量设置分类

1. 在文章管理页勾选多篇文章
2. 点击"批量设置分类"
3. 选择目标分类
4. 确认完成批量更新

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

- `SECRET_KEY`: Flask 密钥（生产环境请修改）
- `DATABASE_URL`: 数据库路径
- `UPLOAD_FOLDER`: 图片上传目录
- `MAX_CONTENT_LENGTH`: 最大上传大小（默认 5MB）
- `ALLOWED_EXTENSIONS`: 允许的图片类型（png, jpg, jpeg, gif, webp）

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
python backend/app.py
```

访问: http://localhost:5000

### 生产部署

推荐使用 Gunicorn + nginx：

```bash
# 安装 gunicorn
pip install gunicorn

# 启动服务
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
```

**nginx 配置示例:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
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

### v1.0.0 (2025-01-24)
- ✨ 初始版本发布
- ✅ 基础博客功能
- ✅ 分类管理
- ✅ 批量操作
- ✅ 分页功能
- ✅ 网易博客导入
- ✅ 响应式设计
