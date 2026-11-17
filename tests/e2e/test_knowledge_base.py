"""端到端：知识库浏览、搜索、BlockNote 编辑器建文档与自动保存。"""

import json
import uuid

import pytest

from .harness import login

pytestmark = pytest.mark.e2e


def test_knowledge_index_and_search(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])

    page.goto('/knowledge/')
    page.wait_body_contains(seed['kb_doc_title'])

    page.goto('/knowledge/search?q=e2e-kb-marker')
    page.wait_body_contains(seed['kb_doc_title'])


def test_create_doc_with_blocknote_editor(page, seed, frontend_built):
    if not frontend_built:
        pytest.skip('Vite frontend build is missing; run npm run build in frontend/')
    login(page, seed['admin_username'], seed['admin_password'])

    token = uuid.uuid4().hex[:8]
    title = f'E2E 知识库新文档 {token}'
    marker = f'e2e-kb-new-marker-{token}'

    page.goto('/knowledge/doc/new')
    page.wait_for("!!window.__KB_EDITOR_INSTANCE__")
    page.wait_for("!!document.querySelector('#kb-editor-root [contenteditable=\"true\"]')")

    page.set_value('input[name="title"]', title)
    page.select_value('select[name="category_id"]', str(seed['kb_category_id']))
    page.eval(
        """
        (async function() {
            const editor = window.__KB_EDITOR_INSTANCE__;
            await editor.insertBlocks(
                [{ type: 'paragraph', content: %s }],
                editor.document[editor.document.length - 1],
                'after'
            );
            return true;
        })();
        """ % json.dumps(marker),
        await_promise=True,
    )
    page.click_by_text('button', '保存并查看')

    page.wait_for("location.pathname.match(/^\\/knowledge\\/doc\\/\\d+$/) !== null")
    page.wait_body_contains(title)
    page.wait_body_contains(marker)

    page.goto('/knowledge/search?q=' + marker)
    page.wait_body_contains(title)


def test_autosave_and_draft_endpoints(page, seed):
    login(page, seed['admin_username'], seed['admin_password'])
    doc_id = seed['kb_doc_id']
    marker = f'e2e-autosave-{uuid.uuid4().hex[:8]}'

    saved = page.fetch_json(
        f'/knowledge/doc/{doc_id}/autosave',
        method='POST',
        payload={'title': 'E2E 自动保存标题', 'content': f'# 自动保存\n\n{marker}'},
    )
    assert saved['status'] == 200
    assert saved['data']['success'] is True

    draft = page.fetch_json(f'/knowledge/doc/{doc_id}/draft')
    assert draft['status'] == 200
    assert draft['data']['success'] is True
    assert draft['data']['draft'] is not None
    assert marker in draft['data']['draft']['content']
