# -*- coding: utf-8 -*-
"""
KShell 远程部署模板（安全版）

凭据从环境变量读取，不要把密码写进代码：

  set KSH_DEPLOY_HOST=your.server.ip
  set KSH_DEPLOY_USER=root
  set KSH_DEPLOY_PASS=your-password
  python packaging/deploy_template.py

功能: 上传源码到服务器 → 安装 PyInstaller → 构建 Linux deb 包
依赖: pip install paramiko
"""

import os
import pathlib
import sys

try:
    import paramiko
except ImportError:
    print("请先安装 paramiko: pip install paramiko")
    sys.exit(1)

HOST = os.environ.get('KSH_DEPLOY_HOST', '')
USER = os.environ.get('KSH_DEPLOY_USER', 'root')
PASS = os.environ.get('KSH_DEPLOY_PASS', '')
REMOTE_DIR = os.environ.get('KSH_DEPLOY_DIR', '/root/kshell')

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

# 需要上传的文件
SOURCE_FILES = [
    'kshell.py', 'terminal.py', 'kplatform.py', 'syscmd.py', 'filesystem.py',
    'parser.py', 'process.py', 'builtin.py', 'settings.py',
    'banner.py', 'theme.py', 'commands_extra.py',
    'kshell.spec', 'README.md', 'example.ksh',
]
PACKAGING_FILES = ['build_linux.sh']


def main() -> int:
    if not HOST or not PASS:
        print("错误: 请先设置环境变量 KSH_DEPLOY_HOST 和 KSH_DEPLOY_PASS")
        print("（不要把密码写进代码或提交到仓库）")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=22, username=USER, password=PASS, timeout=20)

    try:
        sftp = client.open_sftp()
        for directory in (REMOTE_DIR, f'{REMOTE_DIR}/packaging'):
            try:
                sftp.mkdir(directory)
            except IOError:
                pass

        print(f'上传源码到 {HOST}:{REMOTE_DIR}')
        for name in SOURCE_FILES:
            local = PROJECT_ROOT / name
            if local.exists():
                sftp.put(str(local), f'{REMOTE_DIR}/{name}')
                print(f'  [OK] {name}')
        for name in PACKAGING_FILES:
            local = PROJECT_ROOT / 'packaging' / name
            if local.exists():
                sftp.put(str(local), f'{REMOTE_DIR}/packaging/{name}')
                print(f'  [OK] packaging/{name}')
        sftp.close()

        print('\n安装 PyInstaller 并构建 deb ...')
        _, stdout, _ = client.exec_command(
            'pip3 install --break-system-packages pyinstaller 2>&1 | tail -1; '
            f'cd {REMOTE_DIR} && bash packaging/build_linux.sh',
            timeout=900,
        )
        for line in iter(stdout.readline, ''):
            print(line, end='')
    finally:
        client.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
