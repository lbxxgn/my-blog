"""持久化后台任务队列：入队与去重。"""
from backend.models import get_db_context
from backend.services.task_queue import enqueue


def test_enqueue_dedupes_pending_task(temp_db):
    first = enqueue('embedding', {'source_type': 'post', 'source_id': 1}, dedupe_key='test:1')
    second = enqueue('embedding', {'source_type': 'post', 'source_id': 1}, dedupe_key='test:1')

    assert first
    assert second is None

    with get_db_context() as conn:
        conn.execute("DELETE FROM background_tasks WHERE dedupe_key = 'test:1'")
