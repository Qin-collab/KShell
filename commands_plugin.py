"""
KShell - 插件管理命令 (v2.1)

提供 plugin 命令组：
    plugin                    列出全部插件
    plugin list               同上
    plugin info <name>        插件详情（元数据、命令、配置）
    plugin enable <name>      启用插件（持久化）
    plugin disable <name>     禁用插件（持久化）
    plugin reload [name]      重新加载插件
    plugin config <name>      查看插件配置
    plugin config <n> k=v     修改插件配置
    plugin dirs               显示插件搜索目录
    plugin new <name>         生成插件骨架
"""

import pathlib
from typing import List, Tuple

from version import VERSION


class PluginCommands:
    """plugin 命令处理器"""

    def __init__(self, builtin):
        self.builtin = builtin
        self.theme = getattr(builtin, 'theme', None)
        self.platform = builtin.platform
        self._register()

    def _register(self):
        self.builtin.commands.update({
            'plugin': self.cmd_plugin,
        })

    # ------------------------------------------------------------------ 工具

    @property
    def manager(self):
        """延迟获取插件管理器（由 Terminal 注入）"""
        return getattr(self.builtin, 'plugin_manager', None)

    def _c(self, text, key):
        if self.theme:
            try:
                return self.theme.colorize(text, key)
            except Exception:
                return text
        return text

    @staticmethod
    def _bool_mark(flag: bool) -> str:
        # 用 GBK 可编码的字符，避免 Windows 控制台输出崩溃
        return '是' if flag else '否'

    # ------------------------------------------------------------------ 入口

    def cmd_plugin(self, args: List[str], options: dict) -> Tuple[int, str]:
        mgr = self.manager
        if mgr is None:
            return 1, '插件系统未初始化'

        action = args[0] if args else 'list'
        rest = args[1:]

        handlers = {
            'list': self._action_list,
            'ls': self._action_list,
            'info': self._action_info,
            'show': self._action_info,
            'enable': self._action_enable,
            'disable': self._action_disable,
            'reload': self._action_reload,
            'config': self._action_config,
            'dirs': self._action_dirs,
            'dir': self._action_dirs,
            'new': self._action_new,
            'create': self._action_new,
            'help': self._action_help,
        }

        handler = handlers.get(action)
        if handler is None:
            return 1, (f'未知的 plugin 子命令: {action}\n'
                       f'可用: list | info | enable | disable | reload | config | dirs | new | help')

        return handler(rest, options)

    # ------------------------------------------------------------------ list

    def _action_list(self, args: List[str], options: dict) -> Tuple[int, str]:
        mgr = self.manager
        plugins = mgr.list_plugins()
        stats = mgr.stats()

        lines = [
            self._c(f'KShell 插件（{stats["total"]} 个）', 'title'),
            '',
        ]

        if not plugins:
            lines.append('  暂无插件。')
            lines.append('')
            lines.append(f'  插件目录: {stats["dirs"][0] if stats["dirs"] else "-"}')
            lines.append('  用 plugin new <名称> 生成一个插件骨架。')
            return 0, '\n'.join(lines)

        lines.append(f'  {"名称":<14}{"版本":<10}{"状态":<8}命令数  说明')
        lines.append('  ' + '-' * 62)

        for p in plugins:
            if p.loaded:
                status = self._c('已加载', 'success')
            elif p.load_error:
                status = self._c('失败', 'error')
            else:
                status = self._c('已禁用', 'warning')

            desc = p.description or '-'
            if len(desc) > 30:
                desc = desc[:29] + '…'

            # 中文字符宽度对齐用简单填充
            lines.append(
                f'  {p.name:<14}{p.version:<10}{status:<8}'
                f'{len(p.registered):^6}  {desc}'
            )

        lines.append('')
        lines.append(f'  已加载 {stats["loaded"]} · 禁用 {stats["disabled"]} · '
                     f'失败 {stats["failed"]} · 注册命令 {stats["commands"]} 条')
        lines.append('  用 plugin info <名称> 查看详情，plugin help 查看全部子命令。')
        return 0, '\n'.join(lines)

    # ------------------------------------------------------------------ info

    def _action_info(self, args: List[str], options: dict) -> Tuple[int, str]:
        mgr = self.manager
        if not args:
            return 1, '用法: plugin info <插件名>'

        name = args[0]
        plugin = mgr.get(name)
        if plugin is None:
            return 1, f'找不到插件: {name}（用 plugin list 查看已安装插件）'

        conf = plugin.config(mgr)

        lines = [
            self._c(f'插件: {plugin.name}', 'title'),
            '',
            f'  版本    : {plugin.version}',
            f'  作者    : {plugin.author or "-"}',
            f'  说明    : {plugin.description or "-"}',
        ]
        if plugin.homepage:
            lines.append(f'  主页    : {plugin.homepage}')
        lines.append(f'  要求    : KShell {plugin.requires or ">= " + VERSION}')
        lines.append(f'  目录    : {plugin.path}')
        lines.append(f'  启用    : {self._bool_mark(mgr.is_enabled(name))}')

        if plugin.load_error:
            lines.append(f'  状态    : {self._c("加载失败", "error")} → {plugin.load_error}')
        elif plugin.loaded:
            lines.append(f'  状态    : {self._c("已加载", "success")}')
        else:
            lines.append(f'  状态    : {self._c("已禁用", "warning")}')

        # 命令
        lines.append('')
        lines.append('  注册的命令:')
        if plugin.registered:
            for cmd in plugin.registered:
                spec = next((s for s in plugin.commands if s.name == cmd), None)
                usage = spec.usage if spec and spec.usage else cmd
                desc = spec.description if spec else ''
                lines.append(f'    {usage:<24} {desc}')
        elif plugin.commands:
            for spec in plugin.commands:
                lines.append(f'    {spec.usage or spec.name:<24} {spec.description}')
        else:
            lines.append('    （未声明命令）')

        # 配置
        lines.append('')
        lines.append('  配置项:')
        if conf:
            for key, value in conf.items():
                default = plugin.settings_defaults.get(key, None)
                changed = '' if default == value else '  (已修改)'
                lines.append(f'    {key} = {value!r}{changed}')
        else:
            lines.append('    （无配置项）')

        lines.append('')
        lines.append(f'  修改配置: plugin config {name} <键>=<值>')
        return 0, '\n'.join(lines)

    # ------------------------------------------------------------ enable/disable

    def _action_enable(self, args: List[str], options: dict) -> Tuple[int, str]:
        return self._toggle(args, True)

    def _action_disable(self, args: List[str], options: dict) -> Tuple[int, str]:
        return self._toggle(args, False)

    def _toggle(self, args: List[str], flag: bool) -> Tuple[int, str]:
        mgr = self.manager
        if not args:
            return 1, f'用法: plugin {"enable" if flag else "disable"} <插件名>'

        name = args[0]
        plugin = mgr.get(name)
        if plugin is None:
            return 1, f'找不到插件: {name}'

        mgr.set_enabled(name, flag)
        action = '启用' if flag else '禁用'
        hint = '（下次启动生效；也可执行 plugin reload 立即生效）'
        return 0, f'已{action}插件 {name}{hint}'

    # ------------------------------------------------------------------ reload

    def _action_reload(self, args: List[str], options: dict) -> Tuple[int, str]:
        mgr = self.manager
        name = args[0] if args else None
        result = mgr.reload(name)

        lines = []
        if result.get('ok'):
            lines.append(self._c(result['message'], 'success'))
        else:
            lines.append(self._c(result['message'], 'error'))

        summary = result.get('summary')
        if summary:
            lines.append(f'  已加载 {summary["loaded"]} · 禁用 {summary["disabled"]} · '
                         f'失败 {summary["failed"]} · 命令 {summary["commands"]} 条')
            for pname, err in summary.get('errors', []):
                lines.append(f'  {self._c(pname, "error")}: {err}')

        return (0 if result.get('ok') else 1), '\n'.join(lines)

    # ------------------------------------------------------------------ config

    def _action_config(self, args: List[str], options: dict) -> Tuple[int, str]:
        mgr = self.manager
        if not args:
            return 1, '用法: plugin config <插件名> [键=值 ...]'

        name = args[0]
        plugin = mgr.get(name)
        if plugin is None:
            return 1, f'找不到插件: {name}'

        assignments = args[1:]
        if not assignments:
            # 查看
            conf = plugin.config(mgr)
            lines = [self._c(f'插件 {name} 的配置', 'title'), '']
            if not conf:
                lines.append('  （无配置项）')
            for key, value in conf.items():
                default = plugin.settings_defaults.get(key, None)
                mark = '' if default == value else '  (已修改)'
                lines.append(f'  {key} = {value!r}{mark}')
            lines.append('')
            lines.append(f'  修改: plugin config {name} <键>=<值>')
            return 0, '\n'.join(lines)

        # 修改
        changed = []
        for item in assignments:
            if '=' not in item:
                return 1, f'参数格式应为 <键>=<值>，收到: {item}'
            key, raw_value = item.split('=', 1)
            key = key.strip()
            if not key:
                return 1, '配置键不能为空'
            mgr.set_plugin_config(name, key, self._coerce(raw_value))
            changed.append(key)

        lines = [self._c(f'已更新插件 {name} 的配置: {", ".join(changed)}', 'success')]
        lines.append('  配置已立即生效（插件每次执行都会重新读取配置）。')
        lines.append('  只有修改了 plugin.py 源码才需要执行 plugin reload。')
        return 0, '\n'.join(lines)

    @staticmethod
    def _coerce(raw: str):
        """把配置值字符串转成合适的类型"""
        text = raw.strip()
        low = text.lower()
        if low in ('true', 'yes', 'on'):
            return True
        if low in ('false', 'no', 'off'):
            return False
        if low in ('null', 'none'):
            return None
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        return raw

    # ------------------------------------------------------------------ dirs

    def _action_dirs(self, args: List[str], options: dict) -> Tuple[int, str]:
        mgr = self.manager
        lines = [self._c('插件搜索目录（优先级从高到低）', 'title'), '']
        for idx, directory in enumerate(mgr.dirs, 1):
            exists = directory.is_dir()
            mark = self._c('存在', 'success') if exists else self._c('不存在', 'dim') \
                if hasattr(mgr.theme, 'colorize') else ('存在' if exists else '不存在')
            count = 0
            if exists:
                try:
                    count = sum(1 for d in directory.iterdir()
                                if (d / 'plugin.json').is_file())
                except OSError:
                    count = 0
            lines.append(f'  {idx}. {directory}')
            lines.append(f'     [{mark}] 插件数: {count}')
        lines.append('')
        lines.append('  可用 config set plugins.dirs 追加自定义目录（JSON 数组）。')
        return 0, '\n'.join(lines)

    # ------------------------------------------------------------------ new

    def _action_new(self, args: List[str], options: dict) -> Tuple[int, str]:
        mgr = self.manager
        if not args:
            return 1, '用法: plugin new <名称> [--author "作者"] [--description "说明"]'

        name = args[0]
        author = str(options.get('author') or options.get('a') or '')
        description = str(options.get('description') or options.get('d') or '')

        ok, info = mgr.scaffold(name, author, description)
        if not ok:
            return 1, info

        lines = [
            self._c(f'插件骨架已生成: {info}', 'success'),
            '',
            '  生成的文件:',
            '    plugin.json   元数据与命令声明、默认配置',
            '    plugin.py     Python 实现（函数签名 (args, options, ctx)）',
            '',
            '  下一步:',
            f'    1. 编辑 {info}\\plugin.py 实现你的命令',
            f'    2. 执行 plugin reload {name} 加载测试',
            f'    3. 执行 plugin info {name} 查看注册结果',
        ]
        return 0, '\n'.join(lines)

    # ------------------------------------------------------------------ help

    def _action_help(self, args: List[str], options: dict) -> Tuple[int, str]:
        lines = [
            self._c('plugin - KShell 插件管理 (v2.1)', 'title'),
            '',
            '  plugin                     列出全部插件',
            '  plugin list                同上',
            '  plugin info <名称>          插件详情：元数据、命令、配置',
            '  plugin enable <名称>        启用插件（写入配置）',
            '  plugin disable <名称>       禁用插件（写入配置）',
            '  plugin reload [名称]        重新加载插件（省略名称则全部）',
            '  plugin config <名称>        查看插件配置',
            '  plugin config <名称> k=v    修改插件配置',
            '  plugin dirs                显示插件搜索目录',
            '  plugin new <名称>           生成插件骨架',
            '',
            self._c('插件结构', 'info'),
            '  plugins/<名称>/plugin.json  元数据、命令声明、默认配置',
            '  plugins/<名称>/plugin.py    实现（每个命令一个函数）',
            '',
            self._c('函数签名', 'info'),
            '  def cmd_xxx(args, options, ctx):',
            '      return 0, "输出内容"',
            '',
            '  args    —— 位置参数列表',
            '  options —— 选项字典，如 {"v": True} 或 {"name": "value"}',
            '  ctx     —— 上下文：ctx.get/set 读写配置，ctx.fs/platform/theme 等',
            '',
            f'  详细文档见项目根目录 PLUGIN_DEV.md',
        ]
        return 0, '\n'.join(lines)
