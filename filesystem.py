"""
文件系统操作模块
不使用 os 库，使用 pathlib 和其他标准库
"""

import pathlib
import shutil
from typing import List, Optional, Tuple
from kplatform import Platform

class FileSystem:
    """文件系统操作封装"""

    def __init__(self, platform: Platform):
        self.platform = platform
        self.current_dir = pathlib.Path.cwd()

    def getcwd(self) -> str:
        """获取当前工作目录"""
        return str(self.current_dir)

    def chdir(self, path: str) -> bool:
        """改变当前工作目录"""
        try:
            new_path = self._resolve_path(path)
            if new_path.is_dir():
                self.current_dir = new_path.resolve()
                return True
            return False
        except Exception:
            return False

    def _resolve_path(self, path: str) -> pathlib.Path:
        """解析路径，支持相对路径和绝对路径"""
        p = pathlib.Path(path)
        if p.is_absolute():
            return p
        return (self.current_dir / p).resolve()

    def list_dir(self, path: str = None, show_hidden: bool = False) -> List[Tuple[str, str]]:
        """
        列出目录内容
        返回: [(name, type), ...]
        type: 'dir', 'file', 'link'
        """
        target_path = self._resolve_path(path) if path else self.current_dir

        if not target_path.exists():
            return []

        # 目标是文件时，列出该文件本身（与 GNU ls 行为一致，v2.0 修复）
        if target_path.is_file():
            if not show_hidden and target_path.name.startswith('.'):
                return []
            return [(target_path.name, 'file')]

        try:
            items = []
            for item in target_path.iterdir():
                # 跳过隐藏文件
                if not show_hidden and item.name.startswith('.'):
                    continue

                if item.is_dir():
                    items.append((item.name, 'dir'))
                elif item.is_file():
                    items.append((item.name, 'file'))
                elif item.is_symlink():
                    items.append((item.name, 'link'))

            return sorted(items, key=lambda x: (x[1] != 'dir', x[0]))
        except Exception:
            return []

    def exists(self, path: str) -> bool:
        """检查路径是否存在"""
        try:
            return self._resolve_path(path).exists()
        except Exception:
            return False

    def is_dir(self, path: str) -> bool:
        """检查是否是目录"""
        try:
            return self._resolve_path(path).is_dir()
        except Exception:
            return False

    def is_file(self, path: str) -> bool:
        """检查是否是文件"""
        try:
            return self._resolve_path(path).is_file()
        except Exception:
            return False

    def mkdir(self, path: str, parents: bool = False) -> bool:
        """创建目录"""
        try:
            target_path = self._resolve_path(path)
            if parents:
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.mkdir(exist_ok=True)
            return True
        except Exception:
            return False

    def remove_file(self, path: str) -> bool:
        """删除文件"""
        try:
            target_path = self._resolve_path(path)
            if target_path.is_file():
                target_path.unlink()
                return True
            return False
        except Exception:
            return False

    def remove_dir(self, path: str, recursive: bool = False) -> bool:
        """删除目录"""
        try:
            target_path = self._resolve_path(path)
            if not target_path.is_dir():
                return False

            if recursive:
                shutil.rmtree(target_path)
            else:
                target_path.rmdir()
            return True
        except Exception:
            return False

    def copy_file(self, src: str, dst: str) -> bool:
        """复制文件"""
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)
            shutil.copy2(src_path, dst_path)
            return True
        except Exception:
            return False

    def copy_dir(self, src: str, dst: str) -> bool:
        """复制目录"""
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                return True
            return False
        except Exception:
            return False

    def move(self, src: str, dst: str) -> bool:
        """移动文件或目录"""
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)
            shutil.move(str(src_path), str(dst_path))
            return True
        except Exception:
            return False

    def read_file(self, path: str) -> Optional[str]:
        """读取文件内容"""
        try:
            target_path = self._resolve_path(path)
            if target_path.is_file():
                return target_path.read_text(encoding='utf-8', errors='ignore')
            return None
        except Exception:
            return None

    def write_file(self, path: str, content: str, append: bool = False) -> bool:
        """写入文件 (append=True 时追加内容)"""
        try:
            target_path = self._resolve_path(path)
            mode = 'a' if append else 'w'
            with target_path.open(mode, encoding='utf-8', errors='ignore') as f:
                f.write(content)
            return True
        except Exception:
            return False

    def get_file_info(self, path: str) -> Optional[dict]:
        """获取文件信息"""
        try:
            target_path = self._resolve_path(path)
            if not target_path.exists():
                return None

            stat = target_path.stat()
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'is_dir': target_path.is_dir(),
                'is_file': target_path.is_file(),
                'is_symlink': target_path.is_symlink(),
            }
        except Exception:
            return None

    def join_path(self, *parts) -> str:
        """连接路径"""
        return str(pathlib.Path(*parts))

    def get_parent(self, path: str) -> str:
        """获取父目录"""
        return str(self._resolve_path(path).parent)

    def get_basename(self, path: str) -> str:
        """获取文件名"""
        return pathlib.Path(path).name

    def get_dirname(self, path: str) -> str:
        """获取目录名"""
        return str(pathlib.Path(path).parent)