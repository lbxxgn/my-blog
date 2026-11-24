"""Models Package

数据库模型与函数的统一门面。领域实现位于本包内的独立模块：

- db.py            连接 / 上下文 / 建表初始化 / FTS 索引
- users.py         用户、Passkey、AI 配置与历史、API Key
- posts.py         文章 CRUD / 搜索 / 访问控制
- categories.py    博客分类
- knowledge.py     知识库分类树与文档
- tags.py          标签
- comments.py      评论与图片优化记录
- cards.py         卡片与标注
- revisions.py     文章修订历史
- site_settings.py 站点键值配置
- ai_catalog.py    AI 提供商与模型目录
- utils.py         HTML 清理与文本截断

公开 API 由各领域模块的 ``__all__`` 声明，包层只做聚合，不再维护第二份手写
清单（历史清单曾与实现漂移：漏掉 8 个实际可用的函数）。

两个例外不在这里聚合：
- ``draft.py`` 反过来依赖本包（``from backend.models import get_db_context``），
  聚合会形成循环导入；
- ``embeddings.py`` 会拉起 numpy，不应让每次 ``import backend.models`` 都付出代价。
两者请按模块路径导入，例如 ``from backend.models.draft import save_draft``。
"""

from . import (
    ai_catalog,
    cards,
    categories,
    comments,
    db,
    knowledge,
    posts,
    revisions,
    site_settings,
    tags,
    users,
    utils,
)

# 聚合顺序即文档顺序；同一名称不应出现在两个模块的 __all__ 中
_MODULES = (
    db, utils, tags, categories, users, cards, posts, comments,
    knowledge, revisions, site_settings, ai_catalog,
)

for _module in _MODULES:
    for _name in _module.__all__:
        globals()[_name] = getattr(_module, _name)

# 由各模块 __all__ 派生，保证永不漂移
__all__ = sorted({_name for _module in _MODULES for _name in _module.__all__})

del _module
