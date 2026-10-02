# KShell 2.0 端到端测试脚本
echo === 1. system command direct ===
python --version
echo === 2. system command with options ===
python -c "import sys; print('argv:', sys.argv[1:])" -x --long val
echo === 3. builtin priority (ls is builtin) ===
ls -l kshell.py
echo === 4. command bypass forced system ===
command where python
echo === 5. path command ===
path -s findstr
echo === 6. calc ===
calc 2**10
echo === 7. pipeline builtin to system ===
ls | findstr .py
echo === 8. not found ===
no_such_command_xyz
echo === done ===
