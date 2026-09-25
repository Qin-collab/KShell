#!/usr/bin/env python3
"""
KShell - 跨平台终端启动脚本
支持 Windows/MacOS/Linux
"""

import sys
import pathlib

# 添加当前目录到 Python 路径
current_dir = pathlib.Path(__file__).parent
sys.path.insert(0, str(current_dir))

from terminal import Terminal

def main():
    """主入口"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 执行脚本模式
        script_path = sys.argv[1]
        terminal = Terminal()
        terminal.execute_script(script_path)
    else:
        # 交互模式
        terminal = Terminal()
        terminal.run()

if __name__ == '__main__':
    main()