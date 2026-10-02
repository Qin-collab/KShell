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
        self.process_manager.set_filesystem(self.filesystem)
        self.builtin = BuiltinCommands(self.filesystem, self.platform, self.parser, self.settings, self.theme)
        self.builtin.set_process_manager(self.process_manager)

        self.version = "2.0"
        self.running = True
        self.exit_code = 0
        self.max_history = self.settings.get('history_size', 1000)

    def run(self):
        """运行终端主循环"""
        # 显示启动横幅
        if self.settings.get('banner_enabled', True):
            print(get_banner(self.platform, version=self.version, theme=self.theme))

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

        # 原始参数（保留选项与顺序，用于系统命令透传）
        _, raw_args = self.parser.raw_split(user_input)
        clean_raw_args, _, _ = self.parser.parse_redirect(raw_args)

        # 执行命令
        return_code, output = self._execute_command(command, clean_args, options, clean_raw_args)

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

    def _execute_command(self, command: str, args: list, options: dict, raw_args: list = None) -> Tuple[int, str]:
        """
        执行单个命令

        优先级规则（v2.0）:
          1. 内置命令（KShell 自己实现）优先，可被同名系统命令遮蔽
          2. 内置没有的，到系统 PATH 中查找并直接执行
          3. 设置 builtin_priority=false 时改为系统命令优先
          4. `command <cmd>` 可强制使用系统命令，绕过同名内置命令
        """
        raw_args = list(raw_args) if raw_args else list(args)

        # 强制走系统命令（bash 风格的 command 内置）
        if command == 'command':
            if not raw_args:
                return 1, "command: 用法: command <系统命令> [参数...]\n"
            return self._execute_external(raw_args[0], raw_args[1:])

        is_builtin = command in self.builtin.commands
        builtin_first = self.settings.get('builtin_priority', True)

        if builtin_first:
            if is_builtin:
                return self.builtin.execute(command, args, options)
            return self._execute_external(command, raw_args)

        # 系统命令优先模式
        if self.process_manager.resolve(command) is not None:
            return self._execute_external(command, raw_args)
        if is_builtin:
            return self.builtin.execute(command, args, options)
        return self._execute_external(command, raw_args)

    def _execute_external(self, command: str, args: list) -> Tuple[int, str]:
        """执行系统 PATH 中的命令（完整参数透传）"""
        if not command:
            return 1, "未指定命令\n"
        return self.process_manager.run_system(command, list(args))

    def _execute_pipeline(self, pipeline_str: str):
        """
        执行管道命令（v2.0：上游输出真正传递给下游）
        内置命令与系统命令可以混合使用
        """
        commands = self.parser.parse_pipeline(pipeline_str)
        if len(commands) < 2:
            return

        data = None        # 上游输出
        return_code = 0
        output = ''

        for segment in commands:
            segment = segment.strip()
            if not segment:
                continue

            command, args, options = self.parser.parse(segment)
            if not command:
                continue

            _, raw_args = self.parser.raw_split(segment)
            clean_raw_args, _, _ = self.parser.parse_redirect(raw_args)

            if command in self.builtin.commands:
                return_code, output = self.builtin.execute(command, args, options)
            else:
                return_code, output = self.process_manager.run_system(
                    command, clean_raw_args, stdin_data=data
                )

            # 上游输出传给下一段（包含 stderr，保持诊断信息不丢失）
            data = output
            if return_code != 0 and not output:
                break

        # 打印最终输出
        if output:
            print(output, end='')
            if not output.endswith('\n'):
                print()

        self.exit_code = return_code

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