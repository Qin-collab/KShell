"""
进程管理模块
使用 subprocess 执行外部命令
"""

import subprocess
import sys
from typing import Optional, Tuple, List
from kplatform import Platform

class ProcessManager:
    """进程管理器"""

    def __init__(self, platform: Platform):
        self.platform = platform
        self.env = self._get_env_vars()

    def _get_env_vars(self) -> dict:
        """获取环境变量"""
        import os
        return dict(os.environ)

    def execute(self,
                command: str,
                args: List[str],
                capture_output: bool = False,
                shell: bool = False) -> Tuple[int, str, str]:
        """
        执行命令
        返回: (返回码, 标准输出, 标准错误)
        """
        try:
            # 构建完整命令
            if shell:
                # Windows 下可能需要 cmd /c
                if self.platform.is_windows():
                    full_cmd = ['cmd', '/c', command] + args
                else:
                    full_cmd = [command] + args
            else:
                full_cmd = [command] + args

            # 执行命令
            result = subprocess.run(
                full_cmd,
                capture_output=capture_output,
                text=True,
                env=self.env,
                shell=shell,
                cwd=self._get_cwd()
            )

            stdout = result.stdout if capture_output else ''
            stderr = result.stderr if capture_output else ''

            return result.returncode, stdout, stderr

        except FileNotFoundError:
            return 1, '', f"Command not found: {command}"
        except Exception as e:
            return 1, '', str(e)

    def execute_interactive(self, command: str, args: List[str]) -> int:
        """交互式执行命令"""
        try:
            full_cmd = [command] + args
            result = subprocess.run(
                full_cmd,
                env=self.env,
                cwd=self._get_cwd()
            )
            return result.returncode
        except FileNotFoundError:
            print(f"Command not found: {command}")
            return 1
        except Exception as e:
            print(f"Error: {e}")
            return 1

    def _get_cwd(self) -> str:
        """获取当前工作目录"""
        # 从全局状态获取，这里简化处理
        import pathlib
        return str(pathlib.Path.cwd())

    def set_env(self, key: str, value: str):
        """设置环境变量"""
        self.env[key] = value

    def get_env(self, key: str) -> Optional[str]:
        """获取环境变量"""
        return self.env.get(key)

    def unset_env(self, key: str):
        """删除环境变量"""
        if key in self.env:
            del self.env[key]

    def list_env(self) -> dict:
        """列出所有环境变量"""
        return self.env.copy()

    def which(self, command: str) -> Optional[str]:
        """查找命令路径"""
        try:
            # 使用 shutil.which 查找命令
            import shutil
            path = shutil.which(command)
            if path:
                return path

            # 如果找不到，尝试常见的路径
            if self.platform.is_windows():
                # Windows 下检查当前目录和 PATH
                import os
                for path_dir in self.env.get('PATH', '').split(self.platform.get_env_separator()):
                    test_path = os.path.join(path_dir, f"{command}.exe")
                    if os.path.exists(test_path):
                        return test_path
                    test_path = os.path.join(path_dir, f"{command}.bat")
                    if os.path.exists(test_path):
                        return test_path

            return None
        except Exception:
            return None

    def run_script(self, script_path: str, args: List[str] = None) -> Tuple[int, str, str]:
        """运行脚本文件"""
        args = args or []

        # 根据扩展名确定解释器
        if script_path.endswith('.py'):
            return self.execute('python', [script_path] + args, capture_output=True)
        elif script_path.endswith('.sh'):
            return self.execute('bash', [script_path] + args, capture_output=True)
        elif script_path.endswith('.bat') or script_path.endswith('.cmd'):
            return self.execute(script_path, args, capture_output=True)
        else:
            # 尝试直接执行
            return self.execute(script_path, args, capture_output=True)