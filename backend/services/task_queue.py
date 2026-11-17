"""轻量持久化后台任务队列（SQLite）。

用于替代进程内临时线程：任务落库，多 worker 通过 SQLite 事务抢占，
进程重启后可继续；失败的任按指数退避重试。
"""
import json
import logging
import os
import socket
import threading
import uuid
from datetime import datetime, timedelta

from backend.models import get_db_context

logger = logging.getLogger(__name__)

_worker_lock = threading.Lock()
_worker_thread = None
_WORKER_ID = f'{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}'


def _now_sql():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def enqueue(kind, payload, dedupe_key=None, delay_seconds=0, max_attempts=3):
    """写入任务；重复 dedupe_key 返回 None。表不存在时返回 None。"""
    run_after = (datetime.utcnow() + timedelta(seconds=delay_seconds)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with get_db_context() as conn:
            cur = conn.execute(
                '''
                INSERT INTO background_tasks (kind, dedupe_key, payload, max_attempts, run_after)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (kind, dedupe_key, json.dumps(payload, ensure_ascii=False), max_attempts, run_after),
            )
            return cur.lastrowid
    except Exception as e:
        logger.warning('enqueue background task failed: %s', e)
        return None


def _claim_next():
    with get_db_context() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute(
            '''
            SELECT * FROM background_tasks
            WHERE status = 'pending' AND run_after <= ?
            ORDER BY id LIMIT 1
            ''',
            (_now_sql(),),
        ).fetchone()
        if not row:
            return None
        updated = conn.execute(
            '''
            UPDATE background_tasks
            SET status = 'running', attempts = attempts + 1,
                locked_at = ?, locked_by = ?, updated_at = ?
            WHERE id = ? AND status = 'pending'
            ''',
            (_now_sql(), _WORKER_ID, _now_sql(), row['id']),
        ).rowcount
        if not updated:
            return None
        task = dict(row)
        task['attempts'] += 1
        return task


def _finish(task, error=None):
    with get_db_context() as conn:
        if error is None:
            conn.execute(
                "UPDATE background_tasks SET status='done', last_error=NULL, updated_at=? WHERE id=?",
                (_now_sql(), task['id']),
            )
            return
        attempts = task['attempts']
        max_attempts = task['max_attempts']
        if attempts >= max_attempts:
            conn.execute(
                "UPDATE background_tasks SET status='failed', last_error=?, updated_at=? WHERE id=?",
                (str(error)[:2000], _now_sql(), task['id']),
            )
        else:
            delay = min(300, 2 ** attempts)
            run_after = (datetime.utcnow() + timedelta(seconds=delay)).strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                '''UPDATE background_tasks
                   SET status='pending', last_error=?, run_after=?, updated_at=?
                   WHERE id=?''',
                (str(error)[:2000], run_after, _now_sql(), task['id']),
            )


def _run_task(app, task):
    kind = task['kind']
    payload = json.loads(task['payload'])
    if kind == 'review_weekly':
        from backend.routes.review import _run_weekly_review
        _run_weekly_review(app, payload['user_id'])
    elif kind == 'ai_title':
        from backend.routes.admin import posts as posts_module
        posts_module._async_ai_title(
            app, payload['post_id'], payload.get('content', ''), payload['user_id']
        )
    elif kind == 'embedding':
        from backend.tasks.embedding_task import process_embedding
        process_embedding(payload['source_type'], payload['source_id'])
    else:
        raise ValueError(f'unknown task kind: {kind}')


def _worker_loop(app, stop_event, interval):
    while not stop_event.is_set():
        task = None
        try:
            task = _claim_next()
            if task is None:
                stop_event.wait(interval)
                continue
            try:
                _run_task(app, task)
                _finish(task)
            except Exception as e:
                logger.warning('background task %s failed: %s', task['id'], e)
                _finish(task, e)
        except Exception as e:
            logger.warning('background task worker loop error: %s', e)
            stop_event.wait(interval)


def run_pending_tasks(app, max_tasks=100):
    """同步执行当前可领取的任务（测试/运维手动排空队列用）。"""
    for _ in range(max_tasks):
        task = _claim_next()
        if task is None:
            return
        try:
            _run_task(app, task)
            _finish(task)
        except Exception as e:
            _finish(task, e)


def start_worker(app, interval=1.0):
    """每个进程启动一个 worker；多进程通过 SQLite 抢占保证只执行一次。"""
    global _worker_thread
    try:
        with get_db_context() as conn:
            ready = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='background_tasks'"
            ).fetchone()
        if not ready:
            logger.info('background_tasks 表不存在，跳过任务 worker')
            return None
    except Exception as e:
        logger.warning('检查 background_tasks 失败，跳过任务 worker: %s', e)
        return None
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return _worker_thread
        stop_event = threading.Event()
        thread = threading.Thread(
            target=_worker_loop, args=(app, stop_event, interval),
            name='background-task-worker', daemon=True,
        )
        thread.start()
        _worker_thread = thread
        return thread
