"""端到端：后台文章创建、发布、编辑、草稿、下架、删除与恢复。"""

import json
import uuid
from urllib.parse import quote

import pytest

from .harness import login

pytestmark = pytest.mark.e2e


def _create_published_post(page, seed, prefix='E2E 新建文章'):
    token = uuid.uuid4().hex[:8]
    title = f'{prefix} {token}'
    content = f'E2E 正文 {token}'

    page.goto('/admin/new')
    page.wait_for("!!window.quill && typeof window.setQuillHtml === 'function'")
    page.set_value('#title', title)
    if seed.get('category_id'):
        page.set_value('#category_id', str(seed['category_id']))
    page.set_value('#tags', 'E2E创建,自动化')
    page.eval(f'window.setQuillHtml({json.dumps(f"<p>{content}</p>")}); true')
    page.click('#publishToggle')

    page.wait_path('/post/')
    page.wait_body_contains(title)
    post_id = int(page.path().rstrip('/').split('/')[-1])
    return post_id, title, content


def test_create_and_publish_post_from_editor(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])
    post_id, title, content = _create_published_post(page, seed)

    body = page.body_text()
    assert title in body
    assert content in body
    assert 'E2E创建' in body

    page.goto('/admin/')
    page.wait_body_contains(title)
    row = page.row_text(title)
    assert '已发布' in row

    page.goto(f'/post/{post_id}')
    page.wait_body_contains(title)


def test_edit_published_post(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])
    post_id, title, _ = _create_published_post(page, seed, prefix='E2E 待编辑文章')
    updated_title = f'{title} 已更新'

    page.goto(f'/admin/edit/{post_id}')
    page.wait_for('!!window.quill')
    page.set_value('#title', updated_title)
    page.click('#saveBtn')
    page.wait_fetch_contains(f'/post/{post_id}', updated_title)

    page.goto(f'/post/{post_id}')
    page.wait_body_contains(updated_title)


def test_save_as_draft_is_not_public(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])
    token = uuid.uuid4().hex[:8]
    title = f'E2E 保存草稿 {token}'

    page.goto('/admin/new')
    page.wait_for("!!window.quill && typeof window.setQuillHtml === 'function'")
    page.set_value('#title', title)
    page.eval(f'window.setQuillHtml({json.dumps(f"<p>草稿正文 {token}</p>")}); true')
    page.click('#saveBtn')

    page.wait_path('/admin/edit/')
    page.wait_fetch_contains('/admin/?status=draft', title)

    page.goto('/')
    page.wait_body_missing(title)


def test_unpublish_post(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])
    post_id, title, _ = _create_published_post(page, seed, prefix='E2E 待下架文章')

    page.goto(f'/admin/edit/{post_id}')
    page.wait_for('!!window.quill')
    page.click_by_text('button', '取消发布')

    page.wait_body_contains('已取消发布')
    page.wait_fetch_contains(f'/admin/?status=draft&q={quote(title)}', title)


def test_delete_to_trash_and_restore(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])
    _, title, _ = _create_published_post(page, seed, prefix='E2E 待删除文章')

    page.goto('/admin/')
    page.wait_body_contains(title)
    page.click_in_row(title, '删除')
    page.wait_for(
        "Array.from(document.querySelectorAll('button')).some((el) => el.textContent.trim() === '移入回收站')"
    )
    page.click_by_text('button', '移入回收站', last=True)
    page.wait_body_missing(title)

    page.goto('/admin/trash')
    page.wait_body_contains(title)
    page.click_in_row(title, '恢复')
    page.wait_body_missing(title)

    page.goto('/admin/')
    page.wait_body_contains(title)
