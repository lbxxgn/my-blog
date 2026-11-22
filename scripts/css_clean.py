#!/usr/bin/env python3
"""CSS 整理工具：格式化 + 合并重复选择器 + 检查重复。

用途
----
1. 把压缩成单行的样式表展开为可读格式（规则声明逐行）。
2. 合并同一文件中「媒体查询 + 选择器」完全相同的规则，减少覆盖链。
3. 检查文件内是否还存在重复选择器（`--check`，可用于 CI）。

用法
----
    python scripts/css_clean.py static/css/foo.css                 # 原地整理
    python scripts/css_clean.py --dry-run static/css/foo.css       # 只报告
    python scripts/css_clean.py --merge first static/css/foo.css   # 保留首次出现的位置
    python scripts/css_clean.py --drop-selector '.a{b}' foo.css    # 丢弃指定规则
    python scripts/css_clean.py --drop-keyframes spin foo.css      # 丢弃同名动画
    python scripts/css_clean.py --check static/css/*.css           # 只检查重复

合并语义
--------
重复选择器合并后，声明顺序为「先出现的值 -> 后出现的值」，因此**最终生效的值不变**；
规则落在哪一次出现的位置由 `--merge` 决定（默认 `last`，即保留最后一次出现的位置，
把此前只在该选择器里出现过的声明并入其中）。合并结果仍建议用真实页面回归确认，
因为声明位置变化理论上可能与「只对部分选择器生效的中间覆盖」相互作用。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import tinycss2

COMMENT_BANNER = """/*
 * {name}
 *
 * 由 scripts/css_clean.py 整理：仅做格式化与重复选择器合并，未改动声明内容。
 * 新增样式请直接修改对应规则，不要追加同名覆盖块。
 */"""


def _norm_query(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"\s*:\s*", ": ", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    return text


def _norm_selector(sel: str) -> str:
    sel = re.sub(r"\s+", " ", sel.strip())
    sel = re.sub(r"\s*([>+~])\s*", r" \1 ", sel)
    return re.sub(r"\s+", " ", sel).strip()


def _parse_block(content) -> tuple[list[tuple], list[list[str]], list[str]]:
    """解析声明块。

    返回 `(声明, 每条声明前紧跟的注释, 块尾注释)`，三者一起保证规则内容
    （包括「为什么这么写」的行内注释）在整理后不丢失。
    """
    decls: list[tuple] = []
    comments: list[list[str]] = []
    pending: list[str] = []
    for node in tinycss2.parse_declaration_list(
        content, skip_comments=False, skip_whitespace=True
    ):
        if node.type == "comment":
            pending.append(node.serialize().strip())
        elif node.type == "declaration":
            decls.append(
                (node.lower_name, tinycss2.serialize(node.value).strip(), bool(node.important))
            )
            comments.append(pending)
            pending = []
    return decls, comments, pending


def parse(path: Path) -> list[dict]:
    """把样式表解析成有序条目列表（保留注释）。"""
    entries: list[dict] = []

    def walk(nodes, media):
        for node in nodes:
            if node.type == "comment":
                entries.append({"kind": "comment", "media": media, "text": node.serialize().strip()})
            elif node.type == "qualified-rule":
                selectors = [
                    _norm_selector(s)
                    for s in tinycss2.serialize(node.prelude).split(",")
                    if s.strip()
                ]
                decls, comments, tail = _parse_block(node.content)
                entries.append(
                    {
                        "kind": "rule",
                        "media": media,
                        "selectors": selectors,
                        "decls": decls,
                        "comments": comments,
                        "tail": tail,
                    }
                )
            elif node.type == "at-rule" and node.content is not None:
                if node.lower_at_keyword in ("media", "supports"):
                    query = _norm_query(tinycss2.serialize(node.prelude))
                    walk(
                        tinycss2.parse_rule_list(
                            node.content, skip_comments=False, skip_whitespace=True
                        ),
                        media + ((node.lower_at_keyword, query),),
                    )
                elif node.lower_at_keyword == "keyframes":
                    frames = []
                    for frame in tinycss2.parse_rule_list(
                        node.content, skip_comments=True, skip_whitespace=True
                    ):
                        if frame.type != "qualified-rule":
                            continue
                        decls = [
                            (d.lower_name, tinycss2.serialize(d.value).strip(), bool(d.important))
                            for d in tinycss2.parse_declaration_list(
                                frame.content, skip_comments=True, skip_whitespace=True
                            )
                            if d.type == "declaration"
                        ]
                        frames.append((_norm_selector(tinycss2.serialize(frame.prelude)), decls))
                    entries.append(
                        {
                            "kind": "keyframes",
                            "media": media,
                            "name": _norm_query(tinycss2.serialize(node.prelude)),
                            "frames": frames,
                        }
                    )
                else:
                    entries.append(
                        {
                            "kind": "raw",
                            "media": media,
                            "text": "@%s %s {%s}"
                            % (
                                node.lower_at_keyword,
                                tinycss2.serialize(node.prelude).strip(),
                                tinycss2.serialize(node.content).strip(),
                            ),
                        }
                    )

    walk(
        tinycss2.parse_stylesheet(Path(path).read_text(), skip_comments=False, skip_whitespace=True),
        (),
    )
    return entries


def expand(entries: list[dict]) -> list[dict]:
    out = []
    for entry in entries:
        if entry["kind"] == "rule":
            for selector in entry["selectors"]:
                out.append(
                    {
                        "kind": "rule",
                        "media": entry["media"],
                        "selector": selector,
                        "decls": list(entry["decls"]),
                        "comments": [list(notes) for notes in entry["comments"]],
                        "tail": list(entry["tail"]),
                    }
                )
        else:
            out.append(dict(entry))
    return out


def merge(entries: list[dict], mode: str) -> tuple[list[dict], list[str]]:
    """合并 (媒体查询, 选择器) 相同的规则，返回合并后的条目与被合并的选择器列表。"""
    if mode == "none":
        return entries, []

    # 先按出现顺序收集
    order: list[tuple] = []
    buckets: dict[tuple, list[dict]] = {}
    for entry in entries:
        if entry["kind"] != "rule":
            continue
        key = (entry["media"], entry["selector"])
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(entry)

    merged: dict[tuple, dict] = {}
    target_entry: dict[tuple, dict] = {}
    touched: list[str] = []
    for key in order:
        occurrences = buckets[key]
        target = occurrences[0] if mode == "first" else occurrences[-1]
        target_entry[key] = target
        decls: list[tuple] = []
        comments: list[list[str]] = []
        tail: list[str] = []
        blocks: list[list[tuple]] = []
        for occurrence in occurrences:
            # 单条规则内部允许同名声明（100vh -> 100dvh 之类的回退写法），必须原样保留；
            # 只有「更靠后的规则」才覆盖「更靠前的规则」里的同名声明。
            block = list(zip(occurrence["decls"], occurrence["comments"]))
            names = {decl[0] for decl, _ in block}
            for earlier in blocks:
                earlier[:] = [(decl, notes) for decl, notes in earlier if decl[0] not in names]
            blocks.append(block)
            for note in occurrence["tail"]:
                if note not in tail:
                    tail.append(note)
        for block in blocks:
            for decl, notes in block:
                decls.append(decl)
                comments.append(list(notes))
        if len(occurrences) > 1:
            touched.append(key[1])
        merged[key] = {
            "kind": "rule",
            "media": key[0],
            "selector": key[1],
            "decls": decls,
            "comments": comments,
            "tail": tail,
        }

    out = []
    for entry in entries:
        if entry["kind"] != "rule":
            out.append(entry)
            continue
        key = (entry["media"], entry["selector"])
        if entry is target_entry[key]:
            out.append(merged[key])
    return out, touched


def group(entries: list[dict]) -> list[dict]:
    """把相邻且声明完全相同的规则重新合回选择器组，减少体积。"""
    grouped: list[dict] = []
    for entry in entries:
        if entry["kind"] != "rule":
            grouped.append(entry)
            continue
        last = grouped[-1] if grouped else None
        if (
            last
            and last["kind"] == "rule"
            and last["media"] == entry["media"]
            and last["decls"] == entry["decls"]
            and last["comments"] == entry["comments"]
            and last["tail"] == entry["tail"]
        ):
            last["selectors"].append(entry["selector"])
        else:
            grouped.append(
                {
                    "kind": "rule",
                    "media": entry["media"],
                    "selectors": [entry["selector"]],
                    "decls": list(entry["decls"]),
                    "comments": [list(notes) for notes in entry["comments"]],
                    "tail": list(entry["tail"]),
                }
            )
    return grouped


def _comment_lines(note: str, indent: str) -> list[str]:
    return [indent + line.rstrip() for line in note.splitlines()]


def format_decl(decls) -> list[str]:
    lines = []
    for name, value, important in decls:
        value = re.sub(r"\s+", " ", value).strip()
        lines.append(f'    {name}: {value}{" !important" if important else ""};')
    return lines


def emit(entries: list[dict], banner: str | None) -> str:
    lines: list[str] = []
    if banner:
        lines.extend([banner, ""])
    media_stack: tuple = ()

    def close_to(depth: int) -> None:
        nonlocal media_stack
        while len(media_stack) > depth:
            lines.append("    " * (len(media_stack) - 1) + "}")
            media_stack = media_stack[:-1]

    for entry in entries:
        media = entry["media"]
        common = 0
        while (
            common < len(media)
            and common < len(media_stack)
            and media[common] == media_stack[common]
        ):
            common += 1
        close_to(common)
        while len(media_stack) < len(media):
            kind, query = media[len(media_stack)]
            lines.append("    " * len(media_stack) + f"@{kind} {query} {{")
            media_stack = media_stack + (media[len(media_stack)],)

        indent = "    " * len(media_stack)
        if entry["kind"] == "comment":
            lines.append(indent + entry["text"])
        elif entry["kind"] == "raw":
            lines.append(indent + entry["text"])
        elif entry["kind"] == "keyframes":
            lines.append(f'{indent}@keyframes {entry["name"]} {{')
            for frame_sel, decls in entry["frames"]:
                lines.append(f"{indent}    {frame_sel} {{")
                lines.extend(indent + "    " + line for line in format_decl(decls))
                lines.append(f"{indent}    }}")
            lines.append(indent + "}")
            lines.append("")
        else:
            head = (",\n" + indent).join(entry["selectors"])
            lines.append(f"{indent}{head} {{")
            pad = indent + "    "
            for (name, value, important), notes in zip(entry["decls"], entry["comments"]):
                for note in notes:
                    lines.extend(_comment_lines(note, pad))
                value = re.sub(r"\s+", " ", value).strip()
                lines.append(f'{pad}{name}: {value}{" !important" if important else ""};')
            for note in entry["tail"]:
                lines.extend(_comment_lines(note, pad))
            lines.append(indent + "}")
            lines.append("")
    close_to(0)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip() + "\n"


def duplicate_keys(entries: list[dict]) -> list[tuple]:
    seen: dict[tuple, int] = {}
    dupes = []
    for entry in entries:
        if entry["kind"] != "rule":
            continue
        key = (entry["media"], entry["selector"])
        seen[key] = seen.get(key, 0) + 1
        if seen[key] == 2:
            dupes.append(key)
    return dupes


def drop(entries: list[dict], selectors: list[str], keyframes: list[str]) -> list[str]:
    """按选择器 / 动画名删除规则，返回删除说明。"""
    removed = []
    kept = []
    for entry in entries:
        if entry["kind"] == "keyframes" and entry["name"] in keyframes:
            removed.append(f'@keyframes {entry["name"]}')
            continue
        if entry["kind"] == "rule":
            key_with_media = "{}|{}".format(
                " > ".join(q[1] for q in entry["media"]), entry["selector"]
            )
            if entry["selector"] in selectors or key_with_media in selectors:
                removed.append(entry["selector"])
                continue
        kept.append(entry)
    return kept, removed


def process(path: Path, args) -> tuple[str, list[str], list[str]]:
    entries = expand(parse(path))
    entries, dropped = drop(entries, args.drop_selector, args.drop_keyframes)
    merged, touched = merge(entries, args.merge)
    # 合并后可能产生相邻同声明规则，重新分组以压缩体积
    text = emit(group(merged), None)
    return text, touched, dropped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CSS 格式化 + 重复选择器合并")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--merge", choices=["last", "first", "none"], default="last",
                        help="重复选择器并入首次还是末次出现的位置（默认 last）")
    parser.add_argument("--drop-selector", action="append", default=[],
                        help="删除指定选择器的规则，可重复；也可写成 '媒体查询|选择器'")
    parser.add_argument("--drop-keyframes", action="append", default=[],
                        help="删除同名 @keyframes，可重复")
    parser.add_argument("--dry-run", action="store_true", help="只报告，不写回文件")
    parser.add_argument("--check", action="store_true", help="只检查重复选择器，有重复则退出码 1")
    parser.add_argument("--no-banner", action="store_true", help="不写文件头说明")
    args = parser.parse_args(argv)

    failed = False
    for path in args.files:
        if args.check:
            dupes = duplicate_keys(expand(parse(path)))
            if dupes:
                failed = True
                print(f"{path}: 仍有 {len(dupes)} 个重复选择器")
                for media, selector in dupes[:10]:
                    where = " > ".join(q[1] for q in media) or "base"
                    print(f"  [{where}] {selector}")
            else:
                print(f"{path}: OK（无重复选择器）")
            continue

        original = path.read_text()
        text, touched, dropped = process(path, args)
        if not args.no_banner:
            text = COMMENT_BANNER.format(name=path.name) + "\n" + text
        changed = text != original
        rel = path
        if changed and not args.dry_run:
            path.write_text(text)
        print(
            f"{rel}: {'已更新' if changed and not args.dry_run else '无变化' if not changed else '将更新'}"
            f"（合并 {len(touched)} 个重复选择器"
            + (f"，删除 {len(dropped)} 条规则" if dropped else "")
            + "）"
        )
        if touched and args.dry_run:
            for selector in touched:
                print(f"  合并: {selector}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
