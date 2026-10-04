"""
KShell 版本信息（单一来源）

其他模块统一从此处读取版本号，避免各处硬编码不一致。
"""

VERSION = '2.1.0'          # 完整版本号
VERSION_SHORT = '2.1'      # 横幅/提示符中显示的短版本
RELEASE_NAME = 'Plugin'


def version_tuple(version: str = None):
    """把版本号转成可比较的元组，如 '2.1.0' → (2, 1, 0)"""
    text = str(version if version is not None else VERSION)
    parts = []
    for chunk in text.split('.'):
        digits = ''
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def check_requirement(requirement: str, current: str = None) -> tuple:
    """
    校验版本要求表达式，如 '>=2.1.0'、'>2.0'、'==2.1.0'、'2.1.0'

    返回: (是否满足: bool, 说明: str)
    """
    if not requirement or not str(requirement).strip():
        return True, ''

    req = str(requirement).strip()
    current_tuple = version_tuple(current)

    for op in ('>=', '<=', '==', '!=', '>', '<'):
        if req.startswith(op):
            target = version_tuple(req[len(op):].strip())
            ok = {
                '>=': current_tuple >= target,
                '<=': current_tuple <= target,
                '==': current_tuple == target,
                '!=': current_tuple != target,
                '>': current_tuple > target,
                '<': current_tuple < target,
            }[op]
            if not ok:
                return False, f'需要 KShell {op}{req[len(op):].strip()}，当前 {current or VERSION}'
            return True, ''

    # 无操作符：视为最低版本
    target = version_tuple(req)
    if current_tuple < target:
        return False, f'需要 KShell >= {req}，当前 {current or VERSION}'
    return True, ''
