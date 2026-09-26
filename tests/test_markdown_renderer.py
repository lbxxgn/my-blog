"""utils.markdown_renderer 单元测试：Markdown 渲染 + XSS 清洗。"""
from utils.markdown_renderer import render_markdown


class TestRenderMarkdown:
    def test_basic_markdown(self):
        html = render_markdown('**bold** and `code`')
        assert '<strong>bold</strong>' in html
        assert '<code>code</code>' in html

    def test_fenced_code_block(self):
        html = render_markdown('```python\nprint(1)\n```')
        assert '<pre>' in html and '<code' in html

    def test_table_extra(self):
        html = render_markdown('| a | b |\n|---|---|\n| 1 | 2 |')
        assert '<table>' in html

    def test_script_stripped(self):
        html = render_markdown('hello <script>alert(1)</script>')
        assert '<script' not in html.lower()
        # 标签被转义为文本，无法执行
        assert '&lt;script&gt;' in html

    def test_event_handler_stripped(self):
        html = render_markdown('<img src="x" onerror="alert(1)">')
        assert 'onerror' not in html.lower()

    def test_javascript_href_stripped(self):
        html = render_markdown('[x](javascript:alert(1))')
        assert 'javascript:' not in html.lower()

    def test_link_and_img_attributes_kept(self):
        html = render_markdown('[link](https://example.com "t")')
        assert 'href="https://example.com"' in html
        html_img = render_markdown('![alt](https://example.com/a.png "t")')
        assert 'src="https://example.com/a.png"' in html_img
        assert 'alt="alt"' in html_img

    def test_header_ids_flag(self):
        without = render_markdown('# Title')
        with_ids = render_markdown('# Title', with_header_ids=True)
        assert '<h1>' in without
        assert 'id=' in with_ids

    def test_css_whitelist(self):
        html = render_markdown('<span style="text-indent: 2em; color: red;">x</span>')
        assert 'text-indent' in html
        assert 'color' not in html

    def test_none_and_empty(self):
        assert render_markdown(None) == render_markdown('')
        assert '<script' not in render_markdown(None).lower()
