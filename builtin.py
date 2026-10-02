"""
内置命令模块
实现终端的内置命令
"""

import datetime
from typing import List, Optional, Tuple
from filesystem import FileSystem
from kplatform import Platform

class BuiltinCommands:
    """内置命令处理器"""

    def __init__(self, filesystem: FileSystem, platform: Platform, parser=None, settings=None, theme=None):
        self.fs = filesystem
        self.platform = platform
        self.parser = parser
        self.settings = settings
        self.theme = theme
        self.history: List[str] = []
        self.max_history = 1000
        if settings:
            self.max_history = settings.get('history_size', 1000)

        # 命令映射
        self.commands = {
            'cd': self.cmd_cd,
            'ls': self.cmd_ls,
            'dir': self.cmd_ls,  # Windows 别名
            'pwd': self.cmd_pwd,
            'echo': self.cmd_echo,
            'clear': self.cmd_clear,
            'cls': self.cmd_clear,  # Windows 别名
            'mkdir': self.cmd_mkdir,
            'md': self.cmd_mkdir,  # Windows 别名
            'rmdir': self.cmd_rmdir,
            'rd': self.cmd_rmdir,  # Windows 别名
            'rm': self.cmd_rm,
            'del': self.cmd_rm,  # Windows 别名
            'cp': self.cmd_cp,
            'copy': self.cmd_cp,  # Windows 别名
            'mv': self.cmd_mv,
            'move': self.cmd_mv,  # Windows 别名
            'cat': self.cmd_cat,
            'type': self.cmd_cat,  # Windows 别名
            'touch': self.cmd_touch,
            'history': self.cmd_history,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'help': self.cmd_help,
            'env': self.cmd_env,
            'set': self.cmd_set,
            'unset': self.cmd_unset,
            'export': self.cmd_export,
            'alias': self.cmd_alias,
            'unalias': self.cmd_unalias,
            'date': self.cmd_date,
            'time': self.cmd_time,
            'whoami': self.cmd_whoami,
            'hostname': self.cmd_hostname,
            'config': self.cmd_config,
            'theme': self.cmd_theme,
        }

        # 注册扩展命令 (sudo, grep, find, head, tail 等)
        try:
            from commands_extra import ExtraCommands
            ExtraCommands(self)
        except ImportError:
            pass  # 扩展命令模块不可用时静默跳过

    def set_process_manager(self, process_manager):
        """设置进程管理器引用（供 which 等命令使用）"""
        self.process_manager = process_manager

    def execute(self, command: str, args: List[str], options: dict) -> Tuple[int, str]:
        """
        执行内置命令
        返回: (返回码, 输出)
        """
        if command not in self.commands:
            return 1, f"Unknown command: {command}"

        try:
            return self.commands[command](args, options)
        except Exception as e:
            return 1, f"Error executing {command}: {e}"

    def cmd_cd(self, args: List[str], options: dict) -> Tuple[int, str]:
        """改变当前目录"""
        if not args:
            # cd 不带参数，切换到主目录
            target = self.platform.home_dir
        else:
            target = args[0]

        if self.fs.chdir(target):
            return 0, ''
        else:
            return 1, f"cd: {target}: No such directory or permission denied"

    def cmd_ls(self, args: List[str], options: dict) -> Tuple[int, str]:
        """列出目录内容"""
        path = args[0] if args else None
        show_hidden = 'a' in options or 'all' in options
        show_details = 'l' in options or 'long' in options
        show_recursive = 'r' in options or 'recursive' in options

        if show_recursive:
            return self._ls_recursive(path, show_hidden, show_details)

        items = self.fs.list_dir(path, show_hidden)
        output = []

        def _color(name, item_type):
            """根据类型着色"""
            if self.theme:
                if item_type == 'dir':
                    return self.theme.colorize(name, 'dir')
                elif item_type == 'link':
                    return self.theme.colorize(name, 'link')
                else:
                    return self.theme.colorize(name, 'file')
            return name

        # v2.0：判断 path 是否指向单个文件（此时不应再拼接子项名）
        single_file = bool(path) and self.fs.is_file(path)

        for name, item_type in items:
            if show_details:
                if single_file:
                    target_path = path
                else:
                    target_path = path + '/' + name if path else name
                info = self.fs.get_file_info(target_path)
                if info:
                    size = self._format_size(info['size'])
                    modified = datetime.datetime.fromtimestamp(
                        info['modified']).strftime('%Y-%m-%d %H:%M')
                    type_char = 'd' if item_type == 'dir' else 'f'
                    output.append(f"{type_char} {size:>10} {modified} {_color(name, item_type)}")
            else:
                # 使用颜色标记目录/文件/链接
                if item_type == 'dir':
                    output.append(_color(name, 'dir') + '/')
                else:
                    output.append(_color(name, item_type))

        return 0, '\n'.join(output)

    def _ls_recursive(self, path: str, show_hidden: bool, show_details: bool) -> Tuple[int, str]:
        """递归列出目录"""
        output = []
        base_path = path or self.fs.getcwd()

        def walk(current_path: str, prefix: str = ''):
            items = self.fs.list_dir(current_path, show_hidden)
            display_path = current_path.replace(base_path, '.') if current_path != base_path else '.'

            if prefix:
                output.append(f"\n{display_path}:")

            for name, item_type in items:
                full_path = f"{current_path}/{name}" if current_path else name
                rel_path = f"{prefix}{name}" if prefix else name

                if show_details:
                    info = self.fs.get_file_info(full_path)
                    if info:
                        size = self._format_size(info['size'])
                        modified = datetime.datetime.fromtimestamp(
                            info['modified']).strftime('%Y-%m-%d %H:%M')
                        type_char = 'd' if item_type == 'dir' else 'f'
                        output.append(f"  {type_char} {size:>10} {modified} {name}")
                else:
                    if item_type == 'dir':
                        output.append(f"  {name}/")
                    else:
                        output.append(f"  {name}")

                if item_type == 'dir':
                    walk(full_path, rel_path + '/')

        walk(base_path)
        return 0, '\n'.join(output)

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

    def cmd_pwd(self, args: List[str], options: dict) -> Tuple[int, str]:
        """打印当前工作目录"""
        return 0, self.fs.getcwd()

    def cmd_echo(self, args: List[str], options: dict) -> Tuple[int, str]:
        """打印文本"""
        output = ' '.join(args)
        if 'n' not in options:
            output += '\n'
        return 0, output

    def cmd_clear(self, args: List[str], options: dict) -> Tuple[int, str]:
        """清屏"""
        # 使用 ANSI 转义序列清屏
        print('\033[2J\033[H', end='', flush=True)
        return 0, ''

    def cmd_mkdir(self, args: List[str], options: dict) -> Tuple[int, str]:
        """创建目录"""
        if not args:
            return 1, "mkdir: missing operand"

        parents = 'p' in options or 'parents' in options
        errors = []

        for path in args:
            if not self.fs.mkdir(path, parents=parents):
                errors.append(path)

        if errors:
            return 1, f"mkdir: cannot create directory '{', '.join(errors)}'"
        return 0, ''

    def cmd_rmdir(self, args: List[str], options: dict) -> Tuple[int, str]:
        """删除空目录"""
        if not args:
            return 1, "rmdir: missing operand"

        recursive = 'p' in options or 'parents' in options
        errors = []

        for path in args:
            if not self.fs.remove_dir(path, recursive=recursive):
                errors.append(path)

        if errors:
            return 1, f"rmdir: failed to remove '{', '.join(errors)}'"
        return 0, ''

    def cmd_rm(self, args: List[str], options: dict) -> Tuple[int, str]:
        """删除文件或目录"""
        if not args:
            return 1, "rm: missing operand"

        recursive = 'r' in options or 'recursive' in options
        force = 'f' in options or 'force' in options
        errors = []

        for path in args:
            if not self.fs.exists(path):
                if not force:
                    errors.append(f"{path}: No such file or directory")
                continue

            if self.fs.is_dir(path):
                if not self.fs.remove_dir(path, recursive=recursive):
                    errors.append(path)
            else:
                if not self.fs.remove_file(path):
                    errors.append(path)

        if errors:
            return 1, "rm: " + "; ".join(errors)
        return 0, ''

    def cmd_cp(self, args: List[str], options: dict) -> Tuple[int, str]:
        """复制文件或目录"""
        if len(args) < 2:
            return 1, "cp: missing file operand"

        src = args[0]
        dst = args[1]
        recursive = 'r' in options or 'recursive' in options

        if self.fs.is_dir(src):
            if recursive:
                if not self.fs.copy_dir(src, dst):
                    return 1, f"cp: failed to copy directory '{src}'"
            else:
                return 1, f"cp: -r not specified; omitting directory '{src}'"
        else:
            if not self.fs.copy_file(src, dst):
                return 1, f"cp: failed to copy '{src}'"

        return 0, ''

    def cmd_mv(self, args: List[str], options: dict) -> Tuple[int, str]:
        """移动或重命名文件"""
        if len(args) < 2:
            return 1, "mv: missing file operand"

        src = args[0]
        dst = args[1]

        if not self.fs.move(src, dst):
            return 1, f"mv: failed to move '{src}'"
        return 0, ''

    def cmd_cat(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示文件内容"""
        if not args:
            return 1, "cat: missing file operand"

        output = []
        show_numbers = 'n' in options or 'number' in options

        for path in args:
            content = self.fs.read_file(path)
            if content is None:
                return 1, f"cat: {path}: No such file or directory"

            if show_numbers:
                lines = content.split('\n')
                numbered = '\n'.join(f"{i+1:6d}\t{line}" for i, line in enumerate(lines))
                output.append(numbered)
            else:
                output.append(content)

        return 0, '\n'.join(output)

    def cmd_touch(self, args: List[str], options: dict) -> Tuple[int, str]:
        """创建空文件或更新时间戳"""
        if not args:
            return 1, "touch: missing file operand"

        for path in args:
            self.fs.write_file(path, '')

        return 0, ''

    def cmd_history(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示命令历史"""
        # 支持 history -c 清空历史
        if '-c' in args or 'c' in options:
            self.history.clear()
            return 0, "history cleared"

        show_numbers = 'n' not in options and 'number' not in options

        if not self.history:
            return 0, "(history is empty)"

        if show_numbers:
            output = [f"{i+1:4d}  {cmd}" for i, cmd in enumerate(self.history)]
        else:
            output = self.history

        return 0, '\n'.join(output)

    def cmd_exit(self, args: List[str], options: dict) -> Tuple[int, str]:
        """退出终端"""
        return -1, 'exit'

    def cmd_help(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示帮助信息（支持主题着色）"""
        th = self.theme

        def _c(text, key):
            if th:
                return th.colorize(text, key)
            return text

        output = [
            _c("KShell 2.0 - 跨平台终端", 'banner_title'),
            "",
            _c("系统命令 (v2.0 新特性):", 'title'),
            "  任意 PATH 中的命令   - 直接输入即可执行，如 git, python, ipconfig",
            "  command <cmd>        - 强制执行系统版本，绕过同名内置命令",
            "  path                 - 查看 PATH 目录与系统命令总数",
            "  path -s <关键字>      - 搜索系统命令",
            "  path -b              - 显示被内置命令优先接管的系统命令",
            "  path -a / -r <目录>   - 添加/移除 PATH 目录（当前会话）",
            "  path -F              - 强制重新扫描系统命令",
            "  优先级               - 内置命令优先于系统同名命令（可用 config 调整）",
            "",
            _c("文件操作:", 'title'),
            "  cd <dir>        - 改变当前目录",
            "  ls [dir]        - 列出目录内容 (选项: -l, -a, -r)",
            "  pwd             - 显示当前目录",
            "  mkdir <dir>     - 创建目录",
            "  rmdir <dir>     - 删除空目录",
            "  rm <file>       - 删除文件",
            "  cp <src> <dst>  - 复制文件",
            "  mv <src> <dst>  - 移动/重命名文件",
            "  cat <file>      - 显示文件内容",
            "  touch <file>    - 创建空文件",
            "  head [-n N] <f> - 显示文件前 N 行",
            "  tail [-n N] <f> - 显示文件后 N 行",
            "  grep [-i] [-n] [-r] <pattern> [file...] - 搜索文本",
            "  wc [-l] [-w] [-c] <file> - 统计行数/字数/字节",
            "  sort [-r] <file>- 排序文本行",
            "  uniq <file>     - 去除相邻重复行",
            "  nl <file>       - 带行号显示文件",
            "  find [path] [-name pattern] [-type f|d] - 查找文件",
            "  tree [path]     - 显示目录树",
            "  stat <file>     - 显示文件详细信息",
            "  du [-h] [path]  - 计算目录大小",
            "  df [-h]         - 显示磁盘使用情况",
            "",
            _c("系统命令:", 'title'),
            "  sudo <cmd>      - 以管理员/root 权限执行",
            "  ps              - 显示进程列表",
            "  kill [-f] <pid> - 终止进程",
            "  sleep <sec>     - 延迟指定秒数",
            "  uptime          - 显示系统运行时间",
            "  uname [-a]      - 显示系统信息",
            "  id              - 显示用户身份",
            "  date            - 显示日期",
            "  time            - 显示时间",
            "  whoami          - 显示当前用户",
            "  hostname        - 显示主机名",
            "",
            _c("工具命令:", 'title'),
            "  echo <text>     - 打印文本",
            "  clear/cls       - 清屏",
            "  history         - 显示命令历史 (history -c 清空)",
            "  env             - 显示环境变量",
            "  set <key=val>   - 设置环境变量",
            "  unset <key>     - 删除环境变量",
            "  alias <name=val>- 设置别名",
            "  unalias <name>  - 删除别名",
            "  which <cmd>     - 查找命令路径 (which -a 显示系统路径)",
            "  calc <表达式>    - 简单计算器，如 calc (1+2)*3",
            "  base64 [-d] <t> - Base64 编码/解码",
            "  md5sum <file>   - 计算 MD5 哈希",
            "  sha1sum <file>  - 计算 SHA1 哈希",
            "  sha256sum <f>   - 计算 SHA256 哈希",
            "  seq [start] end [step] - 生成数字序列",
            "  yes [text]      - 重复输出文本",
            "  true/false      - 返回成功/失败状态",
            "  man <cmd>       - 显示命令帮助",
            "  theme [list|preview|<name>] - 管理颜色主题",
            "  config          - 管理终端设置",
            "  help            - 显示帮助",
            "  exit            - 退出终端",
            "",
            _c("选项:", 'title'),
            "  -l, --long      - 显示详细信息",
            "  -a, --all       - 显示隐藏文件",
            "  -r, --recursive - 递归操作",
            "  -f, --force     - 强制操作",
            "  -i              - 忽略大小写",
            "  -n              - 显示行号",
            "  -h              - 人类可读大小",
        ]
        return 0, '\n'.join(output)

    def cmd_env(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示环境变量"""
        import os
        env_vars = dict(os.environ)
        output = [f"{k}={v}" for k, v in sorted(env_vars.items())]
        return 0, '\n'.join(output)

    def cmd_set(self, args: List[str], options: dict) -> Tuple[int, str]:
        """设置环境变量"""
        if not args:
            return self.cmd_env(args, options)

        for arg in args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                import os
                os.environ[key] = value
            else:
                import os
                if arg in os.environ:
                    return 0, f"{arg}={os.environ[arg]}"
                else:
                    return 1, f"set: {arg}: not found"

        return 0, ''

    def cmd_unset(self, args: List[str], options: dict) -> Tuple[int, str]:
        """删除环境变量"""
        if not args:
            return 1, "unset: missing argument"

        import os
        for key in args:
            if key in os.environ:
                del os.environ[key]

        return 0, ''

    def cmd_export(self, args: List[str], options: dict) -> Tuple[int, str]:
        """导出环境变量（Unix风格）"""
        return self.cmd_set(args, options)

    def cmd_alias(self, args: List[str], options: dict) -> Tuple[int, str]:
        """设置或显示别名"""
        # 使用 self.parser (来自 Terminal 实例)
        parser = self.parser if self.parser else CommandParser()

        if not args:
            # 显示别名
            runtime_aliases = parser.list_aliases()
            persistent_aliases = self.settings.get_aliases() if self.settings else {}
            all_aliases = {**persistent_aliases, **runtime_aliases}
            output = [f"{k}='{v}'" for k, v in sorted(all_aliases.items())]
            return 0, '\n'.join(output)

        for arg in args:
            if '=' in arg:
                name, value = arg.split('=', 1)
                # 添加到运行时解析器
                parser.add_alias(name, value)
                # 持久化到设置
                if self.settings:
                    self.settings.add_alias(name, value)
            else:
                # 查找特定别名
                runtime_aliases = parser.list_aliases()
                persistent_aliases = self.settings.get_aliases() if self.settings else {}
                all_aliases = {**persistent_aliases, **runtime_aliases}
                if arg in all_aliases:
                    return 0, f"{arg}='{all_aliases[arg]}'"
                else:
                    return 1, f"alias: {arg}: not found"

        return 0, ''

    def cmd_unalias(self, args: List[str], options: dict) -> Tuple[int, str]:
        """删除别名"""
        if not args:
            return 1, "unalias: missing argument"

        parser = self.parser if self.parser else CommandParser()

        for name in args:
            # 从运行时移除
            parser.remove_alias(name)
            # 从持久化设置移除
            if self.settings:
                self.settings.remove_alias(name)

        return 0, ''

    def cmd_date(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示日期"""
        now = datetime.datetime.now()
        return 0, now.strftime('%Y-%m-%d %A')

    def cmd_time(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示时间"""
        now = datetime.datetime.now()
        return 0, now.strftime('%H:%M:%S')

    def cmd_whoami(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示当前用户"""
        import getpass
        return 0, getpass.getuser()

    def cmd_hostname(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示主机名"""
        import socket
        return 0, socket.gethostname()

    def cmd_config(self, args: List[str], options: dict) -> Tuple[int, str]:
        """管理 KShell 设置"""
        if not self.settings:
            return 1, "Error: Settings manager not initialized."

        if not args:
            # 默认行为：列出所有设置
            return self.cmd_config(['list'], options)

        action = args[0]

        if action == 'list':
            output = ["KShell Settings:"]
            for key, value in self.settings.get_all().items():
                output.append(f"  {key}: {value}")
            return 0, '\n'.join(output)

        elif action == 'get':
            if len(args) < 2:
                return 1, "Usage: config get <key>"
            key = args[1]
            value = self.settings.get(key, "Not found")
            return 0, f"{key} = {value}"

        elif action == 'set':
            if len(args) < 3:
                return 1, "Usage: config set <key> <value>"
            key = args[1]
            # 尝试推断值的类型
            value_str = ' '.join(args[2:])
            value = self._parse_config_value(value_str)
            self.settings.set(key, value)
            # 实时同步主题
            if key == 'theme' and self.theme:
                if not self.theme.set_theme(str(value)):
                    return 1, f"Unknown theme: {value} (use 'theme list' to see available themes)"
            return 0, f"Set {key} = {value}"

        elif action == 'reset':
            self.settings.reset()
            return 0, "Settings reset to defaults."

        else:
            return 1, f"Unknown config action: {action}\nUsage: config [list|get|set|reset]"

    def cmd_theme(self, args: List[str], options: dict) -> Tuple[int, str]:
        """管理颜色主题"""
        if not self.theme:
            return 1, "Error: Theme manager not initialized."

        th = self.theme

        if not args:
            # 无参数: 显示当前主题
            name_c = th.colorize(th.name, 'success')
            return 0, f"当前主题: {name_c}\n可用主题: {', '.join(th.list_themes())}"

        action = args[0]

        if action == 'list':
            # 列出所有主题
            lines = []
            for name in th.list_themes():
                mark = th.colorize('*', 'success') if name == th.name else ' '
                lines.append(f"  {mark} {name}")
            return 0, '\n'.join(lines)

        elif action == 'preview':
            # 预览所有主题色块
            return 0, th.preview()

        else:
            # 切换主题
            if th.set_theme(action):
                # 同步保存到设置
                if self.settings:
                    self.settings.set('theme', action)
                return 0, f"主题已切换: {th.colorize(action, 'success')}\n{th.preview()}"
            else:
                return 1, f"未知主题: {action}\n可用主题: {', '.join(th.list_themes())}"

    def _parse_config_value(self, value_str: str):
        """尝试解析配置值为合适的类型"""
        # 尝试布尔值
        if value_str.lower() in ('true', 'yes', '1'):
            return True
        if value_str.lower() in ('false', 'no', '0'):
            return False

        # 尝试整数
        try:
            return int(value_str)
        except ValueError:
            pass

        # 尝试浮点数
        try:
            return float(value_str)
        except ValueError:
            pass

        # 默认返回字符串
        return value_str

    def add_to_history(self, command: str):
        """添加命令到历史"""
        if command and command.strip():
            self.history.append(command.strip())
            # 动态从设置获取最大历史长度
            current_max = self.max_history
            if self.settings:
                current_max = self.settings.get('history_size', self.max_history)

            if len(self.history) > current_max:
                self.history = self.history[-current_max:]