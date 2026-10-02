"""
KShell - 系统命令解析模块 (v2.0)
扫描系统 PATH，使系统命令可以被直接调用。

设计要点:
  1. 启动时扫描一次 PATH 建立索引；未命中时按间隔惰性重扫（支持新安装的命令）
  2. Windows 下识别 PATHEXT 扩展名（.exe/.cmd/.bat/.com 等）
  3. Windows 下识别 cmd.exe 内部命令（dir/ver/title 等，磁盘上无对应可执行文件）
  4. 提供遮蔽报告：哪些系统命令被 KShell 内置命令优先接管
  5. 不使用 os 库，路径操作全部基于 pathlib
"""

import pathlib
import time
from typing import Dict, List, Optional

# Windows cmd.exe 内部命令：磁盘上没有对应可执行文件，必须通过 cmd /c 调用
WINDOWS_CMD_BUILTINS = {
    'assoc', 'break', 'call', 'chdir', 'cls', 'color', 'copy', 'date',
    'del', 'dir', 'echo', 'endlocal', 'erase', 'exit', 'for', 'ftype',
    'goto', 'if', 'md', 'mkdir', 'mklink', 'move', 'path', 'pause', 'popd',
    'prompt', 'pushd', 'rd', 'rem', 'ren', 'rename', 'rmdir', 'set',
    'setlocal', 'shift', 'start', 'time', 'title', 'type', 'ver', 'verify',
    'vol',
}

# Windows 默认可执行扩展名（PATHEXT 缺失时使用）
DEFAULT_PATHEXT = ['.com', '.exe', '.bat', '.cmd']

# 未命中时的重新扫描间隔（秒），用于发现新安装的命令
RESCAN_INTERVAL = 5.0


class SystemCommand:
    """一条系统命令的描述"""

    __slots__ = ('name', 'path', 'kind')

    def __init__(self, name: str, path: str, kind: str = 'executable'):
        self.name = name
        self.path = path
        self.kind = kind  # 'executable' | 'cmd_builtin'

    def __repr__(self) -> str:
        return f"<SystemCommand {self.name} [{self.kind}] {self.path}>"


class SystemCommandResolver:
    """系统 PATH 命令解析器"""

    def __init__(self, platform, env: Optional[Dict[str, str]] = None):
        self.platform = platform
        self.env: Dict[str, str] = env if env is not None else {}
        self._index: Dict[str, SystemCommand] = {}
        self._last_scan = 0.0

    # ------------------------------------------------------------------
    # PATH 相关
    # ------------------------------------------------------------------

    def path_entries(self) -> List[str]:
        """返回 PATH 中的目录列表（保持原始顺序）"""
        raw = self._get_path_var()
        if not raw:
            return []
        sep = self.platform.get_env_separator()
        return [p.strip().strip('"') for p in raw.split(sep) if p.strip()]

    def _get_path_var(self) -> str:
        """读取 PATH 环境变量（Windows 下大小写不敏感）"""
        for key in ('PATH', 'Path', 'path'):
            if key in self.env:
                return self.env[key]
        return ''

    def _pathext(self) -> List[str]:
        """Windows 可执行扩展名列表"""
        raw = self.env.get('PATHEXT', '') or self.env.get('PathExt', '')
        exts = [e.strip().lower() for e in raw.split(';') if e.strip()]
        return exts or list(DEFAULT_PATHEXT)

    # ------------------------------------------------------------------
    # 扫描与索引
    # ------------------------------------------------------------------

    def refresh(self) -> int:
        """重新扫描 PATH，返回索引到的命令数量"""
        index: Dict[str, SystemCommand] = {}
        is_windows = self.platform.is_windows()
        exts = self._pathext() if is_windows else None

        for directory in self.path_entries():
            try:
                base = pathlib.Path(directory)
                if not base.is_dir():
                    continue
                entries = list(base.iterdir())
            except (OSError, PermissionError, ValueError):
                # 目录不存在或无权限，跳过
                continue

            for item in entries:
                try:
                    if not item.is_file():
                        continue
                except OSError:
                    continue

                if is_windows:
                    suffix = item.suffix.lower()
                    if suffix not in exts:
                        continue
                    name = item.name[:len(item.name) - len(item.suffix)]
                    key = name.lower()
                else:
                    if not self._is_executable(item):
                        continue
                    name = item.name
                    key = name

                # PATH 中靠前的目录优先
                if key and key not in index:
                    index[key] = SystemCommand(name, str(item))

        # Windows cmd 内部命令（不覆盖真实可执行文件）
        if is_windows:
            for name in WINDOWS_CMD_BUILTINS:
                index.setdefault(name, SystemCommand(name, 'cmd.exe', 'cmd_builtin'))

        self._index = index
        self._last_scan = time.monotonic()
        return len(index)

    @staticmethod
    def _is_executable(item: pathlib.Path) -> bool:
        """判断文件是否具有可执行权限（Unix）"""
        try:
            return bool(item.stat().st_mode & 0o111)
        except OSError:
            return False

    def _key(self, name: str) -> str:
        return name.lower() if self.platform.is_windows() else name

    def resolve(self, name: str) -> Optional[SystemCommand]:
        """解析命令名，返回系统命令描述或 None"""
        if not name:
            return None
        if not self._index:
            self.refresh()
        cmd = self._index.get(self._key(name))
        if cmd is not None:
            return cmd
        # 未命中：按间隔惰性重扫，支持运行期间新安装的命令
        if time.monotonic() - self._last_scan > RESCAN_INTERVAL:
            self.refresh()
            return self._index.get(self._key(name))
        return None

    def exists(self, name: str) -> bool:
        return self.resolve(name) is not None

    def path_of(self, name: str) -> Optional[str]:
        cmd = self.resolve(name)
        return cmd.path if cmd else None

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def count(self) -> int:
        if not self._index:
            self.refresh()
        return len(self._index)

    def all_names(self) -> List[str]:
        if not self._index:
            self.refresh()
        return sorted(self._index.keys())

    def search(self, keyword: str) -> List[SystemCommand]:
        """按关键字搜索系统命令（子串匹配，忽略大小写）"""
        if not self._index:
            self.refresh()
        kw = keyword.lower()
        found = [c for k, c in self._index.items() if kw in k]
        found.sort(key=lambda c: c.name.lower())
        return found

    def shadowed(self, builtin_names) -> List[tuple]:
        """
        找出被 KShell 内置命令遮蔽的系统命令。
        返回: [(命令名, 系统命令描述), ...] 按名称排序
        """
        if not self._index:
            self.refresh()
        result = []
        for name in builtin_names:
            cmd = self._index.get(self._key(name))
            if cmd is not None:
                result.append((name, cmd))
        result.sort(key=lambda pair: pair[0].lower())
        return result
