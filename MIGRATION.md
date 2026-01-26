# 数据库迁移指南

## 概述

本指南帮助你将Simple Blog从旧版本升级到最新版本。迁移工具会自动备份现有数据并安全地升级数据库结构。

---

## 迁移到 v4.1.0（2026-01-26）

### 新增功能

#### AI功能
- ✅ AI标签生成（支持多提供商）
- ✅ AI摘要生成
- ✅ AI相关文章推荐
- ✅ AI内容续写
- ✅ AI使用历史记录

#### 访问控制
- ✅ 四种访问权限级别
- ✅ 密码保护功能
- ✅ Session密码存储

### 数据库变更

#### 新增表
```sql
-- AI标签历史记录表
CREATE TABLE ai_tag_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_id INTEGER,
    action TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost REAL DEFAULT 0,
    result_preview TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE SET NULL
);

-- AI用户配置表
CREATE TABLE ai_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    ai_tag_generation_enabled BOOLEAN DEFAULT 0,
    ai_provider TEXT NOT NULL DEFAULT 'openai',
    ai_api_key TEXT,
    ai_model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### posts表新增字段
```sql
-- 访问控制字段
ALTER TABLE posts ADD COLUMN access_level TEXT DEFAULT 'public';
ALTER TABLE posts ADD COLUMN access_password TEXT;
```

#### 新增索引
```sql
CREATE INDEX IF NOT EXISTS idx_ai_history_user ON ai_tag_history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_history_post ON ai_tag_history(post_id);
CREATE INDEX IF NOT EXISTS idx_posts_access_level ON posts(access_level);
```

### 迁移步骤

#### 1. 备份数据库（自动）

```bash
cd /path/to/simple-blog
python3 backend/migrations/migrate_ai_features.py
```

脚本会自动创建备份，格式为：`simple_blog.db.backup_YYYYMMDD_HHMMSS`

#### 2. 验证迁移

迁移完成后，请验证：
- ✅ 访问 `/admin/ai/configure` 可以打开AI设置页面
- ✅ 文章编辑页面显示访问权限下拉框
- ✅ 文章编辑页面显示AI工具栏
- ✅ 访问 `/admin/ai/history` 可以查看AI历史记录

#### 3. 配置AI功能（可选）

1. 登录后台
2. 访问 `/admin/ai/configure`
3. 选择AI提供商（OpenAI/火山引擎/阿里百炼）
4. 输入API密钥
5. 选择模型
6. 点击"测试连接"
7. 保存设置

### 回滚方案

如果迁移出现问题：

```bash
# 1. 停止应用
sudo systemctl stop simple-blog

# 2. 恢复备份
cp db/simple_blog.db.backup_YYYYMMDD_HHMMSS db/simple_blog.db

# 3. 重启应用
sudo systemctl start simple-blog
```

---

## 迁移到 v4.0.0（2026-01-25）

### 新增功能

- ✅ 多用户/多作者系统
- ✅ 三级权限管理（admin/editor/author）
- ✅ 文章作者关联
- ✅ 用户管理界面

### 数据库变更

#### users 表新增字段
- `role` - 用户角色（admin/editor/author）
- `display_name` - 显示名称
- `bio` - 个人简介
- `avatar_url` - 头像URL
- `is_active` - 账户状态
- `created_at` - 创建时间
- `updated_at` - 更新时间

#### posts 表新增字段
- `author_id` - 作者ID（外键关联到users表）

#### 新增索引
- `idx_author_id` - 文章作者索引
- `idx_author_created` - 作者+时间复合索引

### 迁移步骤

#### 1. 备份数据库（自动）

迁移脚本会自动创建数据库备份，格式为：`posts_backup_YYYYMMDD_HHMMSS.db`

#### 2. 运行迁移脚本

```bash
cd /path/to/simple-blog
python3 backend/migrate_db.py
```

#### 3. 确认迁移

脚本会显示：
- 当前数据库状态
- 需要添加的字段
- 迁移进度
- 迁移结果

#### 4. 验证功能

迁移完成后，请验证：
- ✅ 文章可以正常访问
- ✅ 文章显示作者信息
- ✅ 登录功能正常
- ✅ 用户管理功能可用

### 迁移详情

#### users 表迁移

```sql
-- 自动添加的字段
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'author';
ALTER TABLE users ADD COLUMN display_name TEXT;
ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN avatar_url TEXT;
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE users ADD COLUMN created_at TIMESTAMP;
ALTER TABLE users ADD COLUMN updated_at TIMESTAMP;
```

#### posts 表迁移

```sql
-- 添加作者字段
ALTER TABLE posts ADD COLUMN author_id INTEGER;

-- 为现有文章分配作者（使用第一个用户）
UPDATE posts SET author_id = (SELECT id FROM users LIMIT 1)
WHERE author_id IS NULL;
```

#### 索引创建

```sql
CREATE INDEX IF NOT EXISTS idx_author_id ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_author_created ON posts(author_id, created_at DESC);
```

#### 全文搜索重建

```sql
-- 清空旧的全文搜索索引
DELETE FROM posts_fts;

-- 重新填充索引
INSERT INTO posts_fts(rowid, title, content)
SELECT id, title, content FROM posts;
```

---

## 通用故障排查

### 问题：脚本提示"数据库文件不存在"

**原因**：数据库路径不正确

**解决**：
```bash
# 检查数据库是否存在
ls -lh db/simple_blog.db

# 如果不存在，先运行应用初始化数据库
python3 backend/app.py
```

### 问题：迁移后文章没有作者

**原因**：数据库中没有用户

**解决**：
```bash
# 1. 启动应用创建管理员用户
python3 backend/app.py

# 2. 重新运行迁移脚本
python3 backend/migrate_db.py
```

### 问题：某些字段已存在

**原因**：数据库已经部分升级

**解决**：脚本会自动检测已存在的字段，只会添加缺失的字段，可以安全地重新运行。

### 问题：AI功能不工作

**原因**：未配置API密钥或AI功能未启用

**解决**：
1. 访问 `/admin/ai/configure`
2. 启用AI标签生成功能
3. 配置API密钥
4. 测试连接

### 问题：密码保护文章无法访问

**原因**：密码未设置或Session过期

**解决**：
1. 在编辑器中为文章设置访问密码
2. 确保访问级别设置为"密码保护"
3. 重新访问文章并输入密码

## 备份保留策略

- ✅ 迁移成功后建议保留备份至少7天
- ✅ 确认无误后再删除
- ✅ 重要迁移建议保留备份30天

## 注意事项

1. **用户角色**
   - 现有用户默认角色为 `author`（作者）
   - 可以在管理后台修改为 `admin` 或 `editor`

2. **文章作者**
   - 现有文章会自动分配给第一个用户（通常是管理员）
   - 可以在编辑文章时修改作者

3. **数据库锁定**
   - 迁移期间应用会暂时无法访问
   - 建议在低峰时段执行

4. **AI功能**
   - AI功能需要配置API密钥才能使用
   - 不同提供商的API密钥获取方式不同
   - 建议先测试连接再使用

5. **访问控制**
   - 默认所有文章为"公开"权限
   - 密码保护文章需要密码才能访问
   - 私密文章只有作者和管理员可见

## 技术支持

如遇到其他问题，请查看：
- 应用日志：`logs/error.log`
- 迁移日志输出
- GitHub Issues

---

**版本**: 4.1.0
**更新日期**: 2026-01-26
