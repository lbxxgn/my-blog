"""时区工具（统一入口）。

约定：数据库 `created_at` / `updated_at` 均为 **naive UTC 字符串**
（SQLite `CURRENT_TIMESTAMP` 恒为 UTC）。展示与统计按 `Asia/Shanghai`（UTC+8，无夏令时）换算。

此前该逻辑在 app.py / routes/review.py / services/weekly_review.py 各写了一份，
统一到本模块，避免偏移量与实现漂移。
"""

from datetime import datetime, timedelta, timezone

# Asia/Shanghai 无夏令时，用固定偏移即可（无需 pytz）
LOCAL_OFFSET = timedelta(hours=8)
LOCAL_TZ = timezone(LOCAL_OFFSET)

DEFAULT_FMT = '%Y-%m-%d %H:%M:%S'


def utc_now():
    """当前 UTC 的 naive datetime（与 created_at 存储格式一致）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_now():
    """当前本地（UTC+8）的 naive datetime"""
    return utc_now() + LOCAL_OFFSET


def to_local(dt):
    """naive UTC datetime -> naive 本地（UTC+8）datetime"""
    return dt + LOCAL_OFFSET


def utc_to_local(value, fmt=DEFAULT_FMT):
    """UTC 时间（字符串或 datetime）-> 本地（UTC+8）格式化字符串。

    - 字符串按 ISO 解析，naive 视为 UTC，带时区则先归一化；
    - 无法解析时原样返回，保证模板不会因脏数据报错。
    """
    if not value:
        return ''
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace(' ', 'T'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        elif isinstance(value, datetime):
            dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        else:
            return value
        return dt.astimezone(LOCAL_TZ).strftime(fmt)
    except Exception:
        return value
