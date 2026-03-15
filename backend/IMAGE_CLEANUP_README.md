# 图片清理工具使用说明

## 📖 工具介绍

这个工具集包含4个脚本，用于清理文章中的失效图片链接。

## 🚀 在远程服务器上使用

### 1. 同步代码到服务器

```bash
# 在本地执行
cd /Users/gn/simple-blog
git pull origin main

# 或者使用rsync/scp上传
rsync -avz backend/*_images.py user@your-server:/path/to/backend/
```

### 2. 选择合适的脚本运行

#### 方案1：快速清理（推荐）

**适用场景**：清理大量已知失效的图片链接（126.net、blog.163.com等）

```bash
cd backend
python3 fast_clean_invalid_images.py
```

**优点**：
- ⚡ 执行速度快（几秒钟完成）
- 🎯 直接删除失效的网易博客图片
- 📊 清理报告详细

#### 方案2：只清理本地图片

**适用场景**：只清理本地文件系统中不存在的图片

```bash
cd backend
python3 clean_invalid_images_simple.py
```

**优点**：
- 🚀 不需要外部依赖
- 💨 快速扫描本地文件
- ✅ 不会影响外部链接

#### 方案3：检查并清理外部图片

**适用场景**：需要检查外部链接是否有效

```bash
cd backend
python3 check_external_images.py
```

**注意**：
- ⏰ 需要较长时间（10-30分钟）
- 🌐 需要网络连接检查外部URL
- 💡 先试运行，确认后再清理

#### 方案4：完整清理（需要额外依赖）

**适用场景**：完整功能，检查所有类型图片

```bash
# 先安装依赖
pip3 install requests

# 运行完整版
python3 clean_invalid_images.py
```

## 📊 清理效果示例

```
📊 清理完成报告
============================================================
扫描文章数: 241
清理文章数: 38
删除图片总数: 643
============================================================
```

## 💾 数据库备份

每次运行前都会提示备份位置：

```bash
# 备份数据库
cp /path/to/db/simple_blog.db /path/to/db/simple_blog.db.backup.$(date +%Y%m%d_%H%M%S)

# 恢复数据库（如果需要）
cp /path/to/db/simple_blog.db.backup.20260315_124428 /path/to/db/simple_blog.db
```

## 🔄 定期维护建议

1. **每月运行一次**快速清理：
   ```bash
   python3 fast_clean_invalid_images.py
   ```

2. **新文章发布后**检查本地图片：
   ```bash
   python3 clean_invalid_images_simple.py
   ```

3. **发现大量破损图片**时检查外部链接：
   ```bash
   python3 check_external_images.py
   ```

## ⚠️ 注意事项

1. **备份数据**：运行清理前务必备份数据库
2. **试运行**：所有脚本都支持试运行模式，先查看效果再确认
3. **网络要求**：检查外部图片时需要稳定的网络连接
4. **执行时间**：完整检查可能需要10-30分钟，请耐心等待

## 🎯 最佳实践

```bash
# 推荐的工作流程
cd backend

# 1. 备份数据库
cp ../db/simple_blog.db ../db/simple_blog.db.backup.$(date +%Y%m%d_%H%M%S)

# 2. 快速清理失效图片
python3 fast_clean_invalid_images.py

# 3. 验证结果（刷新网页查看）

# 4. 如果有问题，从备份恢复
# cp ../db/simple_blog.db.backup.XXX ../db/simple_blog.db
```

## 📧 需要帮助？

如果遇到问题，检查：
1. Python版本：需要Python 3.6+
2. 文件权限：脚本需要有执行权限（chmod +x）
3. 数据库路径：确保数据库文件路径正确
4. 磁盘空间：确保有足够的磁盘空间
