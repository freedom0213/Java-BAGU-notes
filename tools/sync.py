# -*- coding: utf-8 -*-
"""
一键同步：重建站点 -> 提交 -> 推送。

用法（在仓库根目录）:
    python tools/sync.py            # 构建 + 提交 + 推送
    python tools/sync.py --no-push  # 只构建 + 提交，不推送

推送走本机已认证的 gh CLI 拿凭据，不需要额外配置用户名密码。
"""
import datetime
import subprocess
import sys
import time
from pathlib import Path

# Windows 控制台默认按 GBK 输出，这里统一成 UTF-8，避免中文提示乱码
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, 'reconfigure'):
        try:
            _s.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# 笔记原文（txt）路径。
#
# ★ 这里才是你的真源：平时用记事本 / VSCode 随便哪个编辑器改这个 txt，
#   双击「同步到GitHub.bat」时脚本会自动把它转换成 Java八股.md 再发布。
#   Java八股.md 属于自动生成物，不要手改（改了也会被下次同步覆盖）。
#
# 换电脑 / 改文件名 / 移动位置时，只改下面这一行即可。
# ============================================================
NOTE_TXT = Path(r'C:\Users\freedom\Desktop\java八股2.txt')


def run(cmd, check_ok=True):
    print('$ ' + ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    for stream in (r.stdout, r.stderr):
        if stream and stream.strip():
            print(stream.rstrip())
    if check_ok and r.returncode != 0:
        raise SystemExit(f'!! 命令失败（退出码 {r.returncode}）: {" ".join(cmd)}')
    return r


def main() -> int:
    no_push = '--no-push' in sys.argv

    # ---- 0. 环境检查 ----
    if not (ROOT / '.git').exists():
        print('!! 当前目录还不是 git 仓库，请先执行：git init -b main')
        return 1

    # ---- 1. 从 txt 生成真源 ----
    print('== [1/5] 从笔记原文生成真源 ==')
    if not NOTE_TXT.exists():
        print(f'!! 没找到笔记原文：{NOTE_TXT}')
        print('   为避免出现「以为同步了、其实没更新」，这里直接停下。')
        print('   如果文件改名或移动过，请修改 tools/sync.py 顶部的 NOTE_TXT。')
        return 1
    print(f'原文: {NOTE_TXT}')
    run([sys.executable, str(ROOT / 'tools' / 'convert_txt.py'),
         str(NOTE_TXT), str(ROOT / 'Java八股.md')])

    # ---- 2. 重建站点 ----
    print('\n== [2/5] 重建站点 ==')
    run([sys.executable, str(ROOT / 'tools' / 'build.py')])

    # ---- 3. 暂存 ----
    print('\n== [3/5] 暂存改动 ==')
    run(['git', 'add', '-A'])
    status = run(['git', 'status', '--porcelain'], check_ok=False)
    if not status.stdout.strip():
        print('没有检测到任何改动，无需提交。')
        return 0

    # ---- 4. 提交 ----
    print('\n== [4/5] 提交 ==')
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    run(['git', 'commit', '-m', f'chore: 更新笔记 {stamp}'])

    if no_push:
        print('\n（--no-push）已跳过推送。')
        return 0

    # ---- 5. 推送 ----
    print('\n== [5/5] 推送到 GitHub ==')
    remotes = run(['git', 'remote'], check_ok=False).stdout.split()
    if 'origin' not in remotes:
        print('!! 还没有配置远程仓库 origin，已跳过推送。')
        print('   配置命令示例：git remote add origin https://github.com/<你的账号>/<仓库名>.git')
        return 0

    # 用 gh CLI 提供凭据；先清空继承来的凭据助手，避免调用 GCM 卡死。
    # 网络偶发抖动（例如 "Recv failure: Connection was reset"）时自动重试。
    push_cmd = ['git', '-c', 'credential.helper=',
                '-c', 'credential.helper=!gh auth git-credential',
                'push', 'origin', 'HEAD']
    for attempt in range(1, 4):
        print(f'$ {" ".join(push_cmd)}    (第 {attempt}/3 次)')
        r = subprocess.run(push_cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        for stream in (r.stdout, r.stderr):
            if stream and stream.strip():
                print(stream.rstrip())
        if r.returncode == 0:
            break
        if attempt < 3:
            print('推送失败，5 秒后自动重试…')
            time.sleep(5)
    else:
        print('\n!! 推送连续 3 次失败。')
        print('   你的改动已经提交到本地仓库，不会丢失。')
        print('   常见原因：')
        print('     1) 网络/代理抖动 —— 过一会儿再双击本脚本即可，会自动补上。')
        print('     2) 代理软件没开 —— 本机 git 走 http.proxy=127.0.0.1:65532，确认它在运行。')
        return 1

    print('\n完成 ✔')
    return 0


if __name__ == '__main__':
    sys.exit(main())
