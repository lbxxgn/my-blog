# Simple Blog API 文档

**版本**: v2.2
**最后更新**: 2026-03-16
**基础URL**: `http://your-domain.com`

---

## 📋 目录

- [认证](#认证)
- [文章API](#文章api)
- [分类与标签API](#分类与标签api)
- [评论API](#评论api)
- [搜索API](#搜索api)
- [用户管理API](#用户管理api)
- [知识库API](#知识库api)
- [AI功能API](#ai功能api)
- [文件上传API](#文件上传api)
- [草稿API](#草稿api)

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

**响应示例：**
```json
{
  "success": true,
  "redirect": "/"
}
```

### 登出

```http
POST /logout
```

**响应示例：**
```json
{
  "success": true,
  "redirect": "/login"
}
```

### 修改密码

```http
POST /change-password
```

**请求参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| old_password | string | 是 | 旧密码 |
| new_password | string | 是 | 新密码（至少12位） |

**响应示例：**
```json
{
  "success": true,
  "message": "密码修改成功"
}
```

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
      "excerpt": "摘要内容",
      "author": "作者名",
      "created_at": "2026-03-16T10:30:00",
      "updated_at": "2026-03-16T10:30:00",
      "category": "技术",
      "tags": ["Python", "Flask"],
      "image_url": "/static/uploads/images/...",
      "access": "public"
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

**响应示例：**
```json
{
  "id": 123,
  "title": "文章标题",
  "content": "<p>文章HTML内容</p>",
  "author": "作者名",
  "created_at": "2026-03-16T10:30:00",
  "category": "技术",
  "tags": ["Python", "Flask"],
  "access": "public",
  "allow_comments": true
}
```

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
  "message": "密码验证成功"
}
```

### 添加文章

```http
POST /new
```

**请求参数：**
```json
{
  "title": "文章标题",
  "content": "文章HTML内容",
  "category_id": 1,
  "tags": [1, 2, 3],
  "access": "public",
  "allow_comments": true,
  "password": null
}
```

**字段说明：**
| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| title | string | 是 | 文章标题 |
| content | string | 是 | 文章内容（HTML） |
| category_id | int | 否 | 分类ID |
| tags | array | 否 | 标签ID数组 |
| access | string | 否 | 访问控制：public/login/password |
| allow_comments | boolean | 否 | 是否允许评论 |
| password | string | 否 | 访问密码（access=password时必需） |

**响应示例：**
```json
{
  "success": true,
  "message": "文章发布成功",
  "post_id": 124
}
```

### 编辑文章

```http
POST /edit/{post_id}
```

**请求参数：** 同添加文章

**响应示例：** 同添加文章

### 删除文章

```http
POST /delete/{post_id}
```

**响应示例：**
```json
{
  "success": true,
  "message": "文章已删除"
}
```

### 批量操作

#### 批量更新分类

```http
POST /batch-update-category
```

**请求参数：**
```json
{
  "post_ids": [1, 2, 3],
  "category_id": 5
}
```

#### 批量删除

```http
POST /batch-delete
```

**请求参数：**
```json
{
  "post_ids": [1, 2, 3]
}
```

#### 批量发布

```http
POST /batch-publish
```

**请求参数：**
```json
{
  "post_ids": [1, 2, 3],
  "action": "publish"
}
```

#### 批量添加标签

```http
POST /batch-add-tags
```

**请求参数：**
```json
{
  "post_ids": [1, 2, 3],
  "tag_ids": [1, 2]
}
```

---

## 🏷️ 分类与标签API

### 获取所有分类

```http
GET /categories
```

**响应示例：**
```json
{
  "categories": [
    {
      "id": 1,
      "name": "技术",
      "slug": "tech",
      "post_count": 15
    }
  ]
}
```

### 创建分类

```http
POST /categories/new
```

**请求参数：**
```json
{
  "name": "分类名称",
  "slug": "url-slug"
}
```

### 删除分类

```http
POST /categories/{category_id}/delete
```

### 获取所有标签

```http
GET /tags
```

**响应示例：**
```json
{
  "tags": [
    {
      "id": 1,
      "name": "Python",
      "post_count": 8
    }
  ]
}
```

### 创建标签

```http
POST /tags/new
```

**请求参数：**
```json
{
  "name": "标签名称"
}
```

### 删除标签

```http
POST /tags/{tag_id}/delete
```

---

## 💬 评论API

### 添加评论

```http
POST /post/{post_id}/comment
```

**请求参数：**
```json
{
  "content": "评论内容",
  "parent_id": null
}
```

**响应示例：**
```json
{
  "success": true,
  "message": "评论已添加",
  "comment_id": 456
}
```

### 切换评论状态

```http
POST /comments/{comment_id}/toggle
```

### 删除评论

```http
POST /comments/{comment_id}/delete
```

---

## 🔍 搜索API

### 全文搜索

```http
GET /search?q={keyword}&page={1}
```

**查询参数：**
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| q | string | 是 | - | 搜索关键词 |
| page | int | 否 | 1 | 页码 |

**响应示例：**
```json
{
  "query": "Python",
  "results": [
    {
      "id": 123,
      "title": "文章标题",
      "excerpt": "匹配的摘要...",
      "relevance": 0.95
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 10
}
```

---

## 👥 用户管理API

### 创建用户

```http
POST /users/new
```

**请求参数：**
```json
{
  "username": "newuser",
  "email": "user@example.com",
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
POST /users/{user_id}/edit
```

**请求参数：** 同创建用户

### 删除用户

```http
POST /users/{user_id}/delete
```

---

## 📚 知识库API

> 注意：知识库API端点已豁免CSRF保护（浏览器扩展需求）

### 提交卡片

```http
POST /api/plugin/submit
```

**请求参数：**
```json
{
  "content": "卡片内容",
  "url": "https://example.com",
  "title": "页面标题"
}
```

**响应示例：**
```json
{
  "success": true,
  "card_id": 789
}
```

### 同步标注

```http
POST /api/plugin/sync-annotations
```

**请求参数：**
```json
{
  "annotations": [
    {
      "url": "https://example.com",
      "selection": "选中的文本",
      "note": "笔记"
    }
  ]
}
```

### 获取最近标注

```http
GET /api/plugin/annotations
```

### 快速记事

```http
GET /quick-note
POST /quick-note
```

### 获取卡片列表

```http
GET /api/cards
```

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | 筛选状态：idea/incubating/draft |
| limit | int | 返回数量 |

### 更新卡片

```http
PUT /api/cards/{card_id}
```

**请求参数：**
```json
{
  "content": "更新后的内容",
  "status": "draft"
}
```

### 删除卡片

```http
DELETE /api/cards/{card_id}
```

### 卡片状态转换

```http
PUT /api/cards/{card_id}/status
```

**请求参数：**
```json
{
  "status": "incubating"
}
```

### 合并卡片

```http
POST /api/cards/merge
```

**请求参数：**
```json
{
  "card_ids": [1, 2, 3],
  "merged_content": "合并后的内容",
  "title": "新标题"
}
```

### AI生成标签

```http
POST /api/cards/generate-tags
```

**请求参数：**
```json
{
  "card_id": 123
}
```

### AI合并卡片

```http
POST /api/cards/ai-merge
```

**请求参数：**
```json
{
  "card_ids": [1, 2, 3]
}
```

### 转换为文章

```http
POST /api/card/{card_id}/convert-to-post
```

---

## 🤖 AI功能API

### 生成标签

```http
POST /ai/generate-tags
```

**请求参数：**
```json
{
  "content": "文章内容",
  "count": 5
}
```

**响应示例：**
```json
{
  "success": true,
  "tags": ["Python", "Flask", "Web开发", "后端", "教程"]
}
```

### 生成摘要

```http
POST /ai/generate-summary
```

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
  "summary": "这是一篇关于..."
}
```

### 推荐相关文章

```http
POST /ai/recommend-posts
```

**请求参数：**
```json
{
  "post_id": 123,
  "limit": 5
}
```

### 续写文章

```http
POST /ai/continue-writing
```

**请求参数：**
```json
{
  "content": "现有内容",
  "length": 500
}
```

---

## 📤 文件上传API

### 上传图片

```http
POST /upload
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
  "url": "/static/uploads/images/20260316_abc123.jpg",
  "filename": "20260316_abc123.jpg",
  "original_url": "/static/uploads/images/20260316_abc123.jpg",
  "optimization_id": 1,
  "status": "pending"
}
```

**说明：**
- 上传后会在后台自动生成多个尺寸的优化版本
- 支持：JPG, PNG, GIF, BMP, WebP, TIFF, HEIC, HEIF, MPO
- 自动转换为WebP格式
- 生成尺寸：thumbnail (150×150), medium (600×400), large (1200×800), feed (1920×1280)

---

## 📝 草稿API

### 获取草稿列表

```http
GET /api/drafts
```

**响应示例：**
```json
{
  "drafts": [
    {
      "id": 1,
      "title": "草稿标题",
      "content": "草稿内容",
      "updated_at": "2026-03-16T10:30:00"
    }
  ]
}
```

### 创建草稿

```http
POST /api/drafts
```

**请求参数：**
```json
{
  "title": "草稿标题",
  "content": "草稿内容"
}
```

### 获取单个草稿

```http
GET /api/drafts/{draft_id}
```

### 更新草稿

```http
PUT /api/drafts/{draft_id}?_method=PATCH
```

**请求参数：**
```json
{
  "title": "更新的标题",
  "content": "更新的内容"
}
```

### 删除草稿

```http
DELETE /api/drafts/{draft_id}
```

### 解决草稿冲突

```http
POST /api/drafts/resolve
```

**请求参数：**
```json
{
  "draft_id": 1,
  "resolution": "use_server",
  "client_content": "客户端的版本"
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
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁（速率限制） |
| 500 | 服务器内部错误 |

---

## 🔒 权限说明

### 用户角色

| 角色 | 权限 |
|------|------|
| **admin** | 所有权限 |
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

| 端点 | 限制 |
|------|------|
| 登录 | 5次/分钟 |
| AI功能 | 10次/分钟 |
| 其他API | 60次/分钟 |

---

## 📚 相关文档

- [完整启动指南](QUICKSTART.md)
- [数据库迁移](MIGRATION.md)
- [系统部署](SYSTEMD_DEPLOYMENT.md)
- [README](../README.md)

---

**更新日志：**
- v2.2 (2026-03-16): 初始版本，整理所有公开API端点
