"""
Models 模块（re-export 兼容壳）

原 3006 行的单体 models.py 已按领域拆分为：
- db.py         数据库连接/上下文/分页/建表初始化/FTS 索引
- posts.py      文章 CRUD/搜索/访问控制
- categories.py 博客分类
- knowledge.py  知识库分类树/文档/沉淀
- tags.py       标签
- comments.py   评论与图片优化记录
- users.py      用户/Passkey/AI 配置与历史/API Key
- cards.py      卡片与标注（annotations）
- utils.py      HTML 清理与文本截断

本文件只做 re-export，保持 `from backend.models.models import X`
与 `from models import X` 两种历史导入路径行为不变。
"""

from .db import *
from .utils import *
from .tags import *
from .categories import *
from .users import *
from .cards import *
from .posts import *
from .comments import *
from .knowledge import *
