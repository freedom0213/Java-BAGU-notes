# -*- coding: utf-8 -*-
"""
一次性迁移脚本：把「桌面 txt 笔记」转成 md 真源。

用法:
    python tools/convert_txt.py <输入.txt> <输出.md>

转换规则:
    行首 ========== 标题 ==========   ->  ## 标题           (章节)
    （一）小节名                      ->  ### （一）小节名   (小节)
    12：题目？                        ->  #### 12：题目？    (题目)
    （跳过）19：题目？                ->  #### （跳过）19：题目？
    其余非空行（原本缩进的答案）       ->  去掉缩进，行尾补两个空格（markdown 硬换行）
"""
import re
import sys
from pathlib import Path

CHAP_RE = re.compile(r'^=+\s*(.+?)\s*=+$')
SEC_RE = re.compile(r'^（[一二三四五六七八九十]+）[^：？]*$')
Q_RE = re.compile(r'^(\d+)：(.*)$')
QSKIP_RE = re.compile(r'^（跳过）\s*(\d+)：(.*)$')


def convert(text: str) -> str:
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    out: list[str] = []
    title_done = False
    last_kind = None  # chapter / section / question / body

    for raw in lines:
        stripped = raw.strip()

        # 空行：统一压成一个空行，正文块之间保留间隔
        if not stripped:
            if out and out[-1] != '':
                out.append('')
            continue

        # 是否顶格。只有顶格行才可能是章节 / 小节 / 题目；
        # 缩进行一律是答案正文（答案内部也会有 "1：" "2：" 这类编号步骤）。
        is_indented = raw[:1] in ('\t', ' ', '\u3000', '\u00a0')

        # 1) 文档标题（第一个非空行）
        if not title_done:
            out.append(f'# {stripped}')
            out.append('')
            title_done = True
            last_kind = 'title'
            continue

        # 2) 章节标题
        m = CHAP_RE.match(stripped)
        if m and not is_indented:
            if out and out[-1] != '':
                out.append('')
            out.append(f'## {m.group(1)}')
            out.append('')
            last_kind = 'chapter'
            continue

        # 3) 小节（（一）xxx 且不含冒号问号）
        if SEC_RE.match(stripped) and not is_indented:
            if out and out[-1] != '':
                out.append('')
            out.append(f'### {stripped}')
            out.append('')
            last_kind = 'section'
            continue

        # 4) 题目
        m = QSKIP_RE.match(stripped) or Q_RE.match(stripped)
        if m and not is_indented:
            num, rest = m.group(1), m.group(2)
            prefix = '（跳过）' if QSKIP_RE.match(stripped) else ''
            if out and out[-1] != '':
                out.append('')
            out.append(f'#### {prefix}{num}：{rest}')
            out.append('')
            last_kind = 'question'
            continue

        # 5) 正文（答案）。去掉缩进，行尾加两个空格保留作者原本的换行意图
        body = stripped
        out.append(body + '  ')
        last_kind = 'body'

    # 收尾：去掉多余空行
    while out and out[-1] == '':
        out.pop()

    return '\n'.join(out) + '\n'


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    text = src.read_text(encoding='utf-8')
    md = convert(text)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(md, encoding='utf-8')

    # 统计
    chapters = len(re.findall(r'^## ', md, re.M))
    sections = len(re.findall(r'^### ', md, re.M))
    questions = len(re.findall(r'^#### ', md, re.M))
    print(f'已生成 {dst}')
    print(f'  章节 {chapters} 个 / 小节 {sections} 个 / 题目 {questions} 道')
    print(f'  输出 {len(md.splitlines())} 行, {len(md.encode("utf-8"))} 字节')


if __name__ == '__main__':
    main()
