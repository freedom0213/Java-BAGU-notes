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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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

    # ---- 1. 重建站点 ----
    print('== [1/4] 重建站点 ==')
    run([sys.executable, str(ROOT / 'tools' / 'build.py')])

    # ---- 2. 暂存 ----
    print('\n== [2/4] 暂存改动 ==')
    run(['git', 'add', '-A'])
    status = run(['git', 'status', '--porcelain'], check_ok=False)
    if not status.stdout.strip():
        print('没有检测到任何改动，无需提交。')
        return 0

    # ---- 3. 提交 ----
    print('\n== [3/4] 提交 ==')
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    run(['git', 'commit', '-m', f'chore: 更新笔记 {stamp}'])

    if no_push:
        print('\n（--no-push）已跳过推送。')
        return 0

    # ---- 4. 推送 ----
    print('\n== [4/4] 推送到 GitHub ==')
    remotes = run(['git', 'remote'], check_ok=False).stdout.split()
    if 'origin' not in remotes:
        print('!! 还没有配置远程仓库 origin，已跳过推送。')
        print('   配置命令示例：git remote add origin https://github.com/<你的账号>/<仓库名>.git')
        return 0

    # 用 gh CLI 提供凭据；先清空继承来的凭据助手，避免调用 GCM 卡死
    run(['git', '-c', 'credential.helper=',
         '-c', 'credential.helper=!gh auth git-credential',
         'push', 'origin', 'HEAD'])

    print('\n完成 ✔')
    return 0


if __name__ == '__main__':
    sys.exit(main())
