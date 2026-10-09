# -*- coding: utf-8 -*-
"""
一键同步：重建站点 -> 提交 -> 推送。

用法（在仓库根目录）:
    python tools/sync.py            # 构建 + 提交 + 推送
    python tools/sync.py --no-push  # 只构建 + 提交，不推送

推送走本机已认证的 gh CLI 拿凭据，不需要额外配置用户名密码。
"""
import datetime
import os
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


def run(cmd, check_ok=True, env=None):
    print('$ ' + ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
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

    # ---- 推送用的子进程环境：两条都不能省，都是实测踩出来的 ----
    #
    # 1) GIT_CONFIG_NOSYSTEM=1
    #    本机 PATH 上命中的 git 是 D:\skywaimai\Git，它的**系统级** gitconfig 里有：
    #        [url "git@github.com:"]  insteadOf = https://github.com/
    #        [core] sshCommand = ssh ... -o HostName=ssh.github.com -p 443 ...
    #    于是一句 git push 会先把 https 地址改写成 SSH，再直连 ssh.github.com:443。
    #    而本机到那个地址是 100% 被重置（Connection reset）—— 试 3 次也全失败，
    #    表现为「推送连续 3 次失败」，但改任何账号密码都无效。
    #    让这个子进程无视系统配置，就回到 https + 本机 http.proxy，实测稳定。
    #    （只影响这一次推送，不改任何全局/系统配置文件。）
    #
    # 2) 剔除 *_proxy 环境变量
    #    某些注入的代理不支持 CONNECT 隧道，会让 git 静默挂死、零输出，极难排查。
    push_env = os.environ.copy()
    for _k in list(push_env):
        if _k.lower() in ('http_proxy', 'https_proxy', 'all_proxy', 'ftp_proxy'):
            push_env.pop(_k, None)
    push_env['GIT_CONFIG_NOSYSTEM'] = '1'

    # 推送前先确认 git 最终会用哪个地址（这一步是本地操作，不联网）。
    # 若被 url.insteadOf 改写，地址会变成 git@github.com:... —— 直接拦下并说清原因，
    # 而不是让它去撞一个必然失败的 SSH 连接。
    target = run(['git', 'ls-remote', '--get-url', 'origin'],
                 check_ok=False, env=push_env).stdout.strip()
    print(f'推送目标: {target or "(读不到)"}')
    if not target.startswith('https://'):
        print('\n!! 推送地址不是 https，已中止。')
        print('   多半是本机 git 配置里有 url.*.insteadOf 改写规则，把 GitHub 地址')
        print('   换成了 SSH。本脚本只走 https（本机 SSH 到 GitHub 不通）。')
        print('   排查：git config --show-origin --get-regexp "url\\..*insteadof"')
        return 1

    # 用 gh CLI 提供凭据；先清空继承来的凭据助手，避免调用 GCM 卡死。
    # 网络偶发抖动时自动重试。
    push_cmd = ['git', '-c', 'credential.helper=',
                '-c', 'credential.helper=!gh auth git-credential',
                'push', 'origin', 'HEAD']
    for attempt in range(1, 4):
        print(f'$ {" ".join(push_cmd)}    (第 {attempt}/3 次)')
        r = subprocess.run(push_cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', env=push_env)
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
        print('     2) 代理软件没开 —— 确认本机 git 配的 http.proxy 在运行。')
        return 1

    print('\n完成 ✔')
    return 0


if __name__ == '__main__':
    sys.exit(main())
