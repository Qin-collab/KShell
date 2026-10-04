# -*- mode: python ; coding: utf-8 -*-
"""
KShell PyInstaller 打包配置
生成: dist/kshell.exe (Windows) 或 dist/kshell (Linux/macOS)
"""

import os
import sys

sys.path.insert(0, os.path.abspath('.'))

# 插件是运行时动态加载的，PyInstaller 静态分析看不到插件里的 import，
# 因此必须显式把插件常用的标准库模块加入 hiddenimports，
# 否则打包后插件会报 ModuleNotFoundError。
try:
    from pluginmgr import PLUGIN_STDLIB_HINTS as PLUGIN_MODULES
except Exception:
    PLUGIN_MODULES = ['secrets', 'uuid', 'string', 'hashlib', 'socket']

PROJECT_MODULES = [
    'terminal', 'kplatform', 'filesystem', 'parser',
    'process', 'builtin', 'settings', 'banner', 'theme',
    'commands_extra', 'syscmd',
    # v2.1 插件系统
    'pluginmgr', 'commands_plugin', 'version',
]

a = Analysis(
    ['kshell.py'],
    pathex=[],
    binaries=[],
    # 插件示例与开发文档作为数据文件打包：
    #   运行时由 PluginManager 从 sys._MEIPASS/plugins 加载
    datas=[
        ('plugins', 'plugins'),
        ('PLUGIN_DEV.md', '.'),
    ],
    hiddenimports=PROJECT_MODULES + PLUGIN_MODULES,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='kshell',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # 终端程序需要控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
