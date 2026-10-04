"""
KShell 2.1 插件系统测试

覆盖：发现与加载、manifest 校验、命令执行、配置读写、启用/禁用、
      热重载、脚手架生成、异常隔离、别名、自动发现、版本要求
"""

import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from kplatform import Platform
from filesystem import FileSystem
from parser import CommandParser
from process import ProcessManager
from settings import SettingsManager
from theme import ThemeManager
from builtin import BuiltinCommands
from pluginmgr import PluginManager
from version import VERSION, check_requirement, version_tuple

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


def make_env(plugin_dirs=None):
    """构造一套干净的环境"""
    platform = Platform()
    fs = FileSystem(platform)
    parser = CommandParser()
    settings = SettingsManager()
    theme = ThemeManager(enabled=False)
    pm = ProcessManager(platform)
    pm.set_filesystem(fs)
    builtin = BuiltinCommands(fs, platform, parser, settings, theme)
    builtin.set_process_manager(pm)
    mgr = PluginManager(platform, fs, parser, settings, theme, builtin)
    builtin.set_plugin_manager(mgr)
    if plugin_dirs:
        mgr.dirs = [pathlib.Path(d) for d in plugin_dirs]
    return platform, fs, parser, settings, theme, builtin, mgr


def write_plugin(base, name, manifest, code):
    """在指定目录写一个插件"""
    d = pathlib.Path(base) / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'plugin.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                   encoding='utf-8')
    (d / 'plugin.py').write_text(code, encoding='utf-8')
    return d


print("=" * 62)
print("KShell 2.1 插件系统测试")
print("=" * 62)

# ---------------------------------------------------------------- 版本工具
print("\n=== 1. 版本比较工具 ===")
check("2.1.0 > 2.0.0", version_tuple('2.1.0') > version_tuple('2.0.0'))
check(">=2.1.0 满足当前", check_requirement('>=2.1.0', '2.1.0')[0])
check(">=2.2.0 不满足", not check_requirement('>=2.2.0', '2.1.0')[0])
check("空要求视为满足", check_requirement('', '2.1.0')[0])
check("无操作符视为最低版本", check_requirement('2.1.0', '2.1.0')[0])
check(">2.0 满足", check_requirement('>2.0', '2.1.0')[0])
check("!=2.0.0 满足", check_requirement('!=2.0.0', '2.1.0')[0])

# ---------------------------------------------------------------- 内置插件
print("\n=== 2. 内置示例插件加载 ===")
_real_plugins = pathlib.Path(__file__).parent / 'plugins'
platform, fs, parser, settings, theme, builtin, mgr = make_env([_real_plugins])
summary = mgr.load_all()

# 注意：不要断言「插件总数 == 3」——用户会把自己的插件放进 plugins/，
# 那不应该让 KShell 的测试失败。这里改为校验官方插件是否齐全。
OFFICIAL = {
    'hello': ['hello', 'greet'],
    'pwgen': ['pwgen', 'uuid', 'passwd-strength'],
    'sysinfo': ['sysinfo', 'sys'],
}
for pname, commands in OFFICIAL.items():
    plugin = mgr.get(pname)
    check(f"官方插件 {pname} 已加载",
          plugin is not None and plugin.loaded,
          f"err={plugin.load_error if plugin else '未找到'}")
    for cmd in commands:
        check(f"  {pname} 的命令 {cmd} 已注册", cmd in builtin.commands)

check("无加载失败的插件", summary['failed'] == 0, f"errors={summary['errors']}")
check("注册命令数不少于官方插件的命令总数",
      summary['commands'] >= sum(len(v) for v in OFFICIAL.values()),
      f"实际 {summary['commands']}")

# ---------------------------------------------------------------- 命令执行
print("\n=== 3. 插件命令执行 ===")
code, out = builtin.execute('hello', ['KShell'], {})
check("hello KShell 返回 0", code == 0)
check("hello 使用默认配置", 'Hello, KShell!' in out, f"out={out!r}")

code, out = builtin.execute('hello', [], {})
check("hello 无参数用默认名", 'Hello, World!' in out, f"out={out!r}")

code, out = builtin.execute('hello', ['Test'], {'v': True})
check("hello -v 显示插件信息", '插件名称' in out and 'hello' in out, f"out={out[:60]!r}")

code, out = builtin.execute('greet', ['X'], {})
check("别名命令可用", code == 0 and 'Hello, X!' in out, f"out={out!r}")

code, out = builtin.execute('pwgen', ['1', '16'], {})
check("pwgen 生成长度 16", code == 0 and len(out.strip()) == 16, f"len={len(out.strip())}")

code, out = builtin.execute('pwgen', ['3', '12'], {})
check("pwgen 生成 3 个", code == 0 and len(out.strip().splitlines()) == 5, f"out={out!r}")

code, out = builtin.execute('pwgen', ['1', '4'], {})
check("pwgen 拒绝过短长度", code == 1 and '长度' in out, f"out={out!r}")

code, out = builtin.execute('uuid', [], {})
check("uuid 格式正确", code == 0 and len(out.strip()) == 36 and out.count('-') == 4)

code, out = builtin.execute('passwd-strength', ['abc'], {})
check("passwd-strength 识别弱密码", '很弱' in out or '较弱' in out, f"out={out!r}")

code, out = builtin.execute('passwd-strength', ['A1b2C3d4!@#$'], {})
check("passwd-strength 识别强密码", '强' in out, f"out={out!r}")

code, out = builtin.execute('sysinfo', [], {})
check("sysinfo 输出系统信息", code == 0 and 'Python' in out, f"out={out[:60]!r}")

code, out = builtin.execute('sysinfo', [], {'json': True})
valid_json = False
try:
    json.loads(out)
    valid_json = True
except Exception:
    pass
check("sysinfo --json 输出合法 JSON", valid_json, f"out={out[:60]!r}")

# ---------------------------------------------------------------- plugin 命令
print("\n=== 4. plugin 管理命令 ===")
code, out = builtin.execute('plugin', ['list'], {})
check("plugin list 返回 0", code == 0)
check("plugin list 显示插件名", 'hello' in out and 'pwgen' in out and 'sysinfo' in out)

code, out = builtin.execute('plugin', ['info', 'hello'], {})
check("plugin info 显示版本", '1.0.0' in out)
check("plugin info 显示配置项", 'greeting' in out)

code, out = builtin.execute('plugin', ['info', '不存在的插件'], {})
check("plugin info 处理不存在的插件", code == 1 and '找不到' in out, f"out={out!r}")

code, out = builtin.execute('plugin', [], {})
check("plugin 无参数等价于 list", code == 0 and '插件' in out)

code, out = builtin.execute('plugin', ['未知子命令'], {})
check("plugin 未知子命令报错", code == 1 and '未知' in out, f"out={out!r}")

code, out = builtin.execute('plugin', ['help'], {})
check("plugin help 输出用法", code == 0 and 'plugin new' in out)

code, out = builtin.execute('plugin', ['dirs'], {})
check("plugin dirs 列出目录", code == 0 and '插件搜索目录' in out)

# ---------------------------------------------------------------- 配置读写
print("\n=== 5. 插件配置读写 ===")
saved_cfg = dict(settings.get('plugins.config', {}) or {})
mgr.set_plugin_config('hello', 'greeting', '你好')
code, out = builtin.execute('hello', ['世界'], {})
check("修改配置后命令生效", '你好, 世界!' in out, f"out={out!r}")

code, out = builtin.execute('plugin', ['config', 'hello'], {})
check("plugin config 显示已修改", '你好' in out and '已修改' in out, f"out={out!r}")

code, out = builtin.execute('plugin', ['config', 'hello', 'punctuation=~'], {})
check("plugin config 设置成功", code == 0 and '已更新' in out, f"out={out!r}")

code, out = builtin.execute('hello', ['A'], {})
check("新配置立即生效", '你好, A~' in out, f"out={out!r}")

code, out = builtin.execute('plugin', ['config', 'hello', 'uppercase_name=true'], {})
code, out = builtin.execute('hello', ['abc'], {})
check("布尔配置生效", '你好, ABC~' in out, f"out={out!r}")

code, out = builtin.execute('plugin', ['config', 'pwgen', 'default_length=8'], {})
code, out = builtin.execute('pwgen', [], {})
check("pwgen 读取修改后的默认长度", len(out.strip()) == 8, f"len={len(out.strip())}")

# 恢复
settings.set('plugins.config', saved_cfg)
mgr.reload('hello')
mgr.reload('pwgen')

# ---------------------------------------------------------------- 启用禁用
print("\n=== 6. 启用 / 禁用 ===")
saved_enabled = dict(settings.get('plugins.enabled', {}) or {})
mgr.set_enabled('hello', False)
check("禁用后 is_enabled 为 False", mgr.is_enabled('hello') is False)

result = mgr.reload('hello')
check("禁用插件 reload 提示禁用状态", result['ok'] and '禁用' in result['message'],
      f"msg={result['message']!r}")
check("禁用后命令不再注册", 'hello' not in builtin.commands)

mgr.set_enabled('hello', True)
result = mgr.reload('hello')
check("重新启用后加载成功", result['ok'] and '已重新加载' in result['message'])
check("启用后命令重新注册", 'hello' in builtin.commands)
settings.set('plugins.enabled', saved_enabled)

# ---------------------------------------------------------------- 热重载
print("\n=== 7. 热重载源码变更 ===")
tmp = tempfile.mkdtemp(prefix='ksh_plugin_test_')
try:
    write_plugin(tmp, 'hotreload', {
        'name': 'hotreload', 'version': '1.0.0',
        'commands': ['hotreload'],
        'settings': {},
    }, 'def cmd_hotreload(args, options, ctx):\n    return 0, "v1"\n')

    mgr.dirs = [pathlib.Path(tmp)]
    mgr.load_all()
    code, out = builtin.execute('hotreload', [], {})
    check("首次加载返回 v1", out.strip() == 'v1', f"out={out!r}")

    # 修改源码
    entry = pathlib.Path(tmp) / 'hotreload' / 'plugin.py'
    entry.write_text('def cmd_hotreload(args, options, ctx):\n    return 0, "v2"\n',
                     encoding='utf-8')
    mgr.reload('hotreload')
    code, out = builtin.execute('hotreload', [], {})
    check("热重载后返回 v2", out.strip() == 'v2', f"out={out!r}")

    # ------------------------------------------------------------ 异常隔离
    print("\n=== 8. 异常隔离 ===")
    write_plugin(tmp, 'boom', {
        'name': 'boom', 'version': '1.0.0', 'commands': ['boom'],
    }, 'def cmd_boom(args, options, ctx):\n    raise ValueError("故意炸掉")\n')
    mgr.load_all()
    code, out = builtin.execute('boom', [], {})
    check("插件异常返回错误码", code == 1)
    check("异常信息包含插件名", 'boom' in out, f"out={out!r}")
    check("异常被隔离，其他插件仍可用", builtin.execute('hotreload', [], {})[0] == 0)

    # 导入期异常
    write_plugin(tmp, 'badimport', {
        'name': 'badimport', 'version': '1.0.0', 'commands': ['badimport'],
    }, 'import 不存在的模块\n')
    mgr.load_all()
    check("导入异常不影响其他插件", mgr.get('badimport').load_error != '')
    check("其他插件仍加载", mgr.get('hotreload') is not None and mgr.get('hotreload').loaded)

    # ------------------------------------------------------------ manifest 校验
    print("\n=== 9. manifest 校验 ===")
    cases = [
        ('badjson', '{"name": "badjson",}', 'JSON'),
        ('noname', json.dumps({'version': '1.0'}), None),
        ('badname', json.dumps({'name': 'has space', 'commands': ['x']}), '非法'),
        ('mismatch', json.dumps({'name': 'other', 'commands': ['x']}), '不一致'),
        ('baddcommands', json.dumps({'name': 'baddcommands', 'commands': 123}), 'commands'),
        ('missingfunc', json.dumps({'name': 'missingfunc', 'commands': ['nope']}), '不存在'),
        ('badversion', json.dumps({'name': 'badversion', 'kshell': '>=99.0.0',
                                   'commands': ['badversion']}), '需要'),
        ('badsettings', json.dumps({'name': 'badsettings', 'settings': [],
                                    'commands': ['badsettings']}), 'settings'),
    ]
    for name, manifest_text, expect in cases:
        d = pathlib.Path(tmp) / name
        d.mkdir(parents=True, exist_ok=True)
        (d / 'plugin.json').write_text(manifest_text, encoding='utf-8')
        (d / 'plugin.py').write_text('def cmd_x(args, options, ctx):\n    return 0, "x"\n',
                                     encoding='utf-8')
        mgr.load_all()
        p = mgr.get(name)
        loaded_ok = p is not None and not p.load_error
        if expect is None:
            check(f"{name} 容错加载（无 name 时用目录名）", loaded_ok, f"err={p.load_error if p else 'None'}")
        else:
            check(f"{name} 被正确拒绝", p is not None and expect in p.load_error,
                  f"err={p.load_error if p else 'None'}")

    # ------------------------------------------------------------ 自动发现
    print("\n=== 10. 未声明 commands 时自动发现 ===")
    write_plugin(tmp, 'auto', {'name': 'auto', 'version': '1.0.0'}, '''
def cmd_auto_one(args, options, ctx):
    return 0, "one"

def cmd_auto_two(args, options, ctx):
    return 0, "two"

def helper_not_a_command():
    return "nope"
''')
    mgr.load_all()
    p = mgr.get('auto')
    names = sorted(s.name for s in p.commands)
    check("自动发现 2 条命令", names == ['auto-one', 'auto-two'], f"实际 {names}")
    check("自动命令可执行", builtin.execute('auto-one', [], {})[1].strip() == 'one')
    check("非 cmd_ 函数未被注册", 'helper-not-a-command' not in builtin.commands)

    # ------------------------------------------------------------ 返回值归一化
    print("\n=== 11. 返回值归一化 ===")
    write_plugin(tmp, 'returns', {'name': 'returns', 'version': '1.0.0',
                                  'commands': ['r-str', 'r-none', 'r-code', 'r-int']}, '''
def cmd_r_str(args, options, ctx):
    return "纯字符串"

def cmd_r_none(args, options, ctx):
    return None

def cmd_r_code(args, options, ctx):
    return 3, "带错误码"

def cmd_r_int(args, options, ctx):
    return 0
''')
    mgr.load_all()
    check("返回字符串 → (0, str)", builtin.execute('r-str', [], {}) == (0, '纯字符串'))
    check("返回 None → (0, '')", builtin.execute('r-none', [], {}) == (0, ''))
    check("返回 (3, str) 保留错误码", builtin.execute('r-code', [], {}) == (3, '带错误码'))
    check("返回 int → (int, '')", builtin.execute('r-int', [], {}) == (0, ''))

    # ------------------------------------------------------------ 脚手架
    print("\n=== 12. plugin new 脚手架 ===")
    scaffold_root = pathlib.Path(tmp) / 'scaffold'
    scaffold_root.mkdir(exist_ok=True)
    mgr.dirs = [scaffold_root]
    code, out = builtin.execute('plugin', ['new', 'myplugin'], {})
    check("脚手架生成成功", code == 0 and '已生成' in out, f"out={out!r}")
    new_dir = scaffold_root / 'myplugin'
    check("plugin.json 已创建", (new_dir / 'plugin.json').is_file())
    check("plugin.py 已创建", (new_dir / 'plugin.py').is_file())

    manifest = json.loads((new_dir / 'plugin.json').read_text(encoding='utf-8'))
    check("生成的 manifest 名称正确", manifest['name'] == 'myplugin')
    check("生成的 manifest 含命令声明", 'myplugin' in manifest.get('commands', {}))
    check("生成的 manifest 含版本要求", manifest.get('kshell', '').startswith('>='))

    # 生成的插件能被加载并执行
    mgr.load_all()
    code, out = builtin.execute('myplugin', ['Test'], {})
    check("生成的插件可加载执行", code == 0 and 'Test' in out, f"out={out!r}")

    code, out = builtin.execute('plugin', ['new', 'myplugin'], {})
    check("重复创建被拒绝", code == 1 and '已存在' in out, f"out={out!r}")

    code, out = builtin.execute('plugin', ['new', '带空格的 名字'], {})
    check("非法插件名被拒绝", code == 1 and '非法' in out, f"out={out!r}")

    # ------------------------------------------------------------ 脚手架落点
    print("\n=== 12b. 脚手架必须避开打包临时目录 (_MEIPASS) ===")
    import sys as _sys

    sim_root = pathlib.Path(tmp) / 'fake_meipass'
    (sim_root / 'plugins').mkdir(parents=True, exist_ok=True)
    persistent = pathlib.Path(tmp) / 'persistent_plugins'
    persistent.mkdir(exist_ok=True)

    old_meipass = getattr(_sys, '_MEIPASS', None)
    old_dirs = mgr.dirs
    try:
        _sys._MEIPASS = str(sim_root)
        # 模拟打包环境：搜索目录第一个是临时解包目录，其后是可持久化目录
        mgr.dirs = [sim_root / 'plugins', persistent]
        chosen = mgr.scaffold_dir()
        check("脚手架跳过 _MEIPASS 子目录",
              sim_root not in chosen.parents and chosen != sim_root,
              f"选中 {chosen}")
        check("脚手架选中可持久化目录",
              str(chosen) == str(persistent), f"选中 {chosen}")

        code, out = builtin.execute('plugin', ['new', 'locprobe'], {})
        check("plugin new 写入持久目录", (persistent / 'locprobe' / 'plugin.json').is_file(),
              f"out={out!r}")
        check("_MEIPASS 下未产生插件",
              not (sim_root / 'plugins' / 'locprobe').exists())
    finally:
        mgr.dirs = old_dirs
        if old_meipass is None:
            try:
                del _sys._MEIPASS
            except AttributeError:
                pass
        else:
            _sys._MEIPASS = old_meipass

    # ------------------------------------------------------------ 自定义目录
    print("\n=== 13. 自定义插件目录配置 ===")
    check("配置可写入 plugins.dirs", settings.set('plugins.dirs', [tmp]) is None)
    mgr.refresh_dirs()
    check("refresh_dirs 包含自定义目录", any('ksh_plugin_test_' in str(d) for d in mgr.dirs),
          f"dirs={[str(d) for d in mgr.dirs]}")
    settings.set('plugins.dirs', [])

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- 统计
print("\n=== 14. 统计信息 ===")
mgr.dirs = [_real_plugins]
mgr.load_all()
stats = mgr.stats()
check("stats 含 total/loaded/commands", all(k in stats for k in ('total', 'loaded', 'commands')))
check("官方插件都在统计中", all(mgr.get(n) and mgr.get(n).loaded for n in OFFICIAL),
      f"stats={stats}")
check("统计数值自洽", stats['loaded'] + stats['disabled'] + stats['failed'] == stats['total'],
      f"stats={stats}")

print("\n" + "=" * 62)
print(f"测试完成: {PASS} 通过, {FAIL} 失败")
print("=" * 62)

sys.exit(1 if FAIL else 0)
