"""
sysinfo 插件 —— 系统信息速查

演示内容：
  · 通过 ctx.platform / ctx.fs 访问 KShell 的平台抽象与文件系统
  · 读取插件配置（ctx.get）与全局设置（ctx.settings）
  · --json 选项：把结构化数据交给脚本处理
  · 优雅降级：拿不到的信息直接跳过，不让插件整体失败
"""

import json
import shutil
import socket
import sys
import time


def _size(num):
    """字节数转可读大小"""
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if num < 1024:
            return f'{num:.1f} {unit}'
        num /= 1024
    return f'{num:.1f} PB'


def _collect(ctx):
    """收集系统信息，返回有序字典（失败的项自动跳过）"""
    info = {}

    def put(key, factory):
        try:
            value = factory()
            if value is not None:
                info[key] = value
        except Exception:
            pass

    # ---- 平台 ----
    put('系统', lambda: ctx.platform.system)
    put('平台标识', lambda: sys.platform)
    put('架构', lambda: '64 位' if sys.maxsize > 2 ** 32 else '32 位')

    # ---- Python ----
    put('Python', lambda: '{}.{}.{}'.format(*sys.version_info[:3]))
    put('解释器', lambda: sys.implementation.name)
    put('Python 路径', lambda: sys.executable)

    # ---- 主机 ----
    put('主机名', lambda: socket.gethostname())
    put('当前用户', lambda: __import__('getpass').getuser())

    # ---- CPU ----
    put('CPU 核心', lambda: __import__('multiprocessing').cpu_count())

    # ---- 工作目录 ----
    put('当前目录', lambda: ctx.fs.getcwd())

    # ---- 磁盘（可配置关闭）----
    if ctx.get('show_disk', True):
        def disk_total():
            return _size(shutil.disk_usage(ctx.fs.getcwd()).total)

        def disk_free():
            return _size(shutil.disk_usage(ctx.fs.getcwd()).free)

        def disk_used():
            usage = shutil.disk_usage(ctx.fs.getcwd())
            return f'{usage.used * 100 // usage.total}%'

        put('磁盘总量', disk_total)
        put('磁盘可用', disk_free)
        put('磁盘使用率', disk_used)

    # ---- KShell 自身 ----
    from version import VERSION
    info['KShell 版本'] = VERSION

    put('主题', lambda: ctx.settings.get('theme', 'default'))
    put('提示符样式', lambda: ctx.settings.get('prompt_style', 'default'))

    def plugin_stat():
        stats = ctx._manager.stats()
        return f'{stats["loaded"]}/{stats["total"]} 个已加载'

    put('插件', plugin_stat)

    return info


def cmd_sysinfo(args, options, ctx):
    """
    sysinfo [-a] [--json]

    -a / --all  追加内核与本地时间信息
    --json      输出 JSON，便于脚本处理
    """
    info = _collect(ctx)
    show_all = 'a' in options or 'all' in options
    as_json = 'json' in options

    if show_all:
        try:
            info['本地时间'] = time.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass

    # ---- JSON 输出 ----
    if as_json:
        return 0, json.dumps(info, ensure_ascii=False, indent=2)

    # ---- 表格输出 ----
    if not info:
        return 1, '未能获取到任何系统信息'

    width = max(len(k) for k in info)
    lines = [ctx.colorize('系统信息', 'title'), '']
    for key, value in info.items():
        lines.append(f'  {key:<{width}} : {value}')

    if show_all:
        lines.append('')
        lines.append(f'  共 {len(info)} 项')

    return 0, '\n'.join(lines)


def on_load(ctx):
    ctx.log('sysinfo 插件已加载，执行 sysinfo 查看系统信息')
