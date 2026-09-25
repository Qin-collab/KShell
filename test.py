#!/usr/bin/env python3
"""
KShell 测试脚本
测试终端的基本功能
"""

import sys
import pathlib

# 添加当前目录到 Python 路径
current_dir = pathlib.Path(__file__).parent
sys.path.insert(0, str(current_dir))

from kplatform import Platform
from filesystem import FileSystem
from parser import CommandParser
from builtin import BuiltinCommands

def test_platform():
    """测试平台检测"""
    print("=== 测试平台检测 ===")
    platform = Platform()
    print(f"系统: {platform.system}")
    print(f"路径分隔符: {platform.path_separator}")
    print(f"主目录: {platform.home_dir}")
    print(f"Shell 命令: {platform.get_shell_command()}")
    print(f"环境变量分隔符: {platform.get_env_separator()}")
    print()

def test_filesystem():
    """测试文件系统操作"""
    print("=== 测试文件系统操作 ===")
    platform = Platform()
    fs = FileSystem(platform)

    print(f"当前目录: {fs.getcwd()}")
    print()

    # 测试创建目录
    print("创建测试目录...")
    fs.mkdir("test_kshell_dir")
    print(f"目录存在: {fs.exists('test_kshell_dir')}")
    print(f"是目录: {fs.is_dir('test_kshell_dir')}")
    print()

    # 测试创建文件
    print("创建测试文件...")
    fs.write_file("test_kshell_dir/test.txt", "Hello, KShell!")
    print(f"文件存在: {fs.exists('test_kshell_dir/test.txt')}")
    print(f"是文件: {fs.is_file('test_kshell_dir/test.txt')}")
    print()

    # 测试读取文件
    print("读取文件内容...")
    content = fs.read_file("test_kshell_dir/test.txt")
    print(f"内容: {content}")
    print()

    # 测试列出目录
    print("列出目录内容...")
    items = fs.list_dir("test_kshell_dir")
    for name, item_type in items:
        print(f"  {name} ({item_type})")
    print()

    # 测试复制文件
    print("复制文件...")
    fs.copy_file("test_kshell_dir/test.txt", "test_kshell_dir/test_copy.txt")
    print(f"复制文件存在: {fs.exists('test_kshell_dir/test_copy.txt')}")
    print()

    # 测试移动文件
    print("移动文件...")
    fs.move("test_kshell_dir/test_copy.txt", "test_kshell_dir/test_moved.txt")
    print(f"移动文件存在: {fs.exists('test_kshell_dir/test_moved.txt')}")
    print(f"原文件存在: {fs.exists('test_kshell_dir/test_copy.txt')}")
    print()

    # 测试删除文件
    print("删除文件...")
    fs.remove_file("test_kshell_dir/test.txt")
    fs.remove_file("test_kshell_dir/test_moved.txt")
    print(f"文件存在: {fs.exists('test_kshell_dir/test.txt')}")
    print()

    # 测试删除目录
    print("删除目录...")
    fs.remove_dir("test_kshell_dir")
    print(f"目录存在: {fs.exists('test_kshell_dir')}")
    print()

def test_parser():
    """测试命令解析器"""
    print("=== 测试命令解析器 ===")
    parser = CommandParser()

    # 测试基本命令解析
    print("解析: ls -la /tmp")
    cmd, args, opts = parser.parse("ls -la /tmp")
    print(f"  命令: {cmd}")
    print(f"  参数: {args}")
    print(f"  选项: {opts}")
    print()

    # 测试带引号的命令
    print('解析: echo "Hello World"')
    cmd, args, opts = parser.parse('echo "Hello World"')
    print(f"  命令: {cmd}")
    print(f"  参数: {args}")
    print(f"  选项: {opts}")
    print()

    # 测试长选项
    print("解析: ls --all --long")
    cmd, args, opts = parser.parse("ls --all --long")
    print(f"  命令: {cmd}")
    print(f"  参数: {args}")
    print(f"  选项: {opts}")
    print()

    # 测试带值的选项
    print("解析: ls --sort=time")
    cmd, args, opts = parser.parse("ls --sort=time")
    print(f"  命令: {cmd}")
    print(f"  参数: {args}")
    print(f"  选项: {opts}")
    print()

    # 测试重定向解析
    print("解析重定向: ls > output.txt")
    args = ["ls", ">", "output.txt"]
    clean_args, output_file, input_file = parser.parse_redirect(args)
    print(f"  清理后参数: {clean_args}")
    print(f"  输出文件: {output_file}")
    print(f"  输入文件: {input_file}")
    print()

    # 测试管道解析
    print("解析管道: ls | grep test")
    pipeline = parser.parse_pipeline("ls | grep test")
    print(f"  管道命令: {pipeline}")
    print()

def test_builtin_commands():
    """测试内置命令"""
    print("=== 测试内置命令 ===")
    platform = Platform()
    fs = FileSystem(platform)
    builtin = BuiltinCommands(fs, platform)

    # 创建测试环境
    fs.mkdir("test_builtin_dir")
    fs.write_file("test_builtin_dir/file1.txt", "Content 1")
    fs.write_file("test_builtin_dir/file2.txt", "Content 2")

    # 测试 pwd
    print("测试 pwd:")
    code, output = builtin.cmd_pwd([], {})
    print(f"  {output}")

    # 测试 ls
    print("测试 ls:")
    code, output = builtin.cmd_ls([], {})
    print(f"  {output}")

    # 测试 ls -l
    print("测试 ls -l:")
    code, output = builtin.cmd_ls([], {'l': True})
    print(f"  {output}")

    # 测试 echo
    print("测试 echo:")
    code, output = builtin.cmd_echo(["Hello", "World"], {})
    print(f"  {output}")

    # 测试 cat
    print("测试 cat:")
    code, output = builtin.cmd_cat(["test_builtin_dir/file1.txt"], {})
    print(f"  {output}")

    # 测试 help
    print("测试 help:")
    code, output = builtin.cmd_help([], {})
    print(f"  {output[:200]}...")

    # 清理测试环境
    fs.remove_file("test_builtin_dir/file1.txt")
    fs.remove_file("test_builtin_dir/file2.txt")
    fs.remove_dir("test_builtin_dir")
    print()

def run_all_tests():
    """运行所有测试"""
    print("KShell 测试套件")
    print("=" * 50)
    print()

    try:
        test_platform()
        test_filesystem()
        test_parser()
        test_builtin_commands()

        print("=" * 50)
        print("所有测试完成！")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_all_tests()