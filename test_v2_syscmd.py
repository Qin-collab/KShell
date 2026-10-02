"""
KShell 2.0 系统命令特性测试
验证: PATH 命令直通、内置优先、command 绕过、path 命令、选项透传、管道
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from kplatform import Platform
from filesystem import FileSystem
from parser import CommandParser
from process import ProcessManager
from settings import SettingsManager
from theme import ThemeManager
from builtin import BuiltinCommands

PASS = 0
FAIL = 0


def check(name, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


print("=" * 60)
print("KShell 2.0 系统命令测试")
print("=" * 60)

platform = Platform()
fs = FileSystem(platform)
parser = CommandParser()
settings = SettingsManager()
theme = ThemeManager(enabled=False)
pm = ProcessManager(platform)
pm.set_filesystem(fs)
builtin = BuiltinCommands(fs, platform, parser, settings, theme)
builtin.set_process_manager(pm)

print("\n=== 1. 系统命令解析器 ===")
check("PATH 条目非空", len(pm.path_entries()) > 0, f"({len(pm.path_entries())} 个)")
check("系统命令索引非空", pm.resolver.count() > 0, f"({pm.resolver.count()} 条)")
check("能解析 python", pm.resolve('python') is not None)
check("解析不存在的命令返回 None", pm.resolve('no_such_cmd_xyz') is None)

print("\n=== 2. 系统命令直接执行 ===")
code, out = pm.run_system('python', ['--version'])
check("python --version 成功", code == 0 and 'Python' in out, f"code={code} out={out!r}")

print("\n=== 3. 选项透传（v2.0 修复点）===")
# 用 python 验证完整 argv 透传
code, out = pm.run_system('python', ['-c', 'import sys; print(sys.argv[1:])', '-x', '--long', 'val'])
check("选项 -x/--long/val 完整传入", "'-x'" in out and "'--long'" in out and "'val'" in out,
      f"code={code} out={out!r}")

print("\n=== 4. 内置命令优先 ===")
# 找出同时存在于内置和系统的命令（跨平台：Windows 用 find/calc，Linux 用 ls/find）
dual = [n for n in builtin.commands if pm.resolve(n) is not None]
check("存在同时是内置和系统的命令", len(dual) > 0, f"({dual[:8]})")
check("builtin_priority 默认为 True", settings.get('builtin_priority', True) is True)

print("\n=== 5. 遮蔽报告 ===")
shadowed = pm.resolver.shadowed(builtin.commands.keys())
check("存在被遮蔽的系统命令", len(shadowed) > 0, f"({len(shadowed)} 条)")
names = [n for n, _ in shadowed]
print(f"     前 10 条被遮蔽命令: {names[:10]}")

print("\n=== 6. 搜索系统命令 ===")
found = pm.resolver.search('py')
check("搜索 'py' 有结果", len(found) > 0, f"({len(found)} 条)")

print("\n=== 7. path 命令 ===")
code, out = builtin.execute('path', [], {})
check("path 列出目录", code == 0 and 'PATH 目录' in out, f"code={code}")
code, out = builtin.execute('path', ['py'], {'s': 'py'})
check("path -s py 搜索成功", code == 0 and 'py' in out, f"code={code}")
code, out = builtin.execute('path', [], {'b': True})
check("path -b 遮蔽报告", code == 0 and '接管' in out, f"code={code}")

print("\n=== 8. which 命令 ===")
code, out = builtin.execute('which', ['python'], {})
check("which python 返回路径", code == 0 and 'python' in out.lower(), f"out={out!r}")
code, out = builtin.execute('which', ['ls'], {})
check("which ls 显示内置", 'builtin' in out, f"out={out!r}")

print("\n=== 9. calc 命令（AST 求值）===")
code, out = builtin.execute('calc', ['1+2*3'], {})
check("calc 1+2*3 = 7", out == '7', f"out={out!r}")
code, out = builtin.execute('calc', ['(1+2)*3'], {})
check("calc (1+2)*3 = 9", out == '9', f"out={out!r}")
code, out = builtin.execute('calc', ['10/4'], {})
check("calc 10/4 = 2.5", out == '2.5', f"out={out!r}")
code, out = builtin.execute('calc', ['1/0'], {})
check("calc 1/0 报错", code == 1, f"code={code} out={out!r}")
code, out = builtin.execute('calc', ['__import__("os")'], {})
check("calc 拒绝危险表达式", code == 1, f"code={code} out={out!r}")

print("\n=== 10. 解析器 raw_split（选项保留）===")
cmd, raw = parser.raw_split('git --version')
check("raw_split 保留 --version", raw == ['--version'], f"raw={raw!r}")
cmd, raw = parser.raw_split('find . -name "*.py"')
check("raw_split 保留 -name", '-name' in raw, f"raw={raw!r}")

print("\n=== 11. 终端派发逻辑（内置优先 / 强制系统 / 系统优先模式）===")
from terminal import Terminal

terminal = Terminal()
t_builtin = terminal.builtin
t_pm = terminal.process_manager

# 11.1 内置优先：echo 走内置
code, out = terminal._execute_command('echo', ['hi'], {}, ['hi'])
check("内置优先: echo 走内置命令", out.strip() == 'hi', f"out={out!r}")

# 11.2 找到一个被遮蔽的系统命令，用 command 强制走系统版本
shadow_pairs = t_pm.resolver.shadowed(t_builtin.commands.keys())
shadow_names = [n for n, _ in shadow_pairs]
print(f"     可测试的遮蔽命令: {shadow_names[:12]}")

if 'find' in shadow_names:
    code_sys, out_sys = terminal._execute_command('command', [], {}, ['find', '/?'])
    code_bi, out_bi = terminal._execute_command('find', ['.'], {}, ['.'])
    check("command 强制系统版本(不是内置 find)",
          out_sys != out_bi and len(out_sys) > 0,
          f"sys={out_sys[:60]!r} builtin={out_bi[:40]!r}")

# 11.3 command 无参数时给出用法提示
code, out = terminal._execute_command('command', [], {}, [])
check("command 无参数提示用法", code == 1 and '用法' in out, f"out={out!r}")

# 11.4 系统优先模式：无系统同名命令时回退内置
old = terminal.settings.settings.get('builtin_priority', True)
terminal.settings.settings['builtin_priority'] = False
code, out = terminal._execute_command('echo', ['x'], {}, ['x'])
check("系统优先模式: 回退到内置 echo", out.strip() == 'x', f"out={out!r}")
terminal.settings.settings['builtin_priority'] = old

# 11.5 未找到的命令返回 127
code, out = terminal._execute_command('no_such_cmd_abc', [], {}, [])
check("未找到命令返回 127", code == 127, f"code={code} out={out!r}")

print("\n" + "=" * 60)
print(f"测试完成: {PASS} 通过, {FAIL} 失败")
print("=" * 60)

sys.exit(1 if FAIL else 0)
