#!/usr/bin/env kshell
# KShell 示例脚本
# 演示各种命令的使用

echo "================================"
echo "  KShell 示例脚本"
echo "================================"
echo ""

echo "1. 显示当前目录:"
pwd
echo ""

echo "2. 显示当前用户:"
whoami
echo ""

echo "3. 显示主机名:"
hostname
echo ""

echo "4. 显示日期和时间:"
date
echo ""
time
echo ""

echo "5. 创建测试目录和文件:"
mkdir test_example_dir
touch test_example_dir/file1.txt
touch test_example_dir/file2.txt
echo "Hello, KShell!" > test_example_dir/file1.txt
echo "This is file 2." > test_example_dir/file2.txt
echo ""

echo "6. 列出目录内容:"
ls test_example_dir
echo ""

echo "7. 显示详细信息:"
ls -l test_example_dir
echo ""

echo "8. 查看文件内容:"
cat test_example_dir/file1.txt
echo ""

echo "9. 复制文件:"
cp test_example_dir/file1.txt test_example_dir/file1_copy.txt
echo "文件复制完成"
echo ""

echo "10. 再次列出目录:"
ls test_example_dir
echo ""

echo "11. 清理测试文件和目录:"
rm test_example_dir/file1.txt
rm test_example_dir/file2.txt
rm test_example_dir/file1_copy.txt
rmdir test_example_dir
echo "清理完成"
echo ""

echo "12. 检查清理结果:"
ls test_example_dir
echo ""

echo "================================"
echo "  脚本执行完成！"
echo "================================"