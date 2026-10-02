"""
命令解析器
解析用户输入的命令
"""

import re
import shlex
from typing import List, Dict, Optional, Tuple

class CommandParser:
    """命令解析器"""

    def __init__(self):
        self.aliases: Dict[str, str] = {
            'll': 'ls -la',
            'cls': 'clear',
            'dir': 'ls',
            'copy': 'cp',
            'move': 'mv',
            'del': 'rm',
            'md': 'mkdir',
            'rd': 'rmdir',
            'type': 'cat',
        }

    def expand_alias(self, input_str: str) -> str:
        """展开别名（返回替换后的完整命令行）"""
        stripped = input_str.strip()
        if not stripped or stripped.startswith('#'):
            return stripped
        first_word = stripped.split()[0] if stripped.split() else ''
        if first_word in self.aliases:
            return self.aliases[first_word] + stripped[len(first_word):]
        return stripped

    def raw_split(self, input_str: str) -> Tuple[str, List[str]]:
        """
        别名展开后切分，保留原始参数顺序（含所有选项）。
        用于把参数完整透传给系统命令，避免选项被解析丢弃。
        返回: (命令, 原始参数列表)
        """
        expanded = self.expand_alias(input_str)
        if not expanded:
            return '', []
        try:
            parts = shlex.split(expanded)
        except ValueError:
            parts = expanded.split()
        if not parts:
            return '', []
        return parts[0], parts[1:]

    def parse(self, input_str: str) -> Tuple[str, List[str], Dict[str, str]]:
        """
        解析命令行输入
        返回: (命令, 参数列表, 选项字典)
        """
        # 去除空白和注释
        input_str = input_str.strip()
        if not input_str or input_str.startswith('#'):
            return '', [], {}

        # 处理别名
        input_str = self.expand_alias(input_str)

        # 使用 shlex 分割命令和参数（支持引号）
        try:
            parts = shlex.split(input_str)
        except ValueError:
            # 如果引号不匹配，使用简单的分割
            parts = input_str.split()

        if not parts:
            return '', [], {}

        command = parts[0]
        args = []
        options = {}

        # 解析参数和选项
        i = 1
        while i < len(parts):
            part = parts[i]

            # 处理选项 --option=value 或 --option value
            if part.startswith('--'):
                if '=' in part:
                    key, value = part[2:].split('=', 1)
                    options[key] = value
                else:
                    key = part[2:]
                    if i + 1 < len(parts) and not parts[i + 1].startswith('-'):
                        options[key] = parts[i + 1]
                        i += 1
                    else:
                        options[key] = True
            # 处理短选项 -a / -abc / -name
            elif part.startswith('-') and len(part) > 1:
                opts = part[1:]
                # 已知的单横线长选项（如 find 的 -name/-type/-maxdepth）
                # 整体作为一个选项名，不拆分成单个字符
                if opts in ('name', 'type', 'maxdepth', 'mindepth', 'exclude',
                            'include', 'ignore', 'color', 'help', 'version'):
                    key = opts
                    if i + 1 < len(parts) and not parts[i + 1].startswith('-'):
                        options[key] = parts[i + 1]
                        i += 1
                    else:
                        options[key] = True
                else:
                    # 组合短选项 -abc → a, b, c 都是布尔标志
                    # 短选项一律作为布尔标志，不吞后面的参数
                    # （如 echo -n text 中 text 是位置参数，ls -l /tmp 中 /tmp 是位置参数）
                    for opt in opts:
                        options[opt] = True
            else:
                # 普通参数
                args.append(part)

            i += 1

        return command, args, options

    def add_alias(self, name: str, command: str) -> bool:
        """添加别名"""
        if not name or not command:
            return False
        self.aliases[name] = command
        return True

    def remove_alias(self, name: str) -> bool:
        """删除别名"""
        if name in self.aliases:
            del self.aliases[name]
            return True
        return False

    def list_aliases(self) -> Dict[str, str]:
        """列出所有别名"""
        return self.aliases.copy()

    def expand_wildcards(self, pattern: str, filesystem) -> List[str]:
        """展开通配符"""
        import pathlib

        if '*' not in pattern and '?' not in pattern:
            return [pattern]

        try:
            p = pathlib.Path(pattern)
            parent = p.parent if p.parent != pathlib.Path('.') else pathlib.Path.cwd()
            name = p.name

            matches = []
            for item in parent.glob(name):
                matches.append(str(item))

            return sorted(matches)
        except Exception:
            return [pattern]

    def parse_pipeline(self, input_str: str) -> List[str]:
        """解析管道命令"""
        return [cmd.strip() for cmd in input_str.split('|')]

    def parse_redirect(self, args: List[str]) -> Tuple[List[str], Optional[str], Optional[str]]:
        """
        解析重定向
        返回: (命令参数, 输出重定向文件, 输入重定向文件)
        """
        output_file = None
        input_file = None
        clean_args = []

        i = 0
        while i < len(args):
            arg = args[i]

            # 输出重定向 >
            if arg == '>':
                if i + 1 < len(args):
                    output_file = args[i + 1]
                    i += 2
                    continue
            # 追加输出重定向 >>
            elif arg == '>>':
                if i + 1 < len(args):
                    output_file = args[i + 1]
                    # 标记为追加模式
                    output_file = f'>>{output_file}'
                    i += 2
                    continue
            # 输入重定向 <
            elif arg == '<':
                if i + 1 < len(args):
                    input_file = args[i + 1]
                    i += 2
                    continue

            clean_args.append(arg)
            i += 1

        return clean_args, output_file, input_file