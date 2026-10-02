"""
KShell - 进程管理模块 (v2.0)
使用 subprocess 执行系统命令。

v2.0 变化:
  * 集成 SystemCommandResolver，直接使用系统 PATH 中的命令
  * 新增 run_system()：完整 argv 透传（不再丢失 -x/--long 选项）
  * 支持 Windows cmd.exe 内部命令（dir/ver/title 等）
  * 输出使用 errors='replace' 解码，避免非 UTF-8 输出导致崩溃
"""

import pathlib
import subprocess
import sys
from typing import Optional, Tuple, List
from kplatform import Platform
from syscmd import SystemCommandResolver

class ProcessManager:
    """进程管理器"""

    def __init__(self, platform: Platform):
        self.platform = platform
        self.env = self._get_env_vars()
        self.filesystem = None
        # 系统命令解析器（扫描 PATH）
        self.resolver = SystemCommandResolver(platform, self.env)

    def _get_env_vars(self) -> dict:
        """获取环境变量"""
        import os
        return dict(os.environ)

    # ------------------------------------------------------------------
    # 环境与工作目录
    # ------------------------------------------------------------------

    def set_filesystem(self, filesystem):
        """绑定文件系统，使外部命令在 KShell 当前目录下执行"""
        self.filesystem = filesystem

    def _get_cwd(self) -> str:
        """获取当前工作目录（优先使用 KShell 维护的目录）"""
        if self.filesystem is not None:
            try:
                return self.filesystem.getcwd()
            except Exception:
                pass
        return str(pathlib.Path.cwd())

    # ------------------------------------------------------------------
    # 系统命令解析（v2.0）
    # ------------------------------------------------------------------

    def refresh_commands(self) -> int:
        """重新扫描系统 PATH，返回命令数量"""
        return self.resolver.refresh()

    def resolve(self, command: str):
        """解析系统命令，返回 SystemCommand 或 None"""
        return self.resolver.resolve(command)

    def path_entries(self) -> List[str]:
        """返回 PATH 目录列表"""
        return self.resolver.path_entries()

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    def run_system(self, command: str, args: List[str],
                   stdin_data: Optional[str] = None) -> Tuple[int, str]:
        """
        执行系统命令（完整参数透传）
        stdin_data: 管道上游输出，作为标准输入传入
        返回: (返回码, 合并后的输出)
        """
        entry = self.resolver.resolve(command)

        if entry is None:
            return 127, f"{command}: command not found\n"

        if entry.kind == 'cmd_builtin':
            # cmd.exe 内部命令需要 shell 解释
            argv = ['cmd', '/c', command] + list(args)
        else:
            argv = [entry.path] + list(args)

        try:
            result = subprocess.run(
                argv,
                input=stdin_data,
                capture_output=True,
                text=True,
                errors='replace',
                cwd=self._get_cwd(),
                env=self.env,
            )
            output = result.stdout or ''
            if result.stderr:
                output += result.stderr
            return result.returncode, output

        except FileNotFoundError:
            return 127, f"{command}: command not found\n"
        except PermissionError as e:
            return 126, f"{command}: 权限不足 ({e})\n"
        except KeyboardInterrupt:
            return 130, f"{command}: 已被中断\n"
        except Exception as e:
            return 1, f"Error executing {command}: {e}\n"

    def execute(self,
                command: str,
                args: List[str],
                capture_output: bool = False,
                shell: bool = False) -> Tuple[int, str, str]:
        """
        执行命令（兼容旧接口）
        返回: (返回码, 标准输出, 标准错误)
        """
        try:
            if shell:
                if self.platform.is_windows():
                    full_cmd = ['cmd', '/c', command] + args
                else:
                    full_cmd = [command] + args
            else:
                full_cmd = [command] + args

            result = subprocess.run(
                full_cmd,
                capture_output=capture_output,
                text=True,
                errors='replace',
                env=self.env,
                shell=shell,
                cwd=self._get_cwd()
            )

            stdout = result.stdout if capture_output else ''
            stderr = result.stderr if capture_output else ''

            return result.returncode, stdout, stderr

        except FileNotFoundError:
            return 127, '', f"Command not found: {command}"
        except Exception as e:
            return 1, '', str(e)

    def execute_interactive(self, command: str, args: List[str]) -> int:
        """交互式执行命令"""
        try:
            entry = self.resolver.resolve(command)
            if entry is None:
                print(f"{command}: command not found")
                return 127
            if entry.kind == 'cmd_builtin':
                full_cmd = ['cmd', '/c', command] + args
            else:
                full_cmd = [entry.path] + args
            result = subprocess.run(
                full_cmd,
                env=self.env,
                cwd=self._get_cwd()
            )
            return result.returncode
        except FileNotFoundError:
            print(f"{command}: command not found")
            return 127
        except Exception as e:
            print(f"Error: {e}")
            return 1

    # ------------------------------------------------------------------
    # 环境变量
    # ------------------------------------------------------------------

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
        """查找系统命令路径"""
        return self.resolver.path_of(command)

    def run_script(self, script_path: str, args: List[str] = None) -> Tuple[int, str, str]:
        """运行脚本文件"""
        args = args or []

        if script_path.endswith('.py'):
            return self.execute(sys.executable, [script_path] + args, capture_output=True)
        elif script_path.endswith('.sh'):
            return self.execute('bash', [script_path] + args, capture_output=True)
        elif script_path.endswith('.bat') or script_path.endswith('.cmd'):
            return self.execute(script_path, args, capture_output=True)
        else:
            return self.execute(script_path, args, capture_output=True)
