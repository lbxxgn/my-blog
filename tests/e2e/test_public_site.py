"""端到端：公开博客浏览、文章详情、搜索、分类/标签/归档页。"""

from urllib.parse import quote

import pytest

pytestmark = pytest.mark.e2e


def test_homepage_lists_only_published_posts(page, seed):
    page.goto('/')
    page.wait_for("document.querySelectorAll('.post-card').length > 0")

    body = page.body_text()
    assert 'E2E 已发布文章' in body
    assert 'E2E 已发布文章二' in body
    assert seed['draft_title'] not in body


def test_post_detail_renders_content_tags_and_comments(page, seed):
    page.goto(f"/post/{seed['post_id']}")
    page.wait_body_contains(seed['post_title'])

    body = page.body_text()
    assert 'e2e-marker' in body
    assert 'E2E标签' in body
    assert seed['seed_comment'] in body


def test_search_form_finds_post_and_empty_state(page, seed):
    page.goto('/')
    page.wait_for("!!document.querySelector('.search-form-nav input[name=\"q\"]')")
    page.set_value('.search-form-nav input[name="q"]', 'e2e-marker')
    page.click('.search-form-nav button[type="submit"]')

    page.wait_path('/search')
    page.wait_body_contains(seed['post_title'])
    assert 'e2e-marker' in page.body_text()

    page.goto('/search?q=no-such-e2e-keyword-xyz')
    page.wait_body_contains('未找到与')


def test_category_tag_and_archive_pages(page, seed):
    page.goto(f"/category/{seed['category_id']}")
    page.wait_body_contains(seed['post_title'])

    page.goto(f"/tag/{seed['tag_id']}")
    page.wait_body_contains(seed['post_title'])

    page.goto('/tags')
    page.wait_body_contains('E2E标签')

    page.goto('/archive')
    page.wait_body_contains(seed['post_title'])


def test_public_api_posts_cursor(page, seed):
    page.goto('/')
    payload = page.fetch_json('/api/posts?per_page=10')
    assert payload['status'] == 200
    data = payload['data']
    assert data['success'] is True
    titles = [post['title'] for post in data['posts']]
    assert seed['post_title'] in titles
    assert seed['draft_title'] not in titles


def test_share_qrcode_api(page):
    page.goto('/')
    payload = page.fetch_json('/api/share/qrcode?url=' + quote('https://example.com/post/1'))
    assert payload['status'] == 200
    assert payload['data']['qrcode'].startswith('data:image/png;base64,')
