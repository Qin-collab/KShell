"""
hello 插件 —— KShell 插件开发最小示例

这个插件演示了插件系统的基础用法：
  · 从 plugin.json 的 settings 段读取配置（用户可覆盖）
  · 解析位置参数与选项
  · 通过 ctx 访问插件元信息
  · 返回 (退出码, 输出字符串)

约定：命令函数签名固定为 (args, options, ctx)
"""


def cmd_hello(args, options, ctx):
    """
    hello [名字] [-v]

    args    : 位置参数列表，如 ['KShell']
    options : 选项字典，如 {'v': True}（-v）或 {'name': 'x'}（--name x）
    ctx     : 插件上下文
    """
    # ---- 读取配置（plugin.json 的 settings，可被 plugin config 覆盖）----
    greeting = ctx.get('greeting', 'Hello')
    punctuation = ctx.get('punctuation', '!')
    uppercase = ctx.get('uppercase_name', False)

    # ---- 解析参数 ----
    name = args[0] if args else 'World'
    if uppercase:
        name = name.upper()

    verbose = 'v' in options or 'verbose' in options

    lines = [f'{greeting}, {name}{punctuation}']

    if verbose:
        lines.append('')
        lines.append(f'  插件名称 : {ctx.name}')
        lines.append(f'  插件版本 : {ctx.version}')
        lines.append(f'  插件目录 : {ctx.dir}')
        lines.append(f'  当前配置 : greeting={greeting!r} punctuation={punctuation!r} '
                     f'uppercase_name={uppercase!r}')
        lines.append(f'  主题着色 : {ctx.colorize("这是一段着色文本", "success")}')

    return 0, '\n'.join(lines)


def on_load(ctx):
    """插件加载完成时调用（可选）——可以在这里做初始化、打印提示"""
    ctx.log('示例插件已就绪，试试执行 hello')


def on_unload(ctx):
    """插件卸载/重载时调用（可选）——用于释放资源"""
    pass
