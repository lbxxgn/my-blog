# Simple Blog

简洁、优雅的个人博客系统 + 知识库管理

## 快速开始

```bash
git clone https://github.com/lbxxgn/my-blog.git
cd simple-blog
cp .env.example .env
# 编辑 .env 设置管理员密码
pip install -r requirements.txt
python backend/app.py
```

访问 http://localhost:5001，默认用户：admin

## 主要功能

### 博客功能
- **富文本编辑**：Quill编辑器，支持粘贴保持格式
- **多用户系统**：支持admin/editor/author三种角色
- **分类和标签**：灵活的内容组织
- **评论系统**：支持评论管理
- **全文搜索**：FTS5全文搜索
- **访问控制**：公开/登录用户/密码保护/私密

### 知识库
- **卡片管理**：想法、孵化、草稿状态
- **时间线视图**：按时间查看所有内容
- **浏览器扩展**：一键采集网页内容
- **AI辅助**：智能标签生成、内容合并

### AI功能
- **标签生成**：自动为文章生成相关标签
- **摘要生成**：一键生成文章摘要
- **相关推荐**：基于内容推荐相关文章
- **内容续写**：智能续写文章内容
- **多提供商支持**：OpenAI / 火山引擎 / 阿里百炼

### 用户体验
- **暗黑模式**：优化的深色主题
- **响应式设计**：完美适配PC和移动端
- **图片灯箱**：点击放大、键盘导航
- **代码复制**：一键复制代码块
- **加载动画**：骨架屏、渐进式淡入

### 新功能（v2.2）

#### ⌨️ 键盘快捷键
- Ctrl+K: 快速搜索
- Ctrl+N: 新建文章
- Ctrl+/: 查看所有快捷键
- 编辑器: Ctrl+B (加粗), Ctrl+I (斜体)

#### 💾 多设备草稿同步
- 编辑器每30秒自动保存
- 多设备编辑时自动检测冲突
- 支持草稿恢复和合并

#### 🖼️ 图片自动优化
- 上传图片后自动压缩
- 生成多种尺寸（缩略图、中等、大图）
- 转换为WebP格式，平均减少85%大小

#### 🍞 面包屑导航
- 文章页显示导航路径
- SEO优化的结构化数据

#### ⚡ 性能优化
- 静态资源自动版本管理
- 响应式图片加载

## 技术栈

- **后端**：Flask 3.0 + SQLite
- **前端**：Vanilla JS + Quill编辑器
- **AI**：OpenAI API / 火山引擎 / 阿里百炼
- **测试**：pytest + pytest-cov

## 项目结构

```
simple-blog/
├── backend/              # 后端代码
│   ├── models/          # 数据模型
│   ├── routes/          # 路由模块
│   ├── ai_services/     # AI服务
│   └── app.py           # 应用入口
├── templates/           # HTML模板
├── static/              # 静态资源
│   ├── css/            # 样式文件
│   └── js/             # JavaScript
├── browser-extension/   # 浏览器扩展
├── tests/              # 测试代码
└── docs/               # 文档
```

## 文档

- [完整启动指南](STARTUP.md)
- [数据库迁移](MIGRATION.md)
- [系统部署](SYSTEMD_DEPLOYMENT.md)
- [浏览器扩展](browser-extension/README.md)

## 开发

```bash
# 运行测试
pytest tests/ -v

# 查看测试覆盖率
pytest --cov=backend --cov-report=html

# 启动开发服务器
python backend/app.py
```

## 部署

项目支持多种部署方式：

- **开发环境**：直接运行 `python backend/app.py`
- **生产环境**：使用 systemd 服务（参考 [SYSTEMD_DEPLOYMENT.md](SYSTEMD_DEPLOYMENT.md)）
- **Docker**：（待实现）

## 环境变量

主要环境变量（见 `.env.example`）：

```bash
SECRET_KEY=your-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# AI配置（可选）
AI_PROVIDER=openai
OPENAI_API_KEY=your-api-key
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v2.2 (2026-03-13)
- 新增键盘快捷键系统
- 新增多设备草稿同步
- 新增图片自动优化
- 新增面包屑导航
- 新增静态资源自动版本管理

### v2.1 (2026-01-31)
- 新增知识库功能（卡片、时间线、孵化器）
- 新增浏览器扩展（网页内容采集）
- 新增AI辅助功能（标签生成、内容合并）
- 优化暗黑模式
- 改进用户体验（快速记事、草稿恢复）

### v2.0
- 富文本编辑器
- 多用户系统
- AI标签生成
- 暗黑模式

### v1.0
- 基础博客功能
- 评论系统
- 全文搜索
