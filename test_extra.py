# -*- coding: utf-8 -*-
"""KShell 扩展命令验证脚本"""
import sys
sys.path.insert(0, '.')
from terminal import Terminal

t = Terminal()

# 准备测试文件
t.filesystem.write_file('test_cmds.txt', 'apple\nbanana\napple\ncherry\nbanana\n')

def run(cmd_str):
    command, args, options = t.parser.parse(cmd_str)
    clean_args, of, inf = t.parser.parse_redirect(args)
    code, output = t._execute_command(command, clean_args, options)
    return code, output

print('=== 文件内容命令 ===')
for cmd in ['head -n 2 test_cmds.txt', 'tail -n 2 test_cmds.txt',
            'grep apple test_cmds.txt', 'grep -n banana test_cmds.txt',
            'wc test_cmds.txt', 'sort test_cmds.txt',
            'uniq test_cmds.txt', 'nl test_cmds.txt']:
    code, output = run(cmd)
    print(f'[{cmd}] -> code={code}')
    for line in (output or '').split('\n'):
        print('   ', repr(line))
    print()

print('=== 查找和信息命令 ===')
for cmd in ['find . -name *.py', 'find . -type d',
            'stat test_cmds.txt', 'du -h .', 'df -h',
            'which ls', 'which python']:
    code, output = run(cmd)
    lines = (output or '').split('\n')
    print(f'[{cmd}] -> code={code} ({len(lines)} 行)')
    if len(lines) <= 6:
        for line in lines:
            print('   ', repr(line))
    else:
        print('   前3行:', lines[:3])
        print('   最后2行:', lines[-2:])
    print()

print('=== 系统命令 ===')
for cmd in ['sleep 1', 'uname -a', 'id', 'uptime', 'true', 'false',
            'seq 1 5', 'seq 1 10 2', 'base64 hello',
            'md5sum test_cmds.txt', 'sha256sum test_cmds.txt',
            'yes hello', 'man grep', 'history -c']:
    code, output = run(cmd)
    print(f'[{cmd}] -> code={code}')
    for line in (output or '').split('\n')[:5]:
        print('   ', repr(line))
    print()

# 清理
t.filesystem.remove_file('test_cmds.txt')
print('=== 全部测试完成 ===')
