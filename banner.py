"""
启动横幅模块
显示终端启动信息（支持主题着色）
"""

from kplatform import Platform

def get_banner(platform: Platform, version: str = "1.0", theme=None) -> str:
    """获取启动横幅"""

    # ASCII Art 标志
    logo = r"""
  ____  _____   _____ _    ___
 |  _ \|  __ \ / ____| |  | \ \
 | |_) | |__) | |    | |__| | |
 |  _ <|  _  /| |    |  __  | |
 | |_) | | \ \| |____| |  | | |
 |____/|_|  \_\\_____|_|  |_|_|
"""

    # 根据平台显示不同的标识
    # 注意：Windows 控制台默认 GBK 编码，不支持 emoji，使用文本标识
    if platform.system == 'windows':
        os_name = '[Windows]'
    elif platform.system == 'macos':
        os_name = '[macOS]'
    elif platform.system == 'linux':
        os_name = '[Linux]'
    else:
        os_name = '[Unknown]'

    def _c(text, key):
        if theme:
            return theme.colorize(text, key)
        return text

    # 构建带颜色的横幅
    title = _c(f"KShell v{version} - 跨平台 Python 终端", 'banner_title')
    logo_c = _c(logo, 'banner_logo')
    info_platform = _c(f"Platform: {os_name}", 'banner_info')
    info_python = _c(f"Python:   {platform.get_python_version()}", 'banner_info')
    sep = "=" * 36
    hint = _c("Type 'help' for commands, 'theme' for themes, or 'config' for settings.", 'banner_info')

    banner = f"""
{logo_c}
 {title}
 {sep}
 {info_platform}
 {info_python}
 {hint}
 {sep}
"""
    return banner
