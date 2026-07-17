# Simple Blog API 文档

**版本**: v2.3
**最后更新**: 2026-06-28
**基础URL**: `http://your-domain.com`

---

## 📋 目录

- [认证](#认证)
- [Passkey 认证](#passkey-认证)
- [文章API](#文章api)
- [分类与标签API](#分类与标签api)
- [评论API](#评论api)
- [搜索API](#搜索api)
- [用户管理API](#用户管理api)
- [知识库API](#知识库api)
- [AI功能API](#ai功能api)
- [文件上传API](#文件上传api)
- [草稿API](#草稿api)
- [新知识空间API](#新知识空间api)
- [导入导出API](#导入导出api)
- [工具API](#工具api)

---

## 🔐 认证

大部分API端点需要用户登录。使用Session Cookie进行认证。

### 登录

```http
POST /login
Content-Type: application/x-www-form-urlencoded
```

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |
| remember_device | string | 否 | 记住设备（"1"/"true"） |

**响应说明：**
- 成功时返回 HTTP 302 重定向到 `/admin`（或请求中安全的 `next` 参数）
- 失败时重新渲染登录页面
- 此端点返回 HTML 页面，不是 JSON

### 登出

```http
POST /logout
```

### 修改密码

```http
POST /change-password
```

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| current_password | string | 是 | 当前密码 |
| new_password | string | 是 | 新密码（至少10位） |
| confirm_password | string | 是 | 确认密码 |

---

## 🔑 Passkey 认证

无密码登录支持，使用 WebAuthn 标准。

### 开始注册 Passkey

```http
POST /passkeys/register/begin
```

**需要认证**: 是

**响应示例：**
```json
{
  "success": true,
  "options": {
    "rp": {
      "name": "Simple Blog",
      "id": "localhost"
    },
    "user": {
      "id": "...",
      "name": "username",
      "displayName": "username"
    },
    "challenge": "...",
    "pubKeyCredParams": [...]
  }
}
```

### 完成 Passkey 注册

```http
POST /passkeys/register/finish
```

**需要认证**: 是

**请求参数：**
```json
{
  "credential": {...},
  "device_name": "我的 iPhone"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "快捷登录已启用"
}
```

### 开始 Passkey 登录

```http
POST /passkeys/authenticate/begin
```

**响应示例：**
```json
{
  "success": true,
  "options": {
    "challenge": "...",
    "rpId": "localhost",
    "allowCredentials": [...]
  }
}
```

### 完成 Passkey 登录

```http
POST /passkeys/authenticate/finish
```

**请求参数：**
```json
{
  "credential": {...},
  "remember_device": true
}
```

**响应示例：**
```json
{
  "success": true,
  "redirect": "/admin"
}
```

### 获取 Passkey 列表

```http
GET /passkeys
```

**需要认证**: 是

**响应示例：**
```json
{
  "success": true,
  "passkeys": [
    {
      "id": 1,
      "device_name": "iPhone 13",
      "credential_device_type": "multi_device",
      "credential_device_type_label": "可同步设备",
      "backup_state": true,
      "created_at": "2026-03-01T10:00:00",
      "last_used_at": "2026-03-19T15:30:00"
    }
  ]
}
```

### 删除 Passkey

```http
DELETE /passkeys/{passkey_id}
```

**需要认证**: 是

---

## 📝 文章API

### 获取文章列表（游标分页）

```http
GET /api/posts?cursor={timestamp}&per_page={20}&category_id={1}
```

**查询参数：**
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| cursor | string | 否 | - | 基于时间的游标 |
| per_page | int | 否 | 20 | 每页数量（10/20/40/80） |
| category_id | int | 否 | - | 分类筛选 |

**响应示例：**
```json
{
  "success": true,
  "posts": [
    {
      "id": 123,
      "title": "文章标题",
      "content": "<p>文章内容</p>",
      "excerpt": "摘要内容",
      "author": "作者名",
      "created_at": "2026-03-16T10:30:00",
      "updated_at": "2026-03-16T10:30:00",
      "category_id": 1,
      "category_name": "技术",
      "tags": ["Python", "Flask"],
      "image_urls": ["/static/uploads/optimized/xxx_medium.webp"],
      "access_level": "public"
    }
  ],
  "next_cursor": "2026-03-15T08:00:00",
  "has_more": true,
  "per_page": 20
}
```

### 获取文章详情

```http
GET /post/{post_id}
```

**路径参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| post_id | int | 文章ID |

### 验证文章密码

```http
POST /post/{post_id}/verify-password
```

**请求参数：**
```json
{
  "password": "文章访问密码"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "密码验证成功",
  "redirect": "/post/123"
}
```

### 沉淀文章到知识库

```http
POST /post/{post_id}/precipitate
```

**需要认证**: 是

**请求参数：**
```json
{
  "category_id": 1
}
```

**响应示例：**
```json
{
  "success": true,
  "doc_id": 456,
  "redirect": "/knowledge/doc/456"
}
```

### 添加文章

```http
POST /admin/new
```

**需要认证**: 是

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| title | string | 是 | 文章标题 |
| content | string | 是 | 文章内容（HTML） |
| category_id | int | 否 | 分类ID |
| tags | string | 否 | 标签（逗号分隔） |
| is_published | bool | 否 | 是否发布 |
| access_level | string | 否 | 访问控制：public/login/password/private |
| access_password | string | 否 | 访问密码 |
| allow_comments | bool | 否 | 是否允许评论 |

### 编辑文章

```http
POST /admin/edit/{post_id}
```

**需要认证**: 是

**请求参数：** 同添加文章

### 删除文章

```http
POST /admin/delete/{post_id}
```

**需要认证**: 是

### 文章归档

```http
GET /archive?days={7}&year={2026}&month={3}
```

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| days | int | 最近N天（7/30/90/365） |
| year | int | 年份 |
| month | int | 月份 |

### 清除会话密码记录

```http
POST /clear-session
```

**响应示例：**
```json
{
  "success": true,
  "message": "Session已清除"
}

### 导入数据

#### 导入 JSON
```http
POST /admin/import/json
Content-Type: multipart/form-data
```

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| file | file | 是 | 导出的 JSON 文件 |

#### 导入 Markdown
```http
POST /admin/import/markdown
Content-Type: multipart/form-data
```

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| file | file | 是 | Markdown 文件或 ZIP 包 |
| category_id | int | 否 | 默认分类 |

### 导出数据

#### 导出 JSON
```http
GET /admin/export/json
```

**响应：** 下载 `blog_export_YYYYMMDD_HHMMSS.json`。

#### 导出 Markdown
```http
GET /admin/export/markdown
```

### 将文章转为知识库文档

```http
POST /post/{post_id}/precipitate
```

**需要认证**: 是

将博客文章沉淀为知识库文档，返回新文档的跳转地址。

**响应示例：**
```json
{
  "success": true,
  "redirect": "/knowledge/doc/456"
}
```
```

### 获取我的文章（移动端）

```http
GET /mobile/my-posts?tab={published}&page={1}
```

**需要认证**: 是

**查询参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| tab | string | published | published/drafts |
| page | int | 1 | 页码 |
| per_page | int | 10 | 每页数量（5/10/20/40） |

**响应示例：**
```json
{
  "success": true,
  "tab": "published",
  "posts": [
    {
      "id": 123,
      "title": "文章标题",
      "content": "...",
      "is_published": true,
      "created_at": "2026-03-19T10:00:00"
    }
  ],
  "page": 1,
  "total": 25,
  "total_pages": 3
}
```

### 批量操作

#### 批量更新分类

```http
POST /admin/batch-update-category
```

**需要认证**: 是

**请求参数：**
```json
{
  "post_ids": [1, 2, 3],
  "category_id": 5
}
```

#### 批量删除

```http
POST /admin/batch-delete
```

**需要认证**: 是

#### 批量发布/取消发布

```http
POST /admin/batch-publish
```

**需要认证**: 是

**请求参数：**
```json
{
  "post_ids": [1, 2, 3],
  "publish": true
}
```

#### 批量添加标签

```http
POST /admin/batch-add-tags
```

**需要认证**: 是

**请求参数：**
```json
{
  "post_ids": [1, 2, 3],
  "tags": ["Python", "Flask"]
}
```

#### 批量更新访问权限

```http
POST /admin/batch-update-access
```

**需要认证**: 是

**请求参数：**
```json
{
  "post_ids": [1, 2, 3],
  "access_level": "password",
  "access_password": "mypassword"
}
```

---

## 🏷️ 分类与标签API

### 获取所有分类

```http
GET /admin/categories
```

### 创建分类

```http
POST /admin/categories/new
```

**请求参数：**
```json
{
  "name": "分类名称"
}
```

### 删除分类

```http
POST /admin/categories/{category_id}/delete
```

### 获取所有标签

```http
GET /admin/tags
```

### 创建标签

```http
POST /admin/tags/new
```

**请求参数：**
```json
{
  "name": "标签名称"
}
```

### 删除标签

```http
POST /admin/tags/{tag_id}/delete
```

### 评论管理列表

```http
GET /admin/comments
```

**需要认证**: 是

---

## 💬 评论API

### 添加评论

```http
POST /post/{post_id}/comment
```

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| author_name | string | 是 | 评论者姓名 |
| author_email | string | 否 | 评论者邮箱 |
| content | string | 是 | 评论内容 |

**响应示例：**
```json
{
  "success": true,
  "message": "评论提交成功"
}
```

### 切换评论状态

```http
POST /admin/comments/{comment_id}/toggle
```

**需要认证**: 是

### 删除评论

```http
POST /admin/comments/{comment_id}/delete
```

**需要认证**: 是

---

## 🔍 搜索API

### 全文搜索

```http
GET /search?q={keyword}&page={1}&per_page={20}
```

**查询参数：**
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| q | string | 是 | - | 搜索关键词 |
| page | int | 否 | 1 | 页码 |
| per_page | int | 否 | 20 | 每页数量 |

---

## 👥 用户管理API

### 创建用户

```http
POST /admin/users/new
```

**需要认证**: 是（仅管理员）

**请求参数：**
```json
{
  "username": "newuser",
  "password": "SecurePassword123",
  "role": "author"
}
```

**角色选项：**
- `admin`: 管理员
- `editor`: 编辑
- `author`: 作者

### 编辑用户

```http
POST /admin/users/{user_id}/edit
```

### 删除用户

```http
POST /admin/users/{user_id}/delete
```

### 用户列表

```http
GET /admin/users
```

**需要认证**: 是（仅管理员）

---

## 📚 知识库API（旧版插件/卡片 API）

> 注意：以下端点已注册在 `/knowledge_base` 前缀下，其中浏览器扩展端点已豁免 CSRF 保护（使用 API Key 认证）。不存在 `/api/plugin/*` 的根路径别名，客户端必须以 `/knowledge_base` 为 base URL。

### 浏览器扩展 API

#### 验证 API Key

```http
POST /knowledge_base/api/plugin/validate
```

**认证**: API Key（`X-API-Key` 请求头）或 Session

**响应示例：**
```json
{
  "success": true,
  "user_id": 1
}
```

密钥无效或缺失时返回 `401`：`{"success": false, "error": "Invalid or missing API key"}`

#### 提交卡片/文章

```http
POST /knowledge_base/api/plugin/submit
```

**认证**: API Key 或 Session

**请求参数：**
```json
{
  "title": "页面标题",
  "content": "内容或选中文本",
  "source_url": "https://example.com",
  "url": "https://example.com",
  "tags": ["tag1", "tag2"],
  "annotation_type": "capture",
  "create_as_post": true
}
```

**响应示例：**
```json
{
  "success": true,
  "post_id": 123,
  "type": "post",
  "message": "文章创建成功"
}
```

#### 同步标注

```http
POST /knowledge_base/api/plugin/sync-annotations
```

**认证**: API Key 或 Session

**请求参数：**
```json
{
  "url": "https://example.com",
  "annotations": [
    {
      "url": "https://example.com",
      "selection": "选中的文本",
      "text": "高亮文本",
      "xpath": "/html/body/p[1]",
      "color": "yellow",
      "note": "笔记",
      "annotation_type": "highlight"
    }
  ]
}
```

**颜色选项:** yellow, blue, green, pink, orange, purple
**类型选项:** highlight, note, bookmark

#### 获取页面标注

```http
GET /knowledge_base/api/plugin/annotations?url={url}
```

**认证**: API Key 或 Session

**响应示例：**
```json
{
  "success": true,
  "annotations": [
    {
      "id": 1,
      "annotation_text": "选中的文本",
      "xpath": "/html/body/p[1]",
      "color": "yellow",
      "note": "笔记",
      "annotation_type": "highlight",
      "created_at": "2026-03-19T10:00:00"
    }
  ],
  "count": 1
}
```

#### 获取最近捕获

```http
GET /knowledge_base/api/plugin/recent?limit={10}
```

**认证**: API Key 或 Session

**响应示例：**
```json
{
  "success": true,
  "cards": [
    {
      "id": 1,
      "title": "标题",
      "content": "内容",
      "tags": ["tag1"],
      "status": "idea",
      "source": "plugin",
      "created_at": "2026-03-19T10:00:00"
    }
  ],
  "count": 10
}
```

#### 已弃用的页面路由

以下旧版页面路由现已重定向或废弃，建议使用新的 `/knowledge/*` 空间：

- `GET /knowledge_base/timeline` → 重定向到 `/knowledge/`
- `GET /knowledge_base/incubator` → 重定向到 `/knowledge/`
- `GET/POST /knowledge_base/quick-note` → GET 重定向到 `/knowledge/`，POST 仍可创建笔记（但不推荐）

### 卡片管理 API

#### 获取卡片列表

```http
GET /knowledge_base/api/cards?status={idea}&limit={20}
```

**需要认证**: 是

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | 筛选状态：idea/incubating/draft |
| limit | int | 返回数量 |

#### 获取卡片详情

```http
GET /knowledge_base/api/cards/{card_id}
```

#### 更新卡片

```http
PUT /knowledge_base/api/cards/{card_id}
```

**请求参数：**
```json
{
  "title": "新标题",
  "content": "新内容",
  "status": "incubating"
}
```

#### 删除卡片

```http
DELETE /knowledge_base/api/cards/{card_id}
```

#### 卡片状态转换

```http
PUT /knowledge_base/api/cards/{card_id}/status
```

**请求参数：**
```json
{
  "status": "incubating"
}
```

#### 合并卡片

```http
POST /knowledge_base/api/cards/merge
```

**请求参数：**
```json
{
  "card_ids": [1, 2, 3],
  "action": "create_post",
  "post_id": null
}
```

#### AI生成卡片标签

```http
POST /knowledge_base/api/cards/generate-tags
```

**请求参数：**
```json
{
  "card_id": 123
}
```

#### AI合并卡片

```http
POST /knowledge_base/api/cards/ai-merge
```

**请求参数：**
```json
{
  "card_ids": [1, 2, 3],
  "merge_style": "comprehensive"
}
```

#### 转换为文章

```http
POST /knowledge_base/api/card/{card_id}/convert-to-post
```

---

## 📖 知识空间 API

> 新版独立知识空间，URL 前缀为 `/knowledge`。需要登录（Session Cookie）。

### 目录树与页面

#### 知识库首页
```http
GET /knowledge/
```

#### 分类详情
```http
GET /knowledge/category/{category_id}
```

#### 文档详情
```http
GET /knowledge/doc/{doc_id}
```

#### 知识库内搜索
```http
GET /knowledge/search?q={keyword}
```

### 文档管理

#### 新建文档
```http
GET/POST /knowledge/doc/new
```

**POST 请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| title | string | 是 | 文档标题 |
| content | string | 是 | Markdown 内容 |
| category_id | int | 是 | 所属目录 |
| tags | string | 否 | 逗号分隔标签 |
| sort_order | int | 否 | 排序值 |
| is_published | bool | 否 | 是否发布 |

#### 编辑文档
```http
GET/POST /knowledge/doc/{doc_id}/edit
```

#### 删除文档
```http
POST /knowledge/doc/{doc_id}/delete
```

### 目录管理

#### 新建目录
```http
POST /knowledge/category/new
```

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| name | string | 是 | 目录名称 |
| parent_id | int | 否 | 父目录 ID（空为根目录） |
| icon | string | 否 | 图标 |
| description | string | 否 | 描述 |

#### 删除目录
```http
POST /knowledge/category/{category_id}/delete
```

#### 拖拽排序/移动目录
```http
POST /knowledge/reorder
```

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| type | string | 是 | `category` 或 `doc` |
| id | int | 是 | 被移动项 ID |
| parent_id | int/空 | 否 | 新父级 ID（空为根目录） |
| sort_order | int | 是 | 新排序值 |

### 编辑器辅助接口

#### 编辑器内图片上传
```http
POST /knowledge/doc/upload-image
Content-Type: multipart/form-data
```

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| file | file | 是 | 图片文件 |

**响应示例：**
```json
{
  "success": true,
  "url": "/static/uploads/images/20260629_abc123.png",
  "filename": "20260629_abc123.png"
}
```

#### 自动保存草稿
```http
POST /knowledge/doc/{doc_id}/autosave
```

**请求参数：**
```json
{
  "title": "文档标题",
  "content": "Markdown 内容"
}
```

#### 获取最新草稿
```http
GET /knowledge/doc/{doc_id}/draft
```

**响应示例：**
```json
{
  "success": true,
  "draft": {
    "title": "草稿标题",
    "content": "草稿内容",
    "updated_at": "2026-06-29T10:00:00"
  }
}
```

### 归档旧卡片
```http
POST /knowledge/card/{card_id}/archive
```

将旧版知识卡片归档到知识空间。

---

## 🤖 AI功能API

### 生成标签

```http
POST /admin/ai/generate-tags
```

**需要认证**: 是

**请求参数：**
```json
{
  "title": "文章标题",
  "content": "文章内容",
  "post_id": 123
}
```

**响应示例：**
```json
{
  "success": true,
  "tags": ["Python", "Flask", "Web开发"],
  "tokens_used": 250,
  "model": "gpt-3.5-turbo",
  "cost": 0.0001
}
```

### 生成标题

```http
POST /admin/ai/generate-title
```

**需要认证**: 是

**请求参数：**
```json
{
  "content": "文章内容"
}
```

**响应示例：**
```json
{
  "success": true,
  "title": "生成的标题",
  "tokens_used": 120
}
```

### 生成摘要

```http
POST /admin/ai/generate-summary
```

**需要认证**: Is

**请求参数：**
```json
{
  "title": "文章标题",
  "content": "文章内容",
  "max_length": 200
}
```

### 推荐相关文章

```http
POST /admin/ai/recommend-posts
```

**需要认证**: 是

**请求参数：**
```json
{
  "post_id": 123,
  "title": "文章标题",
  "content": "文章内容",
  "max_recommendations": 3
}
```

**响应示例：**
```json
{
  "success": true,
  "recommendations": [
    {"post_id": 100, "title": "相关文章1", "relevance": 0.85},
    {"post_id": 101, "title": "相关文章2", "relevance": 0.78}
  ],
  "tokens_used": 300
}
```

### 续写文章

```http
POST /admin/ai/continue-writing
```

**需要认证**: 是

**请求参数：**
```json
{
  "title": "文章标题",
  "content": "现有内容",
  "continuation_length": 500
}
```

### 内容整理建议

```http
POST /admin/ai/organize-content
```

**需要认证**: 是

**请求参数：**
```json
{
  "title": "当前标题",
  "content": "内容",
  "categories": [{"id": 1, "name": "技术"}]
}
```

**响应示例：**
```json
{
  "success": true,
  "suggestion": {
    "title": "更好的标题",
    "summary": "内容摘要...",
    "tags": ["标签1", "标签2"],
    "content_type": "knowledge",
    "category": {"id": 1, "name": "技术"},
    "source": "ai",
    "tokens_used": 150
  }
}
```

### AI 配置

```http
GET /admin/ai/configure
```

**需要认证**: 是

获取当前 AI 配置和设置页面。

```http
POST /admin/ai/configure
```

**请求参数：**
```json
{
  "ai_tag_generation_enabled": true,
  "ai_provider": "openai",
  "ai_api_key": "sk-...",
  "ai_model": "gpt-3.5-turbo"
}
```

### 测试 AI 配置

```http
POST /admin/ai/test
```

**需要认证**: 是

**请求参数：**
```json
{
  "ai_provider": "openai",
  "ai_api_key": "sk-...",
  "ai_model": "gpt-3.5-turbo"
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "配置测试成功"
}
```

### AI 功能状态

```http
GET /admin/ai/status
```

**需要认证**: 是

**响应示例：**
```json
{
  "ai_enabled": true
}
```

### AI 使用历史

```http
GET /admin/ai/history
```

**需要认证**: 是

---

## 📤 文件上传API

### 上传图片

```http
POST /admin/upload
Content-Type: multipart/form-data
```

**需要认证**: 是

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| file | file | 是 | 图片文件 |

**响应示例：**
```json
{
  "success": true,
  "url": "/static/uploads/images/20260316_abc123.jpg",
  "filename": "20260316_abc123.jpg",
  "original_url": "/static/uploads/images/20260316_abc123.jpg",
  "optimization_id": 1
}
```

**支持格式：** JPG, PNG, GIF, BMP, WebP, TIFF, HEIC, HEIF, MPO

### 查询图片优化状态

```http
GET /admin/image-status/{optimization_id}
```

**需要认证**: 是

**响应示例：**
```json
{
  "success": true,
  "status": "completed",
  "sizes": {
    "thumbnail": "/static/uploads/optimized/xxx_thumbnail.webp",
    "medium": "/static/uploads/optimized/xxx_medium.webp",
    "large": "/static/uploads/optimized/xxx_large.webp"
  },
  "compression_ratio": 85.5
}
```

### 移动端上传图片

```http
POST /mobile/upload
Content-Type: multipart/form-data
```

**需要认证**: 是（Session 或 `X-API-Key` 请求头）

> 注意：此端点已豁免 CSRF 保护，使用 API Key 认证时不受 CSRF 影响

---

## 📝 草稿API

### 获取草稿列表

```http
GET /api/drafts?post_id={123}
```

**需要认证**: 是

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| post_id | int | 可选，筛选特定文章的草稿 |

**响应示例：**
```json
{
  "success": true,
  "drafts": [
    {
      "id": 1,
      "post_id": 123,
      "title": "草稿标题",
      "content": "草稿内容",
      "category_id": 1,
      "tags": ["tag1"],
      "updated_at": "2026-03-19T10:30:00"
    }
  ]
}
```

### 创建草稿

```http
POST /api/drafts
```

**需要认证**: 是

**请求参数：**
```json
{
  "post_id": 123,
  "title": "草稿标题",
  "content": "草稿内容",
  "category_id": 1,
  "tags": ["tag1"],
  "device_info": "iPhone 13"
}
```

### 获取单个草稿

```http
GET /api/drafts/{draft_id}
```

**需要认证**: 是

### 更新草稿

```http
PUT /api/drafts/{draft_id}
```

**需要认证**: 是

**请求参数：**
```json
{
  "title": "更新的标题",
  "content": "更新的内容",
  "category_id": 1,
  "tags": ["tag1"],
  "client_version": "2026-03-19T10:30:00",
  "server_version": "2026-03-19T10:25:00"
}
```

**冲突响应（409）：**
```json
{
  "success": false,
  "error": "检测到版本冲突",
  "status": "conflict",
  "draft": {...}
}
```

### 解决草稿冲突

```http
POST /api/drafts/resolve
```

**需要认证**: 是

**请求参数：**
```json
{
  "draft_id": 1,
  "resolution": "use_client",
  "client_content": "客户端的版本",
  "conflict_draft_id": 2,
  "current_draft_id": 1,
  "action": "merge",
  "merged_data": {...}
}
```

**resolution 选项：**
- `use_client`: 使用客户端版本
- `use_server`: 使用服务器版本
- `merge`: 合并版本

### 删除草稿

```http
DELETE /api/drafts/{draft_id}
```

**需要认证**: 是

---

## 🛠️ 工具API

### 生成分享二维码

```http
GET /api/share/qrcode?url={url}
```

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| url | string | 要生成二维码的URL（默认为首页） |

**响应示例：**
```json
{
  "qrcode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

### 获取原图 URL

```http
GET /api/image/original-url?hash={abc123}
```

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| hash | string | 优化图片文件名中的哈希值 |

**响应示例：**
```json
{
  "success": true,
  "original_url": "/static/uploads/images/xxx.jpg",
  "exists": true,
  "filename": "xxx.jpg"
}
```

---

## ⚠️ 错误响应

所有API在错误情况下返回统一格式：

```json
{
  "success": false,
  "error": "错误消息描述"
}
```

### 常见错误码

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如草稿冲突） |
| 413 | 请求体过大 |
| 429 | 请求过于频繁（速率限制） |
| 500 | 服务器内部错误 |

---

## 🔒 权限说明

### 用户角色

| 角色 | 权限 |
|------|------|
| **admin** | 所有权限，包括用户管理 |
| **editor** | 创建、编辑文章，管理评论 |
| **author** | 只能管理自己的文章 |

### 访问控制

文章访问级别：
- `public`: 公开可见
- `login`: 登录用户可见
- `password`: 需要密码访问
- `private`: 仅作者可见

---

## 📊 速率限制

| 端点类型 | 限制 |
|----------|------|
| 登录 | 5次/分钟 |
| AI功能 | 10次/分钟（可配置） |
| 其他API | 1000次/天, 200次/小时 |

---

## 🔐 CSRF 豁免端点

以下端点已豁免 CSRF 保护（用于浏览器扩展和移动端）：

- `/knowledge_base/api/plugin/submit` - 浏览器扩展提交
- `/knowledge_base/api/plugin/sync-annotations` - 浏览器扩展标注同步
- `/knowledge_base/api/plugin/annotations` - 浏览器扩展获取批注
- `/knowledge_base/api/plugin/recent` - 浏览器扩展最近捕获
- `/mobile/upload` - 移动端图片上传
- `/admin/ai/test` - AI 配置测试

---

## 📚 相关文档

- [系统架构文档](./ARCHITECTURE.md)
- [部署指南](../DEPLOYMENT.md)
- [快速启动](../QUICKSTART.md)
- [文档索引](./README.md)

---

**更新日志：**
- v2.2 (2026-03-19): 更新所有 API 端点，补充 Passkey、知识库、AI 功能、移动端等遗漏端点
- v2.2 (2026-03-16): 初始版本
