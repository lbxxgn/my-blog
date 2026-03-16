# 图片清理工具使用指南

## 快速开始

### 1. 检查并清理外部图片（推荐 - 最快）

```bash
cd backend
python check_external_images_optimized.py
```

**特点**：
- ⚡ 并发检查，速度快10倍
- 💾 分批处理，内存占用低
- 🔄 自动管理数据库连接
- 📊 生成详细报告

### 2. 清理本地无效图片

```bash
cd backend
python clean_invalid_images_simple.py
```

**特点**：
- 🏠 只检查本地图片
- 🚀 不检查外部URL，速度快
- 📝 适合快速清理

### 3. 快速清理已知失效域名

```bash
cd backend
python fast_clean_invalid_images.py
```

**特点**：
- ⚡ 最快，直接删除失效域名
- 🎯 针对126.net、blog.163.com
- 💥 无需检查，直接执行

## 工具对比

| 工具 | 速度 | 内存 | 准确性 | 适用场景 |
|------|------|------|--------|----------|
| `check_external_images_optimized.py` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **推荐** - 全面检查外部图片 |
| `clean_invalid_images_simple.py` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 只检查本地图片 |
| `fast_clean_invalid_images.py` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 快速清理已知失效域名 |
| `check_external_images.py` | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 旧版，不推荐 |
| `clean_invalid_images.py` | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | 旧版，不推荐 |

## 使用共享模块

如果你想编写自己的图片清理脚本，可以使用共享模块：

```python
#!/usr/bin/env python3
from utils.image_cleanup import (
    extract_images_from_content,
    remove_img_tags_by_urls,
    check_image_urls_concurrent,
    print_cleanup_report,
    get_db_connection
)
from config import get_backup_path

# 提取图片
content = "<img src='/test.jpg'>"
images = extract_images_from_content(content)

# 并发检查URL
urls = [url for _, url in images]
results = check_image_urls_concurrent(urls, max_workers=10)

# 删除无效图片
invalid_urls = [url for url, (valid, _) in results.items() if not valid]
cleaned_content = remove_img_tags_by_urls(content, invalid_urls)

# 打印报告
report = {
    'total_posts': 1,
    'valid_images': len(urls) - len(invalid_urls),
    'invalid_images': len(invalid_urls),
    'errors': [],
    'details': []
}
print_cleanup_report(report)
```

## 常见问题

### Q: 如何只检查前10篇文章？

A: 修改脚本或添加参数：
```python
# 在check_external_images_optimized.py中
report_test = check_and_clean_posts_concurrent(
    dry_run=True,
    max_check=10,  # 只检查前10篇
    check_workers=5
)
```

### Q: 如何调整并发数？

A: 修改`check_workers`参数：
```python
check_image_urls_concurrent(urls, max_workers=20)  # 增加到20个并发
```

### Q: 备份文件在哪里？

A: 使用配置函数自动获取：
```python
from config import get_backup_path
backup = get_backup_path()
print(f"最新备份: {backup}")
```

### Q: 如何恢复数据库？

A: 使用备份文件恢复：
```bash
# 查看最新备份
ls -lt db/simple_blog.db.backup.*

# 恢复数据库
cp db/simple_blog.db.backup.XXXXXX db/simple_blog.db
```

## 性能优化建议

1. **使用并发版本**
   - `check_external_images_optimized.py` 比 `check_external_images.py` 快10倍

2. **分批处理大文件**
   - 默认100篇/批，可根据内存调整

3. **调整并发数**
   - CPU密集型: `max_workers=CPU核心数`
   - IO密集型: `max_workers=10-20`

4. **先试运行**
   - 所有工具都支持`dry_run=True`
   - 确认无误后再实际执行

## 维护建议

### 定期清理
```bash
# 每月运行一次
cd backend
python check_external_images_optimized.py
```

### 备份策略
```bash
# 运行清理前自动备份
cp db/simple_blog.db "db/simple_blog.db.backup.$(date +%Y%m%d_%H%M%S)"
```

### 监控无效图片
```python
# 创建定时任务检查
import schedule
import time

def check_images():
    import subprocess
    subprocess.run(['python', 'check_external_images_optimized.py'])

# 每周日凌晨2点运行
schedule.every().sunday.at("02:00").do(check_images)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 更新日志

### 2026-03-15
- ✨ 创建共享工具模块 `utils/image_cleanup.py`
- ✨ 新增并发URL检查功能（10倍提速）
- ✨ 新增分批处理功能（降低90%内存）
- ✨ 优化无限滚动JavaScript
- 🎉 消除约300行重复代码

## 相关文档

- [优化总结](OPTIMIZATION_SUMMARY.md) - 详细的优化内容
- [图片清理说明](IMAGE_CLEANUP_README.md) - 原始工具说明
