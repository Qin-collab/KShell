# -*- mode: python ; coding: utf-8 -*-
"""
KShell PyInstaller 打包配置
生成: dist/kshell.exe (Windows) 或 dist/kshell (Linux/macOS)
"""

a = Analysis(
    ['kshell.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # 显式声明项目模块，确保全部打包
    hiddenimports=[
        'terminal', 'kplatform', 'filesystem', 'parser',
        'process', 'builtin', 'settings', 'banner', 'theme',
        'commands_extra',
    ],
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
