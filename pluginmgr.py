"""
KShell - 插件系统核心 (v2.1)

插件 = 一个目录，包含：
    plugin.json   元数据、命令声明、默认配置
    plugin.py     Python 实现（函数接收 (args, options, ctx)）

设计要点:
  · 插件目录按优先级搜索：打包内置 → 项目 plugins/ → 可执行文件同级 → 用户主目录
  · plugin.json 严格校验，非法插件只报错不崩溃
  · 插件函数异常被隔离，单个插件出错不影响 KShell 本体
  · 启用状态与插件配置持久化到 kshell_config.json 的 plugins 段
  · 支持热重载（plugin reload）与脚手架生成（plugin new）
"""

import importlib.util
import json
import pathlib
import re
import sys
import traceback
import types
from typing import Any, Callable, Dict, List, Optional, Tuple

from version import VERSION, check_requirement

MANIFEST_NAME = 'plugin.json'
ENTRY_NAME = 'plugin.py'

# 插件名合法字符
NAME_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')
# 命令名合法字符
CMD_PATTERN = re.compile(r'^[A-Za-z0-9_.-]+$')

# ----------------------------------------------------------------------
# 插件可用的标准库模块清单
#
# 为什么需要它：插件是运行时动态加载的（compile + exec），PyInstaller 的
# 静态分析看不到插件里的 import，因此打包时不会带上这些模块，
# 插件在 exe 里会报 ModuleNotFoundError。
# kshell.spec 会导入本清单并加入 hiddenimports，保证打包后插件可用。
# ----------------------------------------------------------------------
PLUGIN_STDLIB_HINTS = [
    # 基础
    'sys', 'os', 'io', 're', 'json', 'csv', 'math', 'cmath', 'statistics',
    'decimal', 'fractions', 'random', 'secrets', 'string', 'textwrap',
    'pprint', 'copy', 'dataclasses', 'enum', 'typing', 'abc', 'operator',
    # 时间
    'time', 'datetime', 'calendar',
    # 文件与路径
    'pathlib', 'shutil', 'glob', 'fnmatch', 'tempfile', 'filecmp', 'fileinput',
    'zipfile', 'tarfile', 'gzip', 'bz2', 'lzma',
    # 数据结构与算法
    'collections', 'itertools', 'functools', 'heapq', 'bisect', 'array',
    'queue', 'struct', 'difflib',
    # 文本与编码
    'unicodedata', 'codecs', 'locale', 'html', 'xml.etree.ElementTree',
    # 哈希与编码
    'hashlib', 'hmac', 'base64', 'binascii', 'uuid',
    # 系统与进程
    'platform', 'getpass', 'socket', 'subprocess', 'signal', 'multiprocessing',
    'threading', 'concurrent.futures', 'shlex', 'sysconfig',
    # 网络
    'urllib.request', 'urllib.parse', 'urllib.error', 'http.client',
    'http.server', 'email', 'smtplib', 'ssl',
    # 其它常用
    'argparse', 'logging', 'warnings', 'traceback', 'inspect', 'ast',
    'contextlib', 'weakref', 'gc', 'atexit', 'ctypes', 'configparser',
]


# ======================================================================
# 数据结构
# ======================================================================

class PluginError(Exception):
    """插件相关错误"""


class PluginCommand:
    """插件声明的单条命令"""

    __slots__ = ('name', 'function', 'usage', 'description', 'aliases')

    def __init__(self, name: str, function: str = '', usage: str = '',
                 description: str = '', aliases: Optional[List[str]] = None):
        self.name = name
        self.function = function or ('cmd_' + name.replace('-', '_').replace('.', '_'))
        self.usage = usage
        self.description = description
        self.aliases = aliases or []


class Plugin:
    """已加载（或加载失败）的插件"""

    def __init__(self, path: pathlib.Path):
        self.path = path
        self.name = path.name
        self.version = '0.0.0'
        self.author = ''
        self.description = ''
        self.homepage = ''
        self.requires = ''
        self.manifest: Dict[str, Any] = {}
        self.commands: List[PluginCommand] = []
        self.settings_defaults: Dict[str, Any] = {}
        self.module = None
        self.ctx: Optional['PluginContext'] = None
        self.loaded = False
        self.load_error = ''
        self.registered: List[str] = []

    # -------------------------------------------------- 配置读取

    def config(self, manager) -> Dict[str, Any]:
        """默认配置 + 用户覆盖"""
        merged = dict(self.settings_defaults)
        merged.update(manager.stored_config(self.name))
        return merged

    def __repr__(self) -> str:
        state = 'ok' if self.loaded else ('error' if self.load_error else 'off')
        return f"<Plugin {self.name} v{self.version} [{state}]>"


class PluginContext:
    """
    传给插件函数的上下文（第三个参数）

    插件里用到的所有能力都从这里取，避免插件直接依赖 KShell 内部实现。
    """

    def __init__(self, manager: 'PluginManager', plugin: Plugin):
        self._manager = manager
        self._plugin = plugin
        self.logs: List[str] = []

        # 常用对象
        self.plugin = plugin
        self.name = plugin.name
        self.version = plugin.version
        self.dir = plugin.path
        self.fs = manager.fs
        self.platform = manager.platform
        self.settings = manager.settings
        self.theme = manager.theme
        self.parser = manager.parser

    # -------------------------------------------------- 插件配置

    def config(self) -> Dict[str, Any]:
        """当前插件的完整配置（默认值 + 用户覆盖）"""
        return self._plugin.config(self._manager)

    def get(self, key: str, default: Any = None) -> Any:
        """读取本插件配置项"""
        return self.config().get(key, default)

    def set(self, key: str, value: Any):
        """写入本插件配置项（持久化）"""
        self._manager.set_plugin_config(self.name, key, value)

    # -------------------------------------------------- 便捷能力

    def colorize(self, text: str, key: str = 'info') -> str:
        """按主题着色（无主题时原样返回）"""
        if self.theme:
            try:
                return self.theme.colorize(text, key)
            except Exception:
                return text
        return text

    def log(self, message: str):
        """记录一条日志（加载阶段会打印到终端）"""
        self.logs.append(str(message))

    def command_exists(self, name: str) -> bool:
        return name in self._manager.builtin.commands

    def register_command(self, name: str, func: Callable,
                         usage: str = '', description: str = '') -> bool:
        """运行期动态注册一条命令"""
        spec = PluginCommand(name, function='', usage=usage, description=description)
        return self._manager.register_single_command(self._plugin, spec, func)


# ======================================================================
# 插件管理器
# ======================================================================

class PluginManager:
    """插件的发现、加载、注册与配置管理"""

    def __init__(self, platform, filesystem, parser, settings, theme, builtin):
        self.platform = platform
        self.fs = filesystem
        self.parser = parser
        self.settings = settings
        self.theme = theme
        self.builtin = builtin

        self.plugins: Dict[str, Plugin] = {}
        self.dirs: List[pathlib.Path] = self.resolve_dirs()
        self._module_seq = 0

    # ---------------------------------------------------------------- 目录

    def resolve_dirs(self) -> List[pathlib.Path]:
        """
        解析插件搜索目录（按优先级从高到低）

        1. 打包环境内置目录（PyInstaller 解包目录）
        2. 源码同级 plugins/ 目录
        3. 可执行文件同级的 plugins/ 目录（用户放插件的推荐位置）
        4. 用户主目录 ~/.kshell/plugins
        5. 配置中额外指定的目录
        """
        dirs: List[pathlib.Path] = []

        packed = getattr(sys, '_MEIPASS', None)
        if packed:
            dirs.append(pathlib.Path(packed) / 'plugins')

        dirs.append(pathlib.Path(__file__).resolve().parent / 'plugins')

        if getattr(sys, 'frozen', False):
            dirs.append(pathlib.Path(sys.executable).resolve().parent / 'plugins')

        try:
            dirs.append(pathlib.Path.home() / '.kshell' / 'plugins')
        except Exception:
            pass

        for extra in self.settings.get('plugins.dirs', []) or []:
            try:
                dirs.append(pathlib.Path(extra).expanduser())
            except Exception:
                continue

        # 去重并保持顺序
        seen = set()
        result = []
        for d in dirs:
            key = str(d)
            if key not in seen:
                seen.add(key)
                result.append(d)
        return result

    def refresh_dirs(self):
        """重新解析搜索目录（配置变更后调用）"""
        self.dirs = self.resolve_dirs()

    def find_manifests(self) -> List[pathlib.Path]:
        """扫描所有目录，返回 plugin.json 路径列表（同名插件高优先级覆盖）"""
        found: Dict[str, pathlib.Path] = {}
        order: List[str] = []

        for base in self.dirs:
            try:
                if not base.is_dir():
                    continue
                entries = sorted(base.iterdir(), key=lambda p: p.name)
            except (OSError, PermissionError):
                continue

            for entry in entries:
                try:
                    if not entry.is_dir():
                        continue
                except OSError:
                    continue

                manifest = entry / MANIFEST_NAME
                if not manifest.is_file():
                    continue

                name = entry.name
                if name not in found:
                    order.append(name)
                # 先出现的目录优先级更高，不覆盖
                found.setdefault(name, manifest)

        return [found[n] for n in order if n in found]

    # ---------------------------------------------------------------- 配置

    def is_enabled(self, name: str, default: bool = True) -> bool:
        """插件是否启用（配置缺失时用 manifest 中的 enabled，再退回默认）"""
        stored = self.settings.get('plugins.enabled', {}) or {}
        if name in stored:
            return bool(stored[name])
        plugin = self.plugins.get(name)
        if plugin is not None:
            return bool(plugin.manifest.get('enabled', default))
        return default

    def set_enabled(self, name: str, flag: bool) -> bool:
        """持久化启用状态"""
        stored = dict(self.settings.get('plugins.enabled', {}) or {})
        stored[name] = bool(flag)
        self.settings.set('plugins.enabled', stored)
        return True

    def stored_config(self, name: str) -> Dict[str, Any]:
        """读取用户在配置文件中保存的插件配置"""
        all_conf = self.settings.get('plugins.config', {}) or {}
        value = all_conf.get(name, {})
        return dict(value) if isinstance(value, dict) else {}

    def set_plugin_config(self, name: str, key: str, value: Any) -> bool:
        all_conf = dict(self.settings.get('plugins.config', {}) or {})
        plugin_conf = dict(all_conf.get(name, {}) or {})
        plugin_conf[key] = value
        all_conf[name] = plugin_conf
        self.settings.set('plugins.config', all_conf)
        return True

    # ---------------------------------------------------------------- 加载

    def load_all(self) -> Dict[str, Any]:
        """加载全部插件，返回统计信息"""
        self.plugins.clear()
        summary = {'loaded': 0, 'disabled': 0, 'failed': 0, 'commands': 0, 'errors': []}

        for manifest in self.find_manifests():
            plugin = self.load(manifest.parent, quiet=True)
            self.plugins[plugin.name] = plugin
            if plugin.loaded:
                summary['loaded'] += 1
                summary['commands'] += len(plugin.registered)
            elif plugin.load_error:
                summary['failed'] += 1
                summary['errors'].append((plugin.name, plugin.load_error))
            else:
                summary['disabled'] += 1

        return summary

    def load(self, plugin_dir: pathlib.Path, quiet: bool = False) -> Plugin:
        """加载单个插件目录"""
        plugin = Plugin(plugin_dir)

        # ---- 1. 读取并校验 manifest ----
        manifest_path = plugin_dir / MANIFEST_NAME
        try:
            raw = manifest_path.read_text(encoding='utf-8')
            manifest = json.loads(raw)
        except json.JSONDecodeError as e:
            plugin.load_error = f'{MANIFEST_NAME} JSON 解析失败: {e}'
            return plugin
        except OSError as e:
            plugin.load_error = f'无法读取 {MANIFEST_NAME}: {e}'
            return plugin

        if not isinstance(manifest, dict):
            plugin.load_error = f'{MANIFEST_NAME} 顶层必须是 JSON 对象'
            return plugin

        try:
            self._parse_manifest(plugin, manifest, plugin_dir)
        except PluginError as e:
            plugin.load_error = str(e)
            return plugin

        # ---- 2. 版本要求 ----
        ok, reason = check_requirement(plugin.requires, VERSION)
        if not ok:
            plugin.load_error = reason
            return plugin

        # ---- 3. 启用状态 ----
        if not self.is_enabled(plugin.name):
            return plugin  # loaded=False, load_error='' → 视为已禁用

        # ---- 4. 加载 Python 模块 ----
        entry = plugin_dir / ENTRY_NAME
        if not entry.is_file():
            plugin.load_error = f'缺少实现文件 {ENTRY_NAME}'
            return plugin

        try:
            module = self._import_module(plugin, entry)
        except Exception as e:
            plugin.load_error = f'{ENTRY_NAME} 导入失败: {e.__class__.__name__}: {e}'
            if not quiet:
                traceback.print_exc()
            return plugin

        plugin.module = module
        plugin.ctx = PluginContext(self, plugin)

        # ---- 5. 注册命令 ----
        registered: List[str] = []
        for spec in plugin.commands:
            func = getattr(module, spec.function, None)
            if not callable(func):
                plugin.load_error = (f'命令 "{spec.name}" 声明的函数 '
                                     f'{spec.function}() 在 {ENTRY_NAME} 中不存在')
                self._unregister(registered)
                return plugin
            self._register(plugin, spec, func)
            registered.append(spec.name)
            for alias in spec.aliases:
                self.builtin.commands[alias] = self.builtin.commands[spec.name]
                registered.append(alias)

        plugin.registered = registered
        plugin.loaded = True

        # ---- 6. 可选回调 ----
        on_load = getattr(module, 'on_load', None)
        if callable(on_load):
            try:
                on_load(plugin.ctx)
            except Exception as e:
                plugin.ctx.log(f'on_load 回调出错: {e}')

        if not quiet and plugin.ctx.logs:
            for line in plugin.ctx.logs:
                print(f'[插件 {plugin.name}] {line}')

        return plugin

    def _parse_manifest(self, plugin: Plugin, manifest: dict, plugin_dir: pathlib.Path):
        """校验 manifest 并填充 Plugin 对象"""
        name = str(manifest.get('name') or plugin_dir.name).strip()
        if not NAME_PATTERN.match(name):
            raise PluginError(f'插件名 "{name}" 非法（仅允许字母、数字、下划线、连字符）')
        if name != plugin_dir.name:
            raise PluginError(f'插件名 "{name}" 与目录名 "{plugin_dir.name}" 不一致')

        plugin.name = name
        plugin.version = str(manifest.get('version') or '0.0.0')
        plugin.author = str(manifest.get('author') or '')
        plugin.description = str(manifest.get('description') or '')
        plugin.homepage = str(manifest.get('homepage') or '')
        plugin.requires = str(manifest.get('kshell') or manifest.get('requires') or '')
        plugin.manifest = manifest

        settings_defaults = manifest.get('settings') or {}
        if not isinstance(settings_defaults, dict):
            raise PluginError('settings 必须是 JSON 对象')
        plugin.settings_defaults = settings_defaults

        plugin.commands = self._parse_commands(manifest.get('commands'), plugin_dir)

    def _parse_commands(self, raw, plugin_dir: pathlib.Path) -> List[PluginCommand]:
        """解析 commands 声明，支持三种写法"""
        specs: List[PluginCommand] = []

        if raw is None:
            # 未声明 → 自动发现 plugin.py 中的 cmd_* 函数
            entry = plugin_dir / ENTRY_NAME
            if entry.is_file():
                try:
                    specs = self._discover_commands(entry)
                except Exception:
                    specs = []
            return specs

        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    if not CMD_PATTERN.match(item):
                        raise PluginError(f'命令名 "{item}" 非法')
                    specs.append(PluginCommand(item))
                elif isinstance(item, dict):
                    specs.append(self._command_from_dict(item))
                else:
                    raise PluginError('commands 列表元素必须是字符串或对象')
            return specs

        if isinstance(raw, dict):
            for cmd_name, cfg in raw.items():
                if not CMD_PATTERN.match(str(cmd_name)):
                    raise PluginError(f'命令名 "{cmd_name}" 非法')
                if cfg is None or isinstance(cfg, str):
                    specs.append(PluginCommand(str(cmd_name), function=cfg or ''))
                elif isinstance(cfg, dict):
                    merged = dict(cfg)
                    merged.setdefault('name', cmd_name)
                    specs.append(self._command_from_dict(merged))
                else:
                    raise PluginError(f'命令 "{cmd_name}" 的配置必须是对象')
            return specs

        raise PluginError('commands 必须是数组或对象')

    @staticmethod
    def _command_from_dict(item: dict) -> PluginCommand:
        name = str(item.get('name') or '').strip()
        if not name or not CMD_PATTERN.match(name):
            raise PluginError(f'命令名 "{name}" 非法')
        aliases = item.get('aliases') or []
        if not isinstance(aliases, list):
            aliases = []
        return PluginCommand(
            name=name,
            function=str(item.get('function') or ''),
            usage=str(item.get('usage') or ''),
            description=str(item.get('description') or ''),
            aliases=[str(a) for a in aliases],
        )

    @staticmethod
    def _discover_commands(entry: pathlib.Path) -> List[PluginCommand]:
        """从源码中自动发现 cmd_* 函数（不执行模块，仅静态扫描）"""
        specs: List[PluginCommand] = []
        text = entry.read_text(encoding='utf-8', errors='replace')
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('def cmd_'):
                fn = stripped[4:].split('(')[0].strip()
                if fn.startswith('cmd_') and len(fn) > 4:
                    cmd_name = fn[4:].replace('_', '-')
                    specs.append(PluginCommand(cmd_name, function=fn))
        return specs

    def _import_module(self, plugin: Plugin, entry: pathlib.Path):
        """
        加载插件模块。

        注意：这里刻意不用 importlib.util.spec_from_file_location + exec_module，
        因为 CPython 的 .pyc 过期判断依赖「源文件 mtime（秒级）+ 文件大小」，
        若开发者在同一秒内改动长度相同的代码，reload 会命中旧字节码。
        改为直接读取源码并 compile/exec，保证每次热重载都使用最新代码，
        同时也不会在用户的插件目录里生成 __pycache__。
        """
        self._module_seq += 1
        module_name = f'kshell_plugin_{plugin.name}_{self._module_seq}'

        try:
            source = entry.read_text(encoding='utf-8')
        except OSError as e:
            raise PluginError(f'无法读取 {entry.name}: {e}')

        try:
            code = compile(source, str(entry), 'exec')
        except SyntaxError as e:
            raise PluginError(f'{entry.name} 语法错误 第 {e.lineno} 行: {e.msg}')

        module = types.ModuleType(module_name)
        module.__file__ = str(entry)
        module.__loader__ = None
        module.__spec__ = None
        module.__package__ = ''

        sys.modules[module_name] = module
        try:
            exec(code, module.__dict__)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        return module

    # ---------------------------------------------------------------- 注册

    def _register(self, plugin: Plugin, spec: PluginCommand, func: Callable):
        """把插件函数包装后注册进 builtin.commands"""
        self.builtin.commands[spec.name] = self._wrap(plugin, spec, func)

    def register_single_command(self, plugin: Plugin, spec: PluginCommand, func: Callable) -> bool:
        """运行期注册单条命令"""
        if spec.name in self.builtin.commands:
            return False
        self._register(plugin, spec, func)
        plugin.registered.append(spec.name)
        return True

    @staticmethod
    def _wrap(plugin: Plugin, spec: PluginCommand, func: Callable):
        """包装插件函数：注入上下文、归一化返回值、隔离异常"""
        def handler(args, options):
            try:
                result = func(list(args), dict(options), plugin.ctx)
            except Exception as e:
                detail = f'{e.__class__.__name__}: {e}'
                return 1, f'[插件 {plugin.name}] 命令 {spec.name} 执行出错 → {detail}\n'
            return PluginManager._normalize(result)
        handler.__name__ = f'plugin_{plugin.name}_{spec.name}'
        return handler

    @staticmethod
    def _normalize(result) -> Tuple[int, str]:
        """把插件返回值归一化为 (退出码, 输出字符串)"""
        if result is None:
            return 0, ''
        if isinstance(result, tuple):
            if len(result) == 2:
                code, output = result
                try:
                    code = int(code)
                except (TypeError, ValueError):
                    code = 0
                return code, '' if output is None else str(output)
            if len(result) == 1:
                return 0, str(result[0])
            return 0, ' '.join(str(x) for x in result)
        if isinstance(result, bool):
            return (0 if result else 1), ''
        if isinstance(result, int):
            return result, ''
        return 0, str(result)

    def _unregister(self, commands: List[str]):
        for name in commands:
            self.builtin.commands.pop(name, None)

    # ---------------------------------------------------------------- 卸载

    def unload(self, name: str) -> bool:
        """卸载插件：移除命令、调用 on_unload、清理模块"""
        plugin = self.plugins.get(name)
        if plugin is None:
            return False

        if plugin.module is not None:
            on_unload = getattr(plugin.module, 'on_unload', None)
            if callable(on_unload):
                try:
                    on_unload(plugin.ctx)
                except Exception:
                    pass

        self._unregister(plugin.registered)
        plugin.registered = []

        if plugin.module is not None:
            for mod_name in list(sys.modules):
                if mod_name.startswith(f'kshell_plugin_{plugin.name}_'):
                    sys.modules.pop(mod_name, None)

        plugin.module = None
        plugin.loaded = False
        plugin.load_error = ''
        return True

    def reload(self, name: Optional[str] = None) -> Dict[str, Any]:
        """重新加载指定插件或全部插件"""
        if name:
            self.unload(name)
            manifest = None
            for base in self.dirs:
                candidate = base / name / MANIFEST_NAME
                if candidate.is_file():
                    manifest = candidate
                    break
            if manifest is None:
                return {'ok': False, 'message': f'找不到插件: {name}'}
            plugin = self.load(manifest.parent, quiet=True)
            self.plugins[name] = plugin
            if plugin.loaded:
                return {'ok': True, 'message': f'插件 {name} 已重新加载（{len(plugin.registered)} 条命令）'}
            if plugin.load_error:
                return {'ok': False, 'message': f'插件 {name} 加载失败: {plugin.load_error}'}
            return {'ok': True, 'message': f'插件 {name} 处于禁用状态'}

        return {'ok': True, 'message': '全部插件已重新加载', 'summary': self.load_all()}

    # ---------------------------------------------------------------- 脚手架

    @staticmethod
    def _is_temp_dir(directory: pathlib.Path) -> bool:
        """
        判断目录是否位于打包临时解包目录（_MEIPASS）之下。

        注意：_MEIPASS 本身可能是 plugins 的父目录，
        所以必须做「路径包含」判断，不能只比相等。
        """
        packed_root = getattr(sys, '_MEIPASS', None)
        if not packed_root:
            return False
        try:
            packed = pathlib.Path(packed_root).resolve()
            resolved = directory.resolve()
        except OSError:
            return False
        return resolved == packed or packed in resolved.parents

    def scaffold_dir(self) -> pathlib.Path:
        """
        选择用于生成新插件的目录（必须可持久化、可写）

        优先级：
          1. 当前搜索目录中可写且可持久化的那个
             （尊重用户通过配置或代码指定的 dirs —— 但要排除打包临时解包目录
              _MEIPASS，它退出即删，插件放进去会丢失）
          2. 可执行文件同级 plugins/（打包运行时的用户插件位置）
          3. 项目 plugins/（源码运行）
          4. ~/.kshell/plugins（用户级）
          5. 配置中额外指定的目录

        实现上对每个候选目录做一次真实的写入探测，确保返回的目录确实可用。
        """
        candidates: List[pathlib.Path] = []

        # 1. 当前搜索目录（跳过打包临时目录）
        for directory in self.dirs:
            if self._is_temp_dir(directory):
                continue
            candidates.append(directory)

        # 2-4. 兜底候选
        if getattr(sys, 'frozen', False):
            candidates.append(pathlib.Path(sys.executable).resolve().parent / 'plugins')
        else:
            candidates.append(pathlib.Path(__file__).resolve().parent / 'plugins')
        try:
            candidates.append(pathlib.Path.home() / '.kshell' / 'plugins')
        except Exception:
            pass

        # 5. 配置中额外指定的目录
        for extra in self.settings.get('plugins.dirs', []) or []:
            try:
                candidates.append(pathlib.Path(extra).expanduser())
            except Exception:
                continue

        # 去重并实测可写性
        seen = set()
        for candidate in candidates:
            key = str(candidate)
            if key in seen:
                continue
            seen.add(key)
            if self._is_temp_dir(candidate):
                continue
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                probe = candidate / '.kshell-write-test'
                probe.write_text('ok', encoding='utf-8')
                probe.unlink()
                return candidate
            except OSError:
                continue

        # 最终兜底：当前工作目录
        return pathlib.Path.cwd()

    def scaffold(self, name: str, author: str = '', description: str = '') -> Tuple[bool, str]:
        """生成新插件骨架到可持久化的插件目录"""
        if not NAME_PATTERN.match(name):
            return False, f'插件名 "{name}" 非法（仅允许字母、数字、下划线、连字符）'

        target_dir = self.scaffold_dir()

        dest = target_dir / name
        if dest.exists():
            return False, f'插件目录已存在: {dest}'

        try:
            dest.mkdir(parents=True)
            (dest / MANIFEST_NAME).write_text(
                self._manifest_template(name, author, description), encoding='utf-8')
            (dest / ENTRY_NAME).write_text(
                self._entry_template(name, description), encoding='utf-8')
        except OSError as e:
            return False, f'写入插件文件失败: {e}'

        # 新建目录立刻加入搜索路径，便于马上 reload 测试
        if target_dir not in self.dirs:
            self.dirs.insert(0, target_dir)

        return True, str(dest)

    @staticmethod
    def _manifest_template(name: str, author: str, description: str) -> str:
        manifest = {
            'name': name,
            'version': '0.1.0',
            'author': author or '你的名字',
            'description': description or f'{name} 插件',
            'kshell': f'>={VERSION}',
            'enabled': True,
            'commands': {
                name: {
                    'function': 'cmd_' + name.replace('-', '_'),
                    'usage': f'{name} [参数]',
                    'description': '插件命令说明',
                }
            },
            'settings': {
                'example': 'value',
            },
        }
        return json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'

    @staticmethod
    def _entry_template(name: str, description: str) -> str:
        fn = 'cmd_' + name.replace('-', '_')
        return f'''"""
{name} 插件

约定：
  · 每个命令对应一个函数，签名固定为 (args, options, ctx)
  · args    —— 位置参数列表
  · options —— 选项字典（-a 之类的布尔标志，或 --key=value）
  · ctx     —— 插件上下文，提供 fs / platform / settings / theme / config
  · 返回值   —— (退出码, 输出字符串)，也可直接返回字符串
"""


def {fn}(args, options, ctx):
    """{description or name + ' 的命令实现'}"""
    # 读取插件配置（来自 plugin.json 的 settings 段，可被用户覆盖）
    example = ctx.get('example', 'value')

    target = args[0] if args else 'World'
    verbose = 'v' in options or 'verbose' in options

    lines = [f'hello {{target}}（配置 example={{example}}）']
    if verbose:
        lines.append(f'插件目录: {{ctx.dir}}')
        lines.append(f'插件版本: {{ctx.version}}')

    return 0, '\\n'.join(lines)


def on_load(ctx):
    """可选：插件加载完成时调用"""
    ctx.log('{name} 插件已加载')


def on_unload(ctx):
    """可选：插件卸载时调用"""
    pass
'''

    # ---------------------------------------------------------------- 查询

    def list_plugins(self) -> List[Plugin]:
        return sorted(self.plugins.values(), key=lambda p: p.name.lower())

    def get(self, name: str) -> Optional[Plugin]:
        return self.plugins.get(name)

    def stats(self) -> Dict[str, Any]:
        loaded = [p for p in self.plugins.values() if p.loaded]
        failed = [p for p in self.plugins.values() if p.load_error]
        disabled = [p for p in self.plugins.values() if not p.loaded and not p.load_error]
        return {
            'total': len(self.plugins),
            'loaded': len(loaded),
            'disabled': len(disabled),
            'failed': len(failed),
            'commands': sum(len(p.registered) for p in loaded),
            'dirs': [str(d) for d in self.dirs],
        }
