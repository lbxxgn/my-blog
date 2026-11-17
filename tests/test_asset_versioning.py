"""静态资源必须通过 static_file() 版本化，禁止手写 ?v= 或无版本引用。"""
import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / 'templates'
UNVERSIONED = re.compile(
    r"url_for\(\s*['\"]static['\"]\s*,\s*filename\s*=\s*['\"][^'\"]+\.(?:css|js)['\"]"
)


def test_templates_do_not_reference_unversioned_assets():
    offenders = []
    for path in TEMPLATES.rglob('*.html'):
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if UNVERSIONED.search(line):
                offenders.append(f'{path.relative_to(TEMPLATES.parent)}:{lineno}')
    assert not offenders, 'CSS/JS 必须使用 static_file(): ' + ', '.join(offenders)


def test_no_manual_asset_versions():
    offenders = []
    for path in TEMPLATES.rglob('*.html'):
        text = path.read_text(encoding='utf-8')
        for lineno, line in enumerate(text.splitlines(), 1):
            if re.search(r"\.(?:css|js)['\"]?\s*\?v=", line):
                offenders.append(f'{path.relative_to(TEMPLATES.parent)}:{lineno}')
    assert not offenders, '禁止手写资源版本号: ' + ', '.join(offenders)
