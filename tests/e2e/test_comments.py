"""端到端：文章评论提交与后台评论审核。"""

import uuid

import pytest

from .harness import login

pytestmark = pytest.mark.e2e


def _submit_comment(page, seed, content):
    page.goto(f"/post/{seed['post_id']}")
    page.wait_for("!!document.querySelector('.comment-form')")
    page.set_value('input[name="author_name"]', 'E2E 访客')
    page.set_value('textarea[name="content"]', content)
    page.click('.comment-form button[type="submit"]')
    page.wait_body_contains(content)


def test_visitor_can_submit_comment(page, seed):
    content = f'这是一条 E2E 新评论 {uuid.uuid4().hex[:8]}'
    _submit_comment(page, seed, content)

    assert content in page.body_text()
    assert page.exists('.comments-list')


def test_admin_can_hide_and_delete_comment(page, seed):
    content = f'这是一条 E2E 待审核评论 {uuid.uuid4().hex[:8]}'
    _submit_comment(page, seed, content)

    login(page, seed['admin_username'], seed['admin_password'])
    page.goto('/admin/comments')
    page.wait_body_contains(content)

    page.click_in_row(content, '隐藏')
    page.wait_body_contains('评论状态已更新')
    page.wait_body_contains(content)
    assert '已隐藏' in page.row_text(content)

    page.click_in_row(content, '删除')
    page.wait_for("!!document.querySelector('[role=\"alertdialog\"]')")
    page.click_by_text('button', '删除', last=True)
    page.wait_body_missing(content)
