"""
pwgen 插件 —— 密码与 UUID 生成器

演示内容：
  · 一个插件注册多个命令（pwgen / uuid / passwd-strength）
  · 命令名与函数名不同（passwd-strength → cmd_strength）
  · 命令别名（uuid 同时提供 guuid）
  · 用 ctx.get 读取配置，配置项在 plugin.json 的 settings 中声明
  · 用 ctx.colorize 输出带主题颜色的结果

安全说明：使用标准库 secrets（加密安全随机源），不要用 random 生成密码。
"""

import secrets
import string
import uuid as uuid_module

# 字符集
LOWER = string.ascii_lowercase
UPPER = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = '!@#$%^&*()-_=+[]{}'

# 易混淆字符（0/O、1/l/I 等）
AMBIGUOUS = '0O1lI|`'


def _charset(use_symbols=True, avoid_ambiguous=True):
    """构造字符集"""
    pool = LOWER + UPPER + DIGITS
    if use_symbols:
        pool += SYMBOLS
    if avoid_ambiguous:
        pool = ''.join(c for c in pool if c not in AMBIGUOUS)
    return pool


def _generate(length, use_symbols=True, avoid_ambiguous=True):
    """生成一个密码（加密安全）"""
    pool = _charset(use_symbols, avoid_ambiguous)
    return ''.join(secrets.choice(pool) for _ in range(length))


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def cmd_pwgen(args, options, ctx):
    """
    pwgen [数量] [长度] [--no-symbols] [--avoid-ambiguous]

    数量与长度也可通过 plugin config 修改默认值：
        plugin config pwgen default_length=24
    """
    count = _to_int(args[0], None) if len(args) > 0 else None
    length = _to_int(args[1], None) if len(args) > 1 else None

    # 也支持 --length=24 / --count=5
    if 'length' in options:
        length = _to_int(options['length'], length)
    if 'count' in options:
        count = _to_int(options['count'], count)

    count = count if count is not None else _to_int(ctx.get('default_count', 1), 1)
    length = length if length is not None else _to_int(ctx.get('default_length', 16), 16)

    if count < 1 or count > 200:
        return 1, f'数量必须在 1-200 之间，收到 {count}'
    if length < 6 or length > 256:
        return 1, f'长度必须在 6-256 之间，收到 {length}'

    use_symbols = ctx.get('use_symbols', True)
    if 'no-symbols' in options or 's' in options:
        use_symbols = False

    avoid_ambiguous = ctx.get('avoid_ambiguous', True)
    if 'avoid-ambiguous' in options:
        avoid_ambiguous = True

    passwords = [_generate(length, use_symbols, avoid_ambiguous) for _ in range(count)]

    lines = []
    if count > 1:
        lines.append(ctx.colorize(f'已生成 {count} 个密码（长度 {length}）', 'title'))
        lines.append('')
        for idx, pwd in enumerate(passwords, 1):
            lines.append(f'  {idx:>3}. {pwd}')
    else:
        lines.append(passwords[0])

    return 0, '\n'.join(lines)


def cmd_uuid(args, options, ctx):
    """uuid [数量] —— 生成 UUID v4"""
    count = _to_int(args[0], 1) if args else 1
    if count < 1 or count > 100:
        return 1, f'数量必须在 1-100 之间，收到 {count}'

    if count == 1:
        return 0, str(uuid_module.uuid4())
    return 0, '\n'.join(str(uuid_module.uuid4()) for _ in range(count))


def cmd_strength(args, options, ctx):
    """
    passwd-strength <密码> —— 粗略评估密码强度

    演示：一条命令同时读取参数并输出着色结果。
    """
    if not args:
        return 1, '用法: passwd-strength <密码>'

    password = args[0]
    score = 0
    notes = []

    if len(password) >= 8:
        score += 1
    else:
        notes.append('长度不足 8 位')
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if any(c.islower() for c in password):
        score += 1
    else:
        notes.append('缺少小写字母')
    if any(c.isupper() for c in password):
        score += 1
    else:
        notes.append('缺少大写字母')
    if any(c.isdigit() for c in password):
        score += 1
    else:
        notes.append('缺少数字')
    if any(c in SYMBOLS for c in password):
        score += 1
    else:
        notes.append('缺少符号')

    levels = [
        (2, '很弱', 'error'),
        (4, '较弱', 'warning'),
        (6, '中等', 'info'),
        (7, '较强', 'success'),
        (99, '很强', 'success'),
    ]
    label, color = '很弱', 'error'
    for threshold, name, key in levels:
        if score <= threshold:
            label, color = name, key
            break

    lines = [
        f'强度: {ctx.colorize(label, color)}   （评分 {score}/7）',
        f'长度: {len(password)} 字符',
    ]
    if notes:
        lines.append('建议: ' + '、'.join(notes))
    else:
        lines.append('建议: 未发现明显弱点')

    return 0, '\n'.join(lines)


def on_load(ctx):
    ctx.log('pwgen 插件已加载，执行 pwgen 生成密码')
