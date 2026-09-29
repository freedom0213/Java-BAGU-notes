# -*- coding: utf-8 -*-
"""
构建脚本：把真源 `Java八股.md` 拆分成 docsify 站点，输出到 `docs/`。

用法:
    python tools/build.py

产物:
    docs/README.md      首页（章节统计）
    docs/_sidebar.md    侧边栏目录
    docs/01.md ...      各章正文
    docs/.nojekyll      GitHub Pages 用（跳过 Jekyll）
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'Java八股.md'
DOCS = ROOT / 'docs'

Q_RE = re.compile(r'^#### (.+)$')


def harden_breaks(lines: list[str]) -> list[str]:
    """把答案块里的连续非空行转成 markdown 硬换行（行尾补两个空格）。

    为什么要在这里做：笔记的书写习惯是「一行一个要点」，靠换行分条。
    但 markdown 里单个换行会被合并成一段，所以必须补行尾双空格。
    这件事交给构建脚本自动完成，真源 `Java八股.md` 就不需要夹带任何隐藏字符，
    手写时不用记规则。

    空行 = 真正的段落分隔，保持不动；标题行（# 开头）也不动。
    """
    out = []
    for ln in lines:
        s = ln.rstrip()
        if not s or s.startswith('#'):
            out.append(s)
        else:
            out.append(s + '  ')
    return out


def parse(text: str):
    doc_title = 'Java 八股文笔记'
    chapters: list[dict] = []
    cur = None
    for ln in text.replace('\r\n', '\n').split('\n'):
        if ln.startswith('# ') and not ln.startswith('##'):
            doc_title = ln[2:].strip()
            continue
        if ln.startswith('## '):
            cur = {'title': ln[3:].strip(), 'body': []}
            chapters.append(cur)
            continue
        if cur is not None:
            cur['body'].append(ln)
    return doc_title, chapters


def stats(chapter: dict) -> tuple[int, int]:
    """返回 (题目数, 已作答题数)。题目下方只要有正文就算已作答。"""
    total = answered = 0
    pending_has_body = None  # None=还没遇到题目
    for ln in chapter['body']:
        if Q_RE.match(ln):
            if pending_has_body:
                answered += 1
            total += 1
            pending_has_body = False
            continue
        s = ln.strip()
        if pending_has_body is not None and s and not s.startswith('#'):
            pending_has_body = True
    if pending_has_body:
        answered += 1
    return total, answered


def main() -> None:
    if not SRC.exists():
        print(f'找不到真源文件: {SRC}', file=sys.stderr)
        sys.exit(1)

    doc_title, chapters = parse(SRC.read_text(encoding='utf-8'))
    if not chapters:
        print('真源里没有解析到任何 `## ` 章节。', file=sys.stderr)
        sys.exit(1)

    DOCS.mkdir(parents=True, exist_ok=True)

    # 清理上一轮的章节产物（只删 01.md 这类数字命名的文件，不碰其他）
    for old in DOCS.glob('[0-9][0-9].md'):
        old.unlink()

    sidebar = ['- [🏠 首页](/README.md)']
    index_rows = []
    grand_total = grand_answered = 0

    for i, ch in enumerate(chapters, start=1):
        fname = f'{i:02d}.md'
        body = '\n'.join(harden_breaks(ch['body'])).strip() + '\n'
        content = f'# {ch["title"]}\n\n' + body
        content = re.sub(r'\n{3,}', '\n\n', content)
        # newline='\n'：强制 LF 落盘，与 .gitattributes 的 eol=lf 保持一致，
        # 否则 Windows 上会写成 CRLF，每次提交都冒 "LF will be replaced by CRLF" 警告。
        (DOCS / fname).write_text(content, encoding='utf-8', newline='\n')

        total, answered = stats(ch)
        grand_total += total
        grand_answered += answered

        sidebar.append(f'- [{i}. {ch["title"]}]({fname})')
        index_rows.append(f'| [{ch["title"]}]({fname}) | {total} | {answered} |')

    # 侧边栏
    (DOCS / '_sidebar.md').write_text('\n'.join(sidebar) + '\n', encoding='utf-8', newline='\n')

    # 首页
    home = [
        f'# {doc_title}',
        '',
        '> 面试复习题库 · 纯文本单一真源，构建产物自动生成',
        '',
        f'**{len(chapters)} 个章节 · {grand_total} 道题目 · 已作答 {grand_answered} 道 · 待作答 {grand_total - grand_answered} 道**',
        '',
        '| 章节 | 题目数 | 已作答 |',
        '| :--- | ---: | ---: |',
        *index_rows,
        f'| **合计** | **{grand_total}** | **{grand_answered}** |',
        '',
        '---',
        '',
        '手机上点左上角 ☰ 展开目录、点右上角 🔍 搜索题目；表格里的章节名可直接点开。',
        '',
    ]
    (DOCS / 'README.md').write_text('\n'.join(home), encoding='utf-8', newline='\n')

    # GitHub Pages 用：不让 Jekyll 处理，保住 _sidebar.md
    (DOCS / '.nojekyll').write_text('', encoding='utf-8')

    print(f'构建完成 -> {DOCS}')
    print(f'  章节 {len(chapters)} 个')
    print(f'  题目 {grand_total} 道，已作答 {grand_answered} 道，未作答 {grand_total - grand_answered} 道')
    for i, ch in enumerate(chapters, start=1):
        t, a = stats(ch)
        print(f'    {i:02d}. {ch["title"]}  ({a}/{t})')


if __name__ == '__main__':
    main()
