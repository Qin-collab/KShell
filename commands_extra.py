"""
扩展命令模块
实现额外的内置命令（sudo、文件内容、查找、系统、工具类命令）
"""

import base64
import datetime
import fnmatch
import hashlib
import pathlib
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple


class ExtraCommands:
    """扩展命令处理器"""

    def __init__(self, builtin):
        self.builtin = builtin
        self.fs = builtin.fs
        self.platform = builtin.platform
        self.settings = builtin.settings
        self._register()

    def _register(self):
        """注册扩展命令到 builtin"""
        self.builtin.commands.update({
            # 权限
            'sudo': self.cmd_sudo,
            # 文件内容
            'head': self.cmd_head,
            'tail': self.cmd_tail,
            'grep': self.cmd_grep,
            'wc': self.cmd_wc,
            'sort': self.cmd_sort,
            'uniq': self.cmd_uniq,
            'nl': self.cmd_nl,
            'tee': self.cmd_tee,
            # 查找和信息
            'find': self.cmd_find,
            'tree': self.cmd_tree,
            'stat': self.cmd_stat,
            'du': self.cmd_du,
            'df': self.cmd_df,
            'which': self.cmd_which,
            # 系统
            'ps': self.cmd_ps,
            'kill': self.cmd_kill,
            'sleep': self.cmd_sleep,
            'uptime': self.cmd_uptime,
            'uname': self.cmd_uname,
            'id': self.cmd_id,
            # 工具
            'base64': self.cmd_base64,
            'md5sum': self.cmd_md5sum,
            'sha256sum': self.cmd_sha256sum,
            'sha1sum': self.cmd_sha1sum,
            'seq': self.cmd_seq,
            'yes': self.cmd_yes,
            'true': self.cmd_true,
            'false': self.cmd_false,
            'man': self.cmd_man,
        })

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _parse_gnu_options(self, args: List[str], value_opts: set):
        """
        解析 GNU 风格选项（单横线长选项，如 -name, -type）
        返回: (位置参数列表, 选项字典)
        """
        opts = {}
        positional = []
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith('-') and len(arg) > 1:
                name = arg[1:]
                if '=' in name:
                    k, v = name.split('=', 1)
                    opts[k] = v
                elif name in value_opts:
                    # 带值选项
                    if i + 1 < len(args):
                        opts[name] = args[i + 1]
                        i += 1
                    else:
                        opts[name] = True
                else:
                    opts[name] = True
            else:
                positional.append(arg)
            i += 1
        return positional, opts

    def _format_bytes(self, size: int) -> str:
        """格式化字节大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

    def _split_content(self, content: str) -> List[str]:
        """拆分文件内容为行，去掉末尾空行"""
        lines = content.split('\n')
        if lines and lines[-1] == '':
            lines = lines[:-1]
        return lines

    # ------------------------------------------------------------------
    # sudo - 提权执行
    # ------------------------------------------------------------------

    def cmd_sudo(self, args: List[str], options: dict) -> Tuple[int, str]:
        """
        以管理员/root 权限执行命令
        Windows: 通过 UAC 提升 (Start-Process -Verb RunAs)
        Unix/Linux/macOS: 调用系统 sudo
        """
        if not args:
            return 1, "sudo: missing operand\nUsage: sudo <command> [args...]"

        command = args[0]
        cmd_args = args[1:]

        if self.platform.is_windows():
            # Windows: 使用 PowerShell UAC 提升，在新窗口中执行
            full_cmd = ' '.join([command] + cmd_args)
            ps_script = (
                f'Start-Process cmd -ArgumentList "/k", "{full_cmd}" '
                f'-Verb RunAs -WorkingDirectory "{self.fs.getcwd()}"'
            )
            try:
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command', ps_script],
                    capture_output=True, text=True, shell=False
                )
                if result.returncode == 0:
                    return 0, (
                        f"[sudo] 正在以管理员身份运行: {full_cmd}\n"
                        f"[sudo] 请在 UAC 弹窗中确认，命令将在新的提升窗口中执行。\n"
                        f"[sudo] 如果 UAC 被取消，命令不会执行。"
                    )
                else:
                    return 1, (
                        f"[sudo] 无法启动提升进程: {result.stderr.strip() or result.stdout.strip()}\n"
                        f"[sudo] UAC 提权需要在交互式桌面会话中运行。"
                    )
            except Exception as e:
                return 1, (
                    f"[sudo] 提权失败: {e}\n"
                    f"[sudo] 提示: 可直接右键「以管理员身份运行」来启动 KShell。"
                )
        else:
            # Unix: 调用系统 sudo
            try:
                result = subprocess.run(
                    ['sudo'] + [command] + cmd_args,
                    capture_output=True, text=True,
                    cwd=self.fs.getcwd(), shell=False
                )
                output = result.stdout
                if result.stderr:
                    output += result.stderr
                if result.returncode != 0 and not output:
                    output = f"sudo: command failed (exit code {result.returncode})"
                return result.returncode, output
            except FileNotFoundError:
                return 1, "sudo: command not found (is sudo installed?)"
            except Exception as e:
                return 1, f"sudo: {e}"

    # ------------------------------------------------------------------
    # 文件内容命令
    # ------------------------------------------------------------------

    def cmd_head(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示文件前 N 行 (默认 10)"""
        if not args:
            return 1, "head: missing file operand"

        lines_count = 10
        # 处理 -n N 形式（短选项不吞值，N 在位置参数中）
        if 'n' in options and args and args[0].isdigit():
            lines_count = int(args[0])
            args = args[1:]
        elif 'n' in options and '=' in str(options.get('n', '')):
            # --n=N 或 -n=N 形式
            lines_count = int(str(options['n']).split('=')[-1])

        if not args:
            return 1, "head: missing file operand"

        content = self.fs.read_file(args[0])
        if content is None:
            return 1, f"head: {args[0]}: No such file or directory"

        lines = self._split_content(content)
        return 0, '\n'.join(lines[:lines_count])

    def cmd_tail(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示文件后 N 行 (默认 10)"""
        if not args:
            return 1, "tail: missing file operand"

        lines_count = 10
        if 'n' in options and args and args[0].isdigit():
            lines_count = int(args[0])
            args = args[1:]

        if not args:
            return 1, "tail: missing file operand"

        content = self.fs.read_file(args[0])
        if content is None:
            return 1, f"tail: {args[0]}: No such file or directory"

        lines = self._split_content(content)
        return 0, '\n'.join(lines[-lines_count:])

    def cmd_grep(self, args: List[str], options: dict) -> Tuple[int, str]:
        """在文件中搜索文本模式"""
        if not args:
            return 1, "grep: missing pattern"

        pattern = args[0]
        files = args[1:]
        ignore_case = 'i' in options
        show_line_num = 'n' in options
        recursive = 'r' in options
        show_count = 'c' in options

        try:
            flags = re.IGNORECASE if ignore_case else 0
            regex = re.compile(pattern, flags)
        except re.error as e:
            return 1, f"grep: invalid pattern: {e}"

        results = []
        multiple_files = len(files) > 1 or recursive

        def search_file(file_path: str, display_name: str):
            content = self.fs.read_file(file_path)
            if content is None:
                return
            lines = self._split_content(content)
            if show_count:
                count = sum(1 for line in lines if regex.search(line))
                prefix = f"{display_name}:" if multiple_files else ""
                results.append(f"{prefix}{count}")
                return
            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    if show_line_num:
                        results.append(f"{display_name}:{i}:{line}" if multiple_files else f"{i}:{line}")
                    else:
                        results.append(f"{display_name}:{line}" if multiple_files else line)

        if recursive:
            # 递归搜索目录
            search_dirs = files if files else ['.']
            for search_dir in search_dirs:
                base = self._resolve_path(search_dir)
                if not base.exists():
                    results.append(f"grep: {search_dir}: No such file or directory")
                    continue
                if base.is_dir():
                    for p in base.rglob('*'):
                        if p.is_file():
                            search_file(str(p), str(p))
                else:
                    search_file(str(base), search_dir)
        elif files:
            for f in files:
                if self.fs.is_dir(f):
                    results.append(f"grep: {f}: Is a directory")
                else:
                    search_file(f, f)
        else:
            return 1, "grep: no input files (pipe input not supported yet)"

        if not results:
            return 1, ''
        return 0, '\n'.join(results)

    def _resolve_path(self, path: str) -> pathlib.Path:
        """解析路径"""
        p = pathlib.Path(path)
        if p.is_absolute():
            return p
        return (pathlib.Path(self.fs.getcwd()) / p).resolve()

    def cmd_wc(self, args: List[str], options: dict) -> Tuple[int, str]:
        """统计行数、字数、字节数"""
        show_lines = 'l' in options
        show_words = 'w' in options
        show_bytes = 'c' in options
        # 无选项时全部显示
        if not (show_lines or show_words or show_bytes):
            show_lines = show_words = show_bytes = True

        targets = args if args else ['.']

        output = []
        for target in targets:
            if self.fs.is_dir(target):
                output.append(f"wc: {target}: Is a directory")
                continue
            content = self.fs.read_file(target)
            if content is None:
                output.append(f"wc: {target}: No such file or directory")
                continue

            lines = content.split('\n')
            # 最后一行如果是空（以换行结尾），不计入
            line_count = len(lines) - 1 if lines and lines[-1] == '' else len(lines)
            word_count = len(content.split())
            byte_count = len(content.encode('utf-8', errors='ignore'))

            parts = []
            if show_lines:
                parts.append(f"{line_count:7d}")
            if show_words:
                parts.append(f"{word_count:7d}")
            if show_bytes:
                parts.append(f"{byte_count:7d}")
            parts.append(target)
            output.append(' '.join(parts))

        return 0, '\n'.join(output)

    def cmd_sort(self, args: List[str], options: dict) -> Tuple[int, str]:
        """排序文本行"""
        reverse = 'r' in options
        numeric = 'n' in options

        if not args:
            return 1, "sort: missing input file"

        content = self.fs.read_file(args[0])
        if content is None:
            return 1, f"sort: {args[0]}: No such file or directory"

        lines = self._split_content(content)
        if numeric:
            # 数值排序（提取每行开头的数字）
            def num_key(line):
                match = re.match(r'\s*(-?\d+)', line)
                return (0, int(match.group(1))) if match else (1, 0)
            lines.sort(key=num_key, reverse=reverse)
        else:
            lines.sort(reverse=reverse)

        return 0, '\n'.join(lines)

    def cmd_uniq(self, args: List[str], options: dict) -> Tuple[int, str]:
        """去除相邻重复行"""
        if not args:
            return 1, "uniq: missing input file"

        content = self.fs.read_file(args[0])
        if content is None:
            return 1, f"uniq: {args[0]}: No such file or directory"

        lines = self._split_content(content)
        result = []
        for line in lines:
            if not result or result[-1] != line:
                result.append(line)

        return 0, '\n'.join(result)

    def cmd_nl(self, args: List[str], options: dict) -> Tuple[int, str]:
        """带行号显示文件"""
        if not args:
            return 1, "nl: missing file operand"

        content = self.fs.read_file(args[0])
        if content is None:
            return 1, f"nl: {args[0]}: No such file or directory"

        lines = self._split_content(content)
        numbered = [f"{i+1:6d}\t{line}" for i, line in enumerate(lines)]
        return 0, '\n'.join(numbered)

    def cmd_tee(self, args: List[str], options: dict) -> Tuple[int, str]:
        """将输入写入文件并显示"""
        if not args:
            return 1, "tee: missing file operand"

        # 简化实现：从文件读取（无管道输入支持时）
        # 实际用法: echo hello | tee file.txt —— 管道还不支持，这里直接说明
        return 1, "tee: 需要管道输入，如: echo hello | tee file.txt（管道功能暂未支持）"

    # ------------------------------------------------------------------
    # 查找和信息命令
    # ------------------------------------------------------------------

    def cmd_find(self, args: List[str], options: dict) -> Tuple[int, str]:
        """查找文件"""
        # -name/-type/-maxdepth 由解析器处理为 options
        start = args[0] if args else '.'
        name_pattern = options.get('name')
        file_type = options.get('type')  # f=文件, d=目录
        try:
            max_depth = int(options.get('maxdepth', 99))
        except (TypeError, ValueError):
            max_depth = 99

        base = self._resolve_path(start)
        if not base.exists():
            return 1, f"find: {start}: No such file or directory"

        results = []

        def walk(p: pathlib.Path, depth: int):
            if depth > max_depth:
                return
            try:
                for item in p.iterdir():
                    is_dir = item.is_dir()
                    # 类型过滤
                    if file_type == 'f' and is_dir:
                        continue
                    if file_type == 'd' and not is_dir:
                        continue
                    # 名字过滤
                    if name_pattern and not fnmatch.fnmatch(item.name, name_pattern):
                        # 目录仍需继续遍历
                        if is_dir:
                            walk(item, depth + 1)
                        continue

                    results.append(str(item))
                    if is_dir:
                        walk(item, depth + 1)
            except PermissionError:
                pass

        walk(base, 0)
        if results:
            return 0, '\n'.join(results)
        return 0, ''

    def cmd_tree(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示目录树"""
        start = args[0] if args else '.'
        show_hidden = 'a' in options
        max_depth = 5

        base = self._resolve_path(start)
        if not base.exists():
            return 1, f"tree: {start}: No such file or directory"

        output = [str(base)]

        def walk(p: pathlib.Path, prefix: str, depth: int):
            if depth > max_depth:
                output.append(prefix + "└── ...")
                return
            try:
                items = sorted(
                    [i for i in p.iterdir() if show_hidden or not i.name.startswith('.')],
                    key=lambda x: (not x.is_dir(), x.name.lower())
                )
            except PermissionError:
                return

            for idx, item in enumerate(items):
                is_last = idx == len(items) - 1
                connector = "└── " if is_last else "├── "
                is_dir = item.is_dir()
                display = item.name + ('/' if is_dir else '')
                output.append(prefix + connector + display)
                if is_dir:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    walk(item, next_prefix, depth + 1)

        walk(base, '', 0)
        return 0, '\n'.join(output)

    def cmd_stat(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示文件详细信息"""
        if not args:
            return 1, "stat: missing file operand"

        info = self.fs.get_file_info(args[0])
        if info is None:
            return 1, f"stat: {args[0]}: No such file or directory"

        modified = datetime.datetime.fromtimestamp(info['modified']).strftime('%Y-%m-%d %H:%M:%S')
        output = [
            f"  文件: {args[0]}",
            f"  大小: {self._format_bytes(info['size'])} ({info['size']} 字节)",
            f"  类型: {'目录' if info['is_dir'] else '文件'}",
            f"  修改: {modified}",
            f"  路径: {self.fs.getcwd()}/{args[0]}",
        ]
        return 0, '\n'.join(output)

    def cmd_du(self, args: List[str], options: dict) -> Tuple[int, str]:
        """计算目录/文件大小"""
        target = args[0] if args else '.'
        human_readable = 'h' in options

        base = self._resolve_path(target)
        if not base.exists():
            return 1, f"du: {target}: No such file or directory"

        def get_size(p: pathlib.Path) -> int:
            if p.is_file():
                return p.stat().st_size
            total = 0
            try:
                for item in p.iterdir():
                    total += get_size(item)
            except PermissionError:
                pass
            return total

        size = get_size(base)
        if human_readable:
            return 0, f"{self._format_bytes(size)}\t{target}"
        return 0, f"{size}\t{target}"

    def cmd_df(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示磁盘使用情况"""
        human_readable = 'h' in options
        target = args[0] if args else self.fs.getcwd()

        try:
            usage = shutil.disk_usage(target)
        except Exception:
            return 1, f"df: {target}: cannot determine disk usage"

        if human_readable:
            output = [
                f"文件系统    总大小    已用    可用    使用率",
                f"{target:<10} {self._format_bytes(usage.total):>8} "
                f"{self._format_bytes(usage.used):>8} "
                f"{self._format_bytes(usage.free):>8} "
                f"{usage.used * 100 // usage.total:>5}%"
            ]
        else:
            output = [
                f"文件系统    总大小    已用    可用    使用率",
                f"{target:<10} {usage.total:>10} {usage.used:>10} "
                f"{usage.free:>10} {usage.used * 100 // usage.total:>5}%"
            ]
        return 0, '\n'.join(output)

    def cmd_which(self, args: List[str], options: dict) -> Tuple[int, str]:
        """查找命令路径"""
        if not args:
            return 1, "which: missing command"

        output = []
        for cmd in args:
            path = self.builtin.process_manager.which(cmd) if hasattr(self.builtin, 'process_manager') else None
            if path is None:
                # 尝试内置命令
                if cmd in self.builtin.commands:
                    path = f"builtin: {cmd}"
                else:
                    path = None
            if path:
                output.append(path)
            else:
                output.append(f"which: no {cmd} in PATH")

        return 0, '\n'.join(output)

    # ------------------------------------------------------------------
    # 系统命令
    # ------------------------------------------------------------------

    def cmd_ps(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示进程列表"""
        try:
            if self.platform.is_windows():
                try:
                    result = subprocess.run(
                        ['tasklist'], capture_output=True, text=True, shell=False
                    )
                except Exception:
                    # 回退: 使用 wmic
                    result = subprocess.run(
                        ['wmic', 'process', 'get', 'name,processid'],
                        capture_output=True, text=True, shell=False
                    )
            else:
                result = subprocess.run(
                    ['ps', 'aux'], capture_output=True, text=True, shell=False
                )
            output = result.stdout + result.stderr
            if result.returncode != 0 and not output:
                output = f"ps: 无法获取进程列表 (exit code {result.returncode})"
            return result.returncode, output
        except Exception as e:
            return 1, f"ps: {e}"

    def cmd_kill(self, args: List[str], options: dict) -> Tuple[int, str]:
        """终止进程"""
        if not args:
            return 1, "kill: missing process id"

        force = 'f' in options
        pids = [a for a in args if a.isdigit()]
        if not pids:
            return 1, "kill: no valid process id"

        output = []
        for pid in pids:
            try:
                if self.platform.is_windows():
                    if force:
                        result = subprocess.run(
                            ['taskkill', '/PID', pid, '/F'],
                            capture_output=True, text=True, shell=False
                        )
                    else:
                        result = subprocess.run(
                            ['taskkill', '/PID', pid],
                            capture_output=True, text=True, shell=False
                        )
                else:
                    if force:
                        result = subprocess.run(
                            ['kill', '-9', pid],
                            capture_output=True, text=True, shell=False
                        )
                    else:
                        result = subprocess.run(
                            ['kill', pid],
                            capture_output=True, text=True, shell=False
                        )
                out = result.stdout.strip()
                err = result.stderr.strip()
                if out:
                    output.append(out)
                if err:
                    output.append(err)
            except Exception as e:
                output.append(f"kill: {pid}: {e}")

        return 0, '\n'.join(output) if output else ''

    def cmd_sleep(self, args: List[str], options: dict) -> Tuple[int, str]:
        """延迟指定秒数"""
        if not args:
            return 1, "sleep: missing operand"

        try:
            seconds = float(args[0])
        except ValueError:
            return 1, f"sleep: invalid time interval '{args[0]}'"

        if seconds < 0:
            return 1, "sleep: time interval cannot be negative"

        if seconds > 60:
            return 1, f"sleep: {seconds} seconds too long (max 60)"

        time.sleep(seconds)
        return 0, ''

    def cmd_uptime(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示系统运行时间"""
        try:
            if self.platform.is_windows():
                import ctypes
                millis = ctypes.windll.kernel32.GetTickCount64()
                seconds = millis // 1000
            else:
                # 从 /proc/uptime 读取
                with open('/proc/uptime', 'r') as f:
                    seconds = int(float(f.read().split()[0]))
        except Exception:
            # 回退: 尝试系统 uptime 命令
            try:
                result = subprocess.run(['uptime'], capture_output=True, text=True)
                return result.returncode, result.stdout.strip()
            except Exception:
                return 1, "uptime: cannot determine system uptime"

        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)
        return 0, f"up {days} days, {hours:02d}:{mins:02d}:{secs:02d}"

    def cmd_uname(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示系统信息"""
        all_info = 'a' in options

        # 使用 sys 和 socket 获取信息（避免与标准库 platform 混淆）
        import sys as sys_module
        import socket

        system = self.platform.system
        node = socket.gethostname()
        release = getattr(sys_module, 'winver', '') if system == 'windows' else ''
        machine = self._get_machine_arch()

        if all_info:
            parts = [system, node]
            if release:
                parts.append(release)
            parts.append(machine)
            return 0, ' '.join(parts)
        elif system == 'windows':
            return 0, f"{system} {release}".strip()
        else:
            return 0, f"{system}"

    def _get_machine_arch(self) -> str:
        """获取机器架构"""
        try:
            import struct
            return 'x86_64' if struct.calcsize('P') == 8 else 'x86'
        except Exception:
            return 'unknown'

    def cmd_id(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示用户身份信息"""
        import getpass
        username = getpass.getuser()

        if self.platform.is_unix_like():
            try:
                result = subprocess.run(['id'], capture_output=True, text=True)
                return result.returncode, result.stdout.strip()
            except Exception:
                pass

        # Windows 或回退
        try:
            import socket
            host = socket.gethostname()
            return 0, f"uid=({username}) gid=({username}) groups=({username}) host={host}"
        except Exception:
            return 0, f"uid=({username})"

    # ------------------------------------------------------------------
    # 工具命令
    # ------------------------------------------------------------------

    def cmd_base64(self, args: List[str], options: dict) -> Tuple[int, str]:
        """Base64 编码/解码"""
        decode = 'd' in options or 'decode' in options

        if not args:
            return 1, "base64: missing input"

        # 参数可能是文本或文件路径
        text = args[0]
        if self.fs.is_file(text):
            text = self.fs.read_file(text) or ''

        try:
            if decode:
                result = base64.b64decode(text.encode('utf-8')).decode('utf-8', errors='replace')
            else:
                result = base64.b64encode(text.encode('utf-8')).decode('utf-8')
            return 0, result
        except Exception as e:
            return 1, f"base64: {e}"

    def _hash_file(self, args: List[str], algo: str) -> Tuple[int, str]:
        """计算文件哈希"""
        if not args:
            return 1, f"{algo}: missing file operand"

        content = self.fs.read_file(args[0])
        if content is None:
            return 1, f"{algo}: {args[0]}: No such file or directory"

        h = hashlib.new(algo)
        h.update(content.encode('utf-8', errors='ignore'))
        return 0, f"{h.hexdigest()}  {args[0]}"

    def cmd_md5sum(self, args: List[str], options: dict) -> Tuple[int, str]:
        """计算 MD5 哈希"""
        return self._hash_file(args, 'md5')

    def cmd_sha1sum(self, args: List[str], options: dict) -> Tuple[int, str]:
        """计算 SHA1 哈希"""
        return self._hash_file(args, 'sha1')

    def cmd_sha256sum(self, args: List[str], options: dict) -> Tuple[int, str]:
        """计算 SHA256 哈希"""
        return self._hash_file(args, 'sha256')

    def cmd_seq(self, args: List[str], options: dict) -> Tuple[int, str]:
        """生成数字序列"""
        if len(args) == 1:
            end = int(args[0])
            start, step = 1, 1
        elif len(args) == 2:
            start, end = int(args[0]), int(args[1])
            step = 1
        elif len(args) == 3:
            start, end = int(args[0]), int(args[1])
            step = int(args[2])
        else:
            return 1, "seq: usage: seq [start] end [step]"

        if step == 0:
            return 1, "seq: step cannot be zero"

        try:
            nums = list(range(start, end + (1 if step > 0 else -1), step))
            return 0, '\n'.join(str(n) for n in nums)
        except Exception as e:
            return 1, f"seq: {e}"

    def cmd_yes(self, args: List[str], options: dict) -> Tuple[int, str]:
        """重复输出字符串（最多 20 次，防止刷屏）"""
        text = ' '.join(args) if args else 'y'
        limit = int(options.get('limit', 20)) if isinstance(options.get('limit'), str) else 20
        return 0, '\n'.join([text] * limit)

    def cmd_true(self, args: List[str], options: dict) -> Tuple[int, str]:
        """返回成功状态"""
        return 0, ''

    def cmd_false(self, args: List[str], options: dict) -> Tuple[int, str]:
        """返回失败状态"""
        return 1, ''

    def cmd_man(self, args: List[str], options: dict) -> Tuple[int, str]:
        """显示命令帮助（简化版 man）"""
        if not args:
            return 1, "man: missing command name"

        cmd = args[0]
        if cmd not in self.builtin.commands:
            return 1, f"man: no manual entry for {cmd}"

        # 简单帮助字典
        docs = {
            'sudo': "sudo <command> [args...] - 以管理员/root 权限执行命令",
            'head': "head [-n N] <file> - 显示文件前 N 行 (默认 10)",
            'tail': "tail [-n N] <file> - 显示文件后 N 行 (默认 10)",
            'grep': "grep [-i] [-n] [-r] [-c] <pattern> [file|dir...] - 搜索文本",
            'wc': "wc [-l] [-w] [-c] [file...] - 统计行数/字数/字节数",
            'sort': "sort [-r] [-n] <file> - 排序文本行",
            'uniq': "uniq <file> - 去除相邻重复行",
            'nl': "nl <file> - 带行号显示文件",
            'find': "find [path] [-name pattern] [-type f|d] [-maxdepth N] - 查找文件",
            'tree': "tree [path] [-a] - 显示目录树",
            'stat': "stat <file> - 显示文件详细信息",
            'du': "du [-h] [path] - 计算目录/文件大小",
            'df': "df [-h] [path] - 显示磁盘使用情况",
            'which': "which <command> - 查找命令路径",
            'ps': "ps - 显示进程列表",
            'kill': "kill [-f] <pid> - 终止进程",
            'sleep': "sleep <seconds> - 延迟指定秒数",
            'uptime': "uptime - 显示系统运行时间",
            'uname': "uname [-a] - 显示系统信息",
            'id': "id - 显示用户身份信息",
            'base64': "base64 [-d] <text|file> - Base64 编码/解码",
            'md5sum': "md5sum <file> - 计算 MD5 哈希",
            'sha1sum': "sha1sum <file> - 计算 SHA1 哈希",
            'sha256sum': "sha256sum <file> - 计算 SHA256 哈希",
            'seq': "seq [start] end [step] - 生成数字序列",
            'yes': "yes [text] - 重复输出文本",
            'true': "true - 返回成功状态",
            'false': "false - 返回失败状态",
            'man': "man <command> - 显示命令帮助",
        }

        doc = docs.get(cmd, f"{cmd} - 内置命令（查看 help 获取完整列表）")
        return 0, f"NAME\n    {cmd}\n\nSYNOPSIS\n    {doc}"

    def cmd_calc(self, args: List[str], options: Dict[str, Any]) -> Tuple[int, str]:
        if not args:
            return 1, self.theme.error("用法: calc <表达式>") if self.theme else "用法: calc <表达式>"
        
        expr = " ".join(args)
        try:
            # 安全求值：只允许数字和运算符
            allowed = set("0123456789+-*/.() ")
            if not all(c in allowed for c in expr):
                return 1, self.theme.error("表达式包含非法字符") if self.theme else "表达式包含非法字符"
            result = eval(expr, {"__builtins__": {}}, {})
            return 0, str(result)
        except Exception as e:
            return 1, self.theme.error(f"计算错误: {e}") if self.theme else f"计算错误: {e}"