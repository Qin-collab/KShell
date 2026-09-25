"""
主题模块 - 终端颜色主题
支持 ANSI 转义序列，跨平台（Windows 自动启用 VT 处理）
"""

import sys

# ------------------------------------------------------------------
# ANSI 转义码常量
# ------------------------------------------------------------------
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
ITALIC = '\033[3m'
UNDERLINE = '\033[4m'
BLINK = '\033[5m'
REVERSE = '\033[7m'

FG = {
    'black': '\033[30m', 'red': '\033[31m', 'green': '\033[32m',
    'yellow': '\033[33m', 'blue': '\033[34m', 'magenta': '\033[35m',
    'cyan': '\033[36m', 'white': '\033[37m',
    'bright_black': '\033[90m', 'bright_red': '\033[91m',
    'bright_green': '\033[92m', 'bright_yellow': '\033[93m',
    'bright_blue': '\033[94m', 'bright_magenta': '\033[95m',
    'bright_cyan': '\033[96m', 'bright_white': '\033[97m',
}

BG = {
    'black': '\033[40m', 'red': '\033[41m', 'green': '\033[42m',
    'yellow': '\033[43m', 'blue': '\033[44m', 'magenta': '\033[45m',
    'cyan': '\033[46m', 'white': '\033[47m',
}

def _c(*parts):
    """拼接多个 ANSI 码"""
    return ''.join(parts)


# ------------------------------------------------------------------
# 预设主题
# ------------------------------------------------------------------
THEMES = {
    'default': {
        'prompt_user': _c(FG['green']),
        'prompt_dir':  _c(BOLD, FG['blue']),
        'prompt_sym':  _c(BOLD, FG['green']),
        'banner_logo': _c(BOLD, FG['bright_cyan']),
        'banner_title':_c(BOLD, FG['cyan']),
        'banner_info': _c(FG['white']),
        'dir':   _c(BOLD, FG['blue']),
        'file':  _c(FG['white']),
        'link':  _c(FG['cyan']),
        'error': _c(BOLD, FG['red']),
        'warning': _c(BOLD, FG['yellow']),
        'info':  _c(FG['cyan']),
        'success': _c(BOLD, FG['green']),
        'command': _c(BOLD, FG['green']),
        'title': _c(BOLD, FG['magenta']),
    },
    'dark': {
        'prompt_user': _c(FG['bright_green']),
        'prompt_dir':  _c(FG['bright_blue']),
        'prompt_sym':  _c(BOLD, FG['bright_green']),
        'banner_logo': _c(BOLD, FG['bright_blue']),
        'banner_title':_c(BOLD, FG['bright_cyan']),
        'banner_info': _c(FG['bright_white']),
        'dir':   _c(BOLD, FG['bright_blue']),
        'file':  _c(FG['bright_white']),
        'link':  _c(FG['bright_cyan']),
        'error': _c(BOLD, FG['bright_red']),
        'warning': _c(BOLD, FG['bright_yellow']),
        'info':  _c(FG['bright_cyan']),
        'success': _c(BOLD, FG['bright_green']),
        'command': _c(BOLD, FG['bright_green']),
        'title': _c(BOLD, FG['bright_magenta']),
    },
    'light': {
        'prompt_user': _c(BOLD, FG['magenta']),
        'prompt_dir':  _c(BOLD, FG['blue']),
        'prompt_sym':  _c(BOLD, FG['black']),
        'banner_logo': _c(BOLD, FG['blue']),
        'banner_title':_c(BOLD, FG['magenta']),
        'banner_info': _c(FG['black']),
        'dir':   _c(BOLD, FG['blue']),
        'file':  _c(FG['black']),
        'link':  _c(FG['magenta']),
        'error': _c(BOLD, FG['red']),
        'warning': _c(BOLD, FG['yellow']),
        'info':  _c(FG['blue']),
        'success': _c(BOLD, FG['green']),
        'command': _c(BOLD, FG['magenta']),
        'title': _c(BOLD, FG['black']),
    },
    'ocean': {
        'prompt_user': _c(FG['cyan']),
        'prompt_dir':  _c(BOLD, FG['bright_blue']),
        'prompt_sym':  _c(BOLD, FG['bright_cyan']),
        'banner_logo': _c(BOLD, FG['bright_blue']),
        'banner_title':_c(BOLD, FG['cyan']),
        'banner_info': _c(FG['bright_cyan']),
        'dir':   _c(BOLD, FG['bright_blue']),
        'file':  _c(FG['cyan']),
        'link':  _c(FG['bright_cyan']),
        'error': _c(BOLD, FG['bright_red']),
        'warning': _c(BOLD, FG['bright_yellow']),
        'info':  _c(FG['bright_cyan']),
        'success': _c(BOLD, FG['bright_green']),
        'command': _c(BOLD, FG['cyan']),
        'title': _c(BOLD, FG['bright_blue']),
    },
    'monokai': {
        'prompt_user': _c(FG['yellow']),
        'prompt_dir':  _c(BOLD, FG['bright_green']),
        'prompt_sym':  _c(BOLD, FG['bright_magenta']),
        'banner_logo': _c(BOLD, FG['bright_magenta']),
        'banner_title':_c(BOLD, FG['bright_yellow']),
        'banner_info': _c(FG['bright_white']),
        'dir':   _c(BOLD, FG['bright_blue']),
        'file':  _c(FG['bright_white']),
        'link':  _c(FG['bright_cyan']),
        'error': _c(BOLD, FG['bright_red']),
        'warning': _c(BOLD, FG['bright_yellow']),
        'info':  _c(FG['bright_cyan']),
        'success': _c(BOLD, FG['bright_green']),
        'command': _c(BOLD, FG['yellow']),
        'title': _c(BOLD, FG['magenta']),
    },
    'solarized': {
        'prompt_user': _c(FG['green']),
        'prompt_dir':  _c(BOLD, FG['blue']),
        'prompt_sym':  _c(BOLD, FG['yellow']),
        'banner_logo': _c(BOLD, FG['cyan']),
        'banner_title':_c(BOLD, FG['blue']),
        'banner_info': _c(FG['cyan']),
        'dir':   _c(BOLD, FG['blue']),
        'file':  _c(FG['white']),
        'link':  _c(FG['cyan']),
        'error': _c(BOLD, FG['red']),
        'warning': _c(BOLD, FG['yellow']),
        'info':  _c(FG['cyan']),
        'success': _c(BOLD, FG['green']),
        'command': _c(BOLD, FG['green']),
        'title': _c(BOLD, FG['yellow']),
    },
}


def enable_ansi_windows():
    """在 Windows 上启用 ANSI 转义序列支持 (VT100)"""
    if not sys.platform.startswith('win'):
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def supports_color():
    """检查终端是否支持颜色输出"""
    # 管道/重定向时不输出颜色
    try:
        if not sys.stdout.isatty():
            return False
    except Exception:
        return False
    # NO_COLOR 约定
    try:
        import os
        if os.environ.get('NO_COLOR'):
            return False
    except Exception:
        pass
    return True


def strip_ansi(text: str) -> str:
    """去除文本中的 ANSI 转义码（重定向写入文件时使用）"""
    import re
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


class ThemeManager:
    """主题管理器"""

    def __init__(self, name: str = 'default', enabled: bool = True):
        self.enabled = enabled
        self.colors = THEMES.get('default', {})
        self.name = 'default'
        self.set_theme(name)

    def set_theme(self, name: str) -> bool:
        """切换主题"""
        if name in THEMES:
            self.name = name
            self.colors = THEMES[name]
            return True
        return False

    def colorize(self, text: str, key: str) -> str:
        """为文本着色（颜色键如 'dir', 'error' 等）"""
        if not self.enabled:
            return text
        code = self.colors.get(key)
        if not code:
            return text
        return f"{code}{text}{RESET}"

    def raw(self, key: str) -> str:
        """获取原始 ANSI 码"""
        return self.colors.get(key, '')

    def list_themes(self) -> list:
        """列出所有主题名"""
        return list(THEMES.keys())

    def preview(self) -> str:
        """生成所有主题的预览色块"""
        sample_keys = ['dir', 'file', 'link', 'error', 'warning', 'info', 'success', 'command']
        lines = []
        for name, colors in THEMES.items():
            current = ' <= current' if name == self.name else ''
            swatches = []
            for key in sample_keys:
                code = colors.get(key, '')
                swatches.append(f"{code}██{RESET}")
            lines.append(f"  {name:<12} {' '.join(swatches)}{current}")
        return '\n'.join(lines)
