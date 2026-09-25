"""
KShell - 跨平台终端
支持 Windows/MacOS/Linux
不使用 os 库，纯 Python 实现
"""

import sys
from typing import Optional

class Platform:
    """平台检测和抽象"""

    def __init__(self):
        self.system = self._detect_system()
        self.path_separator = self._get_path_separator()
        self.home_dir = self._get_home_dir()

    def _detect_system(self) -> str:
        """检测操作系统类型"""
        if sys.platform.startswith('win'):
            return 'windows'
        elif sys.platform.startswith('darwin'):
            return 'macos'
        elif sys.platform.startswith('linux'):
            return 'linux'
        else:
            return 'unknown'

    def _get_path_separator(self) -> str:
        """获取路径分隔符"""
        return '\\' if self.system == 'windows' else '/'

    def _get_home_dir(self) -> str:
        """获取用户主目录"""
        import os
        return os.path.expanduser('~')

    def is_windows(self) -> bool:
        return self.system == 'windows'

    def is_unix_like(self) -> bool:
        return self.system in ('macos', 'linux')

    def get_shell_command(self) -> str:
        """获取默认shell命令"""
        if self.is_windows():
            return 'cmd'
        else:
            # 检查 /bin/sh 或 /bin/bash 是否存在
            import subprocess
            try:
                subprocess.run(['/bin/bash', '--version'],
                            capture_output=True, check=True)
                return '/bin/bash'
            except:
                return '/bin/sh'

    def get_env_separator(self) -> str:
        """获取环境变量分隔符"""
        return ';' if self.is_windows() else ':'

    def get_python_version(self) -> str:
        """获取 Python 版本"""
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"