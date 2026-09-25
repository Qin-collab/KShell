"""
KShell - 主终端模块
跨平台终端核心逻辑
"""

import sys
import subprocess
import os
from typing import Optional, Tuple
from kplatform import Platform
from filesystem import FileSystem
from parser import CommandParser
from process import ProcessManager
from builtin import BuiltinCommands
from settings import SettingsManager
from banner import get_banner
from theme import ThemeManager, enable_ansi_windows, supports_color, strip_ansi

class Terminal:
    """终端核心类"""

    def __init__(self):
        self.platform = Platform()
        self.filesystem = FileSystem(self.platform)
        self.settings = SettingsManager()

        # 初始化主题
        enable_ansi_windows()
        theme_name = self.settings.get('theme', 'default')
        color_enabled = self.settings.get('use_colors', True) and supports_color()
        self.theme = ThemeManager(name=theme_name, enabled=color_enabled)

        self.parser = CommandParser()
        # 加载持久化别名
        persistent_aliases = self.settings.get_aliases()
        for name, cmd in persistent_aliases.items():
            self.parser.add_alias(name, cmd)

        self.process_manager = ProcessManager(self.platform)
        self.builtin = BuiltinCommands(self.filesystem, self.platform, self.parser, self.settings, self.theme)
        self.builtin.set_process_manager(self.process_manager)

        self.running = True
        self.exit_code = 0
        self.max_history = self.settings.get('history_size', 1000)

    def run(self):
        """运行终端主循环"""
        # 显示启动横幅
        if self.settings.get('banner_enabled', True):
            print(get_banner(self.platform, version="1.0", theme=self.theme))

        # 显示欢迎消息
        welcome_msg = self.settings.get('welcome_message')
        if welcome_msg and welcome_msg != "Welcome to KShell!":
            print(f"{welcome_msg}\n")

        while self.running:
            try:
                # 显示提示符
                prompt = self._get_prompt()
                user_input = input(prompt)

                # 处理输入
                self._process_input(user_input)

            except KeyboardInterrupt:
                # Ctrl+C
                print()
                continue
            except EOFError:
                # Ctrl+D
                print()
                self.running = False
                break
            except Exception as e:
                print(f"Error: {e}")

    def _get_prompt(self) -> str:
        """生成提示符（带主题颜色）"""
        th = self.theme
        username = os.environ.get('USER', os.environ.get('USERNAME', 'user'))
        cwd = self.filesystem.getcwd()
        home = self.platform.home_dir

        # 简化路径显示
        if cwd.lower().startswith(home.lower()):
            cwd = '~' + cwd[len(home):]

        style = self.settings.get('prompt_style', 'default')

        if style == 'simple':
            return th.colorize("$ ", 'prompt_sym')

        elif style == 'poweruser':
            import datetime
            import socket
            time_str = datetime.datetime.now().strftime("%H:%M")
            host = socket.gethostname()
            line1 = (f"[{time_str}] "
                     f"{th.colorize(username, 'prompt_user')}@{host}:"
                     f"{th.colorize(cwd, 'prompt_dir')}")
            return f"{line1}\n{th.colorize('$ ', 'prompt_sym')} "

        else:  # default
            u = th.colorize(username, 'prompt_user')
            d = th.colorize(cwd, 'prompt_dir')
            sym = th.colorize("> ", 'prompt_sym') if self.platform.is_windows() else th.colorize("$ ", 'prompt_sym')
            if self.platform.is_windows():
                return f"{u}@{d}{sym}"
            else:
                import getpass
                username = getpass.getuser()
                u = th.colorize(username, 'prompt_user')
                return f"{u}:{d}{sym} "

    def _process_input(self, user_input: str):
        """处理用户输入"""
        if not user_input.strip():
            return

        # 添加到历史
        self.builtin.add_to_history(user_input)

        # 解析命令
        command, args, options = self.parser.parse(user_input)

        if not command:
            return

        # 处理管道
        if '|' in user_input:
            self._execute_pipeline(user_input)
            return

        # 处理重定向
        clean_args, output_file, input_file = self.parser.parse_redirect(args)

        # 执行命令
        return_code, output = self._execute_command(command, clean_args, options)

        # 处理输出重定向
        if output_file:
            append = output_file.startswith('>>')
            file_path = output_file[2:] if append else output_file
            # 写入文件时去除 ANSI 颜色码
            clean_output = strip_ansi(output)
            self.filesystem.write_file(file_path, clean_output, append=append)
        else:
            # 打印输出
            if output:
                print(output, end='')
                # 确保输出以换行结束，避免提示符与输出粘连
                # echo -n 除外（用户明确要求不换行）
                if not output.endswith('\n') and not (command == 'echo' and 'n' in options):
                    print()

        self.exit_code = return_code

        # 处理退出命令
        if return_code == -1:
            self.running = False

    def _execute_command(self, command: str, args: list, options: dict) -> Tuple[int, str]:
        """执行单个命令"""
        # 检查是否是内置命令
        if command in self.builtin.commands:
            return self.builtin.execute(command, args, options)

        # 执行外部命令
        return self._execute_external(command, args, options)

    def _execute_external(self, command: str, args: list, options: dict) -> Tuple[int, str]:
        """执行外部命令"""
        # 检查命令是否存在
        cmd_path = self.process_manager.which(command)
        if not cmd_path:
            return 1, f"{command}: command not found\n"

        try:
            # 执行命令
            result = subprocess.run(
                [command] + args,
                capture_output=True,
                text=True,
                cwd=self.filesystem.getcwd(),
                shell=False
            )

            output = result.stdout
            if result.stderr:
                output += result.stderr

            return result.returncode, output

        except Exception as e:
            return 1, f"Error executing {command}: {e}\n"

    def _execute_pipeline(self, pipeline_str: str):
        """执行管道命令"""
        commands = self.parser.parse_pipeline(pipeline_str)

        if len(commands) < 2:
            return

        # 处理第一个命令
        first_cmd, first_args, first_opts = self.parser.parse(commands[0])
        return_code, output = self._execute_command(first_cmd, first_args, first_opts)

        if return_code != 0:
            return

        # 处理中间命令
        for cmd_str in commands[1:-1]:
            command, args, options = self.parser.parse(cmd_str)
            # 将前一个命令的输出作为输入
            # 这里简化处理，实际需要更复杂的管道实现
            return_code, output = self._execute_command(command, args, options)
            if return_code != 0:
                break

        # 处理最后一个命令
        last_cmd_str = commands[-1]
        last_cmd, last_args, last_opts = self.parser.parse(last_cmd_str)
        last_cmd, last_args, last_opts = self.parser.parse(last_cmd_str)
        return_code, output = self._execute_command(last_cmd, last_args, last_opts)

        # 打印最终输出
        if output:
            print(output, end='')
            # 确保输出以换行结束，避免提示符与输出粘连
            if not output.endswith('\n'):
                print()

    def execute_script(self, script_path: str):
        """执行脚本文件"""
        content = self.filesystem.read_file(script_path)
        if content is None:
            print(f"Error: Cannot read script: {script_path}")
            return

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            self._process_input(line)

def main():
    """主函数"""
    terminal = Terminal()
    terminal.run()

if __name__ == '__main__':
    main()