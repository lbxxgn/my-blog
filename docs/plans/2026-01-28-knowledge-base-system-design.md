# 个人知识库系统设计方案

## 设计日期
2026-01-28

## 需求概述

基于现有博客系统，打造一个兼具**第二大脑**和**想法孵化器**功能的个人知识库系统：
- 长期存储和组织学习笔记、想法，方便回顾和连接知识点
- 快速记录碎片化想法，逐步打磨成成熟文章

---

## 第一部分：整体架构与核心组件

### 系统架构

采用**双层内容模型**：

**卡片层（轻量级）**
- 快速碎片化记录
- 字段：id、标题、内容、标签、状态（idea/draft/incubating/published）、创建时间、关联文章ID
- 支持语音转文字输入
- 浏览器插件快速捕获

**文章层（重量级）**
- 现有的文章系统增强
- 新增字段：原始卡片IDs（记录从哪些卡片合并而来）、文章类型（blog/knowledge-article）
- 保留现有富文本编辑、AI辅助功能

**核心新增页面**
1. **快速记事页面** (`/quick-note`) - 极简界面，标题+内容框+语音按钮
2. **时间线页面** (`/timeline`) - 倒序展示所有卡片和文章，支持筛选
3. **孵化箱页面** (`/incubator`) - 展示标记为"待完善"的内容
4. **浏览器插件API** (`/api/plugin/submit`) - 接收插件发送的内容

---

## 第二部分：数据模型与数据库设计

### 数据库表结构

**新增表：`cards`**
```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    tags TEXT,
    status TEXT DEFAULT 'idea',
    source TEXT DEFAULT 'web',
    linked_article_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (linked_article_id) REFERENCES posts(id)
);

CREATE INDEX idx_cards_user_status ON cards(user_id, status);
CREATE INDEX idx_cards_created ON cards(created_at DESC);
```

**扩展表：`posts`**
```sql
ALTER TABLE posts ADD COLUMN post_type TEXT DEFAULT 'blog';
ALTER TABLE posts ADD COLUMN source_card_ids TEXT;
```

**状态流转**
- `idea` → `incubating` → `draft` → `published`
- `idea` 可直接合并成文章（状态变为`published`，link到post）

---

## 第三部分：核心功能实现

### 1. 快速记事页面 (`/quick-note`)

**UI设计**
- 极简布局：顶部标题输入框 + 下方大文本框
- 右下角悬浮按钮组：
  - 📤 快速保存（Ctrl+S）
  - 🎤 语音输入（调用Web Speech API）
  - 🏷️ AI生成标签
- 保存后自动清空，显示Toast"已保存到时间线"

**后端路由**
```python
@app.route('/quick-note', methods=['GET', 'POST'])
@login_required
def quick_note():
    if request.method == 'POST':
        title = request.form.get('title', '')
        content = request.form.get('content')
        card = create_card(user_id=current_user.id, title=title,
                          content=content, status='idea', source='web')
        return jsonify({'success': True, 'card_id': card.id})
```

### 2. 时间线页面 (`/timeline`)

**展示逻辑**
- 合并查询`cards`和`posts`，按`created_at`倒序
- 卡片显示：标题、内容摘要、标签、状态图标
- 筛选器：全部/想法/孵化中/已发布 + 标签筛选
- 操作：编辑、删除、"开始孵化"（移至incubator状态）、"合并到文章"

**批量操作**
- 勾选多个卡片 → "合并成文章"按钮激活
- 点击后跳转到编辑器，预填充内容（按时间排序）

---

## 第四部分：扩展功能与智能辅助

### 3. 浏览器插件与移动端

**浏览器插件**
- Chrome Extension：选中网页文本 → 右键"保存到知识库"
- 插件调用API：`POST /api/plugin/submit`
  ```json
  {
    "title": "网页标题",
    "content": "选中文本 + URL",
    "source": "plugin",
    "tags": ["待阅读"]
  }
  ```
- 后端验证API Key（用户设置中生成）

**移动端优化**
- `/quick-note` 响应式设计
- PWA支持：添加到主屏幕，离线缓存（IndexedDB）
- 语音输入优先：移动端显示大麦克风按钮

### 4. 孵化箱页面 (`/incubator`)

**目的** - 专门处理"待完善"的内容

**功能**
- 左侧：卡片列表（status=`incubating`）
- 右侧：选中卡片的详情 + 编辑区
- AI辅助按钮：
  - 🤖 **生成大纲** - 分析卡片内容，生成文章结构
  - 🔗 **查找关联** - 搜索相关卡片和文章
  - 📝 **续写内容** - 基于卡片扩展成段落
- 底部："合并到文章"或"创建新文章"

### 5. AI语音转文字

**前端实现**
```javascript
const recognition = new webkitSpeechRecognition();
recognition.lang = 'zh-CN';
recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    contentEditor.value += transcript;
};
```

**后端增强**
- 保存后自动调用：`AI.generate_tags(content)` 提取关键词
- 如果内容超过200字，自动生成摘要

---

## 第五部分：卡片合并成文章机制

### 合并流程设计

**方式一：手动合并**
1. 时间线页面勾选多个卡片
2. 点击"合并成文章"按钮
3. 弹窗选择：
   - 创建新文章（跳转到编辑器，内容按时间倒序拼接）
   - 添加到现有文章（选择文章ID，追加到末尾）
4. 保存文章时，记录`source_card_ids`，卡片状态更新为`published`

**方式二：AI辅助整理**
1. 选择卡片后，点击"AI智能合并"
2. 后端调用AI处理：
   ```python
   def ai_merge_cards(card_ids):
       cards = get_cards(card_ids)
       prompt = f"将以下内容整理成连贯的文章，去重、提取核心观点..."
       result = ai_client.generate(prompt)
       return {
           'title': ai_title,
           'content': ai_content,
           'tags': ai_tags,
           'outline': ai_outline
       }
   ```
3. 跳转到编辑器，预填充AI整理的内容
4. 用户可以继续修改后发布

**方式三：渐进式成熟**
1. 单张卡片可以"标记为孵化中"（status → `incubating`）
2. 在孵化箱页面逐步完善：
   - 添加更多卡片到同一文章
   - AI生成大纲后人工填充细节
   - 随时保存为草稿
3. 成熟后"发布为文章"

### 数据流转示例

```
Card 1 (idea) + Card 2 (idea) → 手动合并 → Draft Post (source_card_ids: [1,2])
Card 3 (idea) → AI整理 → Published Post (source_card_ids: [3])
Card 4 (idea) → incubating → 在孵化箱添加Card 5 → 合并成文章
```

---

## 第六部分：安全性、性能与测试

### 安全性考虑

**浏览器插件安全**
- API Key机制：每个用户在设置中生成独立密钥
- 速率限制：插件每分钟最多提交10条
- Content Security Policy：防止XSS

**语音输入**
- 前端处理，不上传音频文件
- 用户手动确认后才保存

**权限控制**
- 卡片和文章继承现有权限系统（公开/登录/密码/私密）
- 用户只能看到自己的卡片（多用户系统下）

### 性能优化

**数据库查询**
- 时间线查询使用游标分页（现有优化）
- 索引：`user_id + status + created_at`

**缓存策略**
- 孵化箱页面缓存用户卡片列表（Redis，5分钟）
- AI生成结果缓存（相同内容24小时内直接返回）

### 测试计划

**单元测试**
- `test_card_creation()` - 卡片创建逻辑
- `test_card_merge()` - 合并功能
- `test_status_transition()` - 状态流转

**集成测试**
- `test_quick_note_workflow()` - 快速记事完整流程
- `test_ai_merge_cards()` - AI合并功能

**E2E测试**
- 使用Playwright测试：快速记事 → 语音输入 → 保存 → 时间线查看

---

## 实施优先级

### 第一阶段（核心功能）
- 数据库表创建
- 快速记事页面
- 时间线页面（基础展示）
- 手动合并功能

### 第二阶段（智能辅助）
- 孵化箱页面
- AI辅助合并
- AI语音标签生成

### 第三阶段（扩展功能）
- 浏览器插件
- 移动端PWA
- 语音输入优化

---

## 技术栈

- **后端**: Flask (现有)
- **数据库**: SQLite (现有)
- **前端**: 纯 CSS/JS (现有)
- **AI**: 复用现有AI配置（OpenAI/火山引擎/阿里百炼）
- **语音**: Web Speech API
- **插件**: Chrome Extension API
- **PWA**: Service Worker + IndexedDB
