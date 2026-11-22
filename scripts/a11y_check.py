#!/usr/bin/env python3
"""用 axe-core 对本地站点做一次 WCAG 2A/2AA 巡检。

前置条件：
    1. 本地已启动开发服务器（默认 http://127.0.0.1:5001）
    2. 已安装 Playwright 与 Chrome：`pip install playwright`
    3. 已安装前端依赖（axe-core 从 frontend/node_modules 读取）：`cd frontend && npm ci`

用法：
    python scripts/a11y_check.py [base_url]

说明：
    - 需要登录的页面会用 .env 里的 ADMIN_USERNAME / ADMIN_PASSWORD 登录。
    - 退出码始终为 0（这是巡检而非卡口），结果用于人工判断。
    - 已知遗留问题见 docs/engineering-backlog-2026-11.md 的 FE-12。
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

BASE = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:5001').rstrip('/')
ROOT = pathlib.Path(__file__).resolve().parent.parent
AXE_PATH = ROOT / 'frontend' / 'node_modules' / 'axe-core' / 'axe.min.js'

PAGES = [
    '/',
    '/archive',
    '/tags',
    '/post/150',
    '/login',
    '/admin/',
    '/admin/new',
    '/knowledge/',
]


def read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = ROOT / '.env'
    if not path.exists():
        return env
    for line in path.read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)', line)
        if not m:
            continue
        value = m.group(2).strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        env[m.group(1)] = value
    return env


def main() -> int:
    if not AXE_PATH.exists():
        print(f'找不到 {AXE_PATH}，请先在 frontend/ 执行 npm ci')
        return 1

    from playwright.sync_api import sync_playwright

    axe_source = AXE_PATH.read_text(encoding='utf-8')
    env = read_env()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome')
        page = browser.new_context(viewport={'width': 1280, 'height': 900}).new_page()

        if env.get('ADMIN_USERNAME') and env.get('ADMIN_PASSWORD'):
            page.goto(BASE + '/login', wait_until='networkidle')
            page.fill('#username', env['ADMIN_USERNAME'])
            page.fill('#password', env['ADMIN_PASSWORD'])
            page.press('#password', 'Enter')
            page.wait_for_load_state('networkidle')

        total = 0
        for path in PAGES:
            page.goto(BASE + path, wait_until='networkidle')
            page.add_script_tag(content=axe_source)
            violations = page.evaluate(
                """async () => {
                  const res = await axe.run(document,
                    {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa']}});
                  return res.violations.map(v => ({
                    id: v.id, impact: v.impact,
                    count: v.nodes.length,
                    sample: v.nodes.slice(0, 2).map(n => n.target.join(' ')),
                  }));
                }"""
            )
            print(f'{path}  violations={len(violations)}')
            for v in violations:
                total += v['count']
                print(f"   {v['impact']:<8} {v['id']} x{v['count']}  {v['sample']}")

        print(f'\n合计受影响节点: {total}')
        browser.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
