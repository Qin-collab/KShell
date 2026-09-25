# KShell 快速入门指南

## 5分钟快速开始

### 1. 运行终端

```bash
# Windows
python kshell.py

# 或双击
kshell.bat

# Unix/Linux/macOS
python3 kshell.py

# 或
./kshell.sh
```

启动时会显示 ASCII 艺术横幅和系统信息，然后进入交互模式。

### 2. 基本命令

```bash
# 查看帮助
help

# 列出当前目录
ls

# 查看详细信息
ls -l

# 查看隐藏文件
ls -la

# 切换目录
cd Documents

# 返回上级目录
cd ..

# 返回主目录
cd

# 显示当前目录
pwd
```

### 3. 文件操作

```bash
# 创建目录
mkdir myproject

# 进入目录
cd myproject

# 创建文件
touch readme.txt

# 写入内容
echo "Hello, KShell!" > readme.txt

# 查看内容
cat readme.txt

# 复制文件
cp readme.txt readme_backup.txt

# 重命名文件
mv readme_backup.txt backup.txt

# 删除文件
rm backup.txt

# 返回上级并删除目录
cd ..
rmdir myproject
```

### 4. 实用功能

```bash
# 清屏
clear  # Unix/Linux/macOS
cls    # Windows

# 查看日期
date

# 查看时间
time

# 查看用户
whoami

# 查看主机名
hostname

# 查看环境变量
env

# 设置环境变量
set MY_VAR=hello

# 查看环境变量
set MY_VAR

# 删除环境变量
unset MY_VAR
```

### 5. 命令历史

```bash
# 查看历史
history

# 使用别名
alias ll='ls -la'
ll

# 删除别名
unalias ll
```

### 6. 运行脚本

创建 `myscript.ksh`:
```bash
echo "My Script"
pwd
ls -l
```

运行脚本:
```bash
python kshell.py myscript.ksh
```

### 7. 管道和重定向

```bash
# 输出重定向
echo "Hello" > output.txt

# 追加输出
echo "World" >> output.txt

# 查看输出
cat output.txt

# 管道（基础支持）
ls -l | more
```

### 8. 高级命令

```bash
# 查看文件前/后 N 行
head -n 5 readme.txt
tail -n 20 app.log

# 搜索文件内容
grep error app.log
grep -in warning app.log      # 忽略大小写 + 显示行号

# 递归搜索
grep -r "class" .

# 统计信息
wc -l app.log                 # 行数
wc -w app.log                 # 字数
wc -c app.log                 # 字节

# 查找文件
find . -name "*.py"
find . -type d                # 只找目录
find . -name "*.txt" -maxdepth 2

# 查看目录树
tree

# 磁盘和目录大小
df -h
du -h .

# 排序和去重
sort names.txt
sort -r names.txt             # 逆序
uniq names.txt

# 系统信息
uptime
uname -a
id
ps                            # 进程列表
sleep 2                       # 延迟 2 秒

# 哈希和编码
md5sum file.txt
sha256sum file.txt
base64 "Hello"                # 编码
base64 -d "SGVsbG8="          # 解码

# 数字序列
seq 1 10
seq 1 10 2                    # 步长 2

# 权限提升
sudo <command>                # Windows: UAC 弹窗 / Unix: 系统 sudo

# 其他
which python                  # 查找命令路径
true / false                  # 返回状态
man grep                      # 查看命令帮助
history -c                    # 清空历史
```

## 常见任务

### 批量重命名文件
```bash
# 创建测试文件
touch file1.txt file2.txt file3.txt

# 查看文件
ls *.txt

# 重命名
mv file1.txt newfile1.txt
mv file2.txt newfile2.txt
```

### 查看大文件
```bash
# 创建大文件
echo "Line 1" > bigfile.txt
echo "Line 2" >> bigfile.txt
echo "Line 3" >> bigfile.txt

# 分页查看
cat bigfile.txt | more
```

### 环境变量管理
```bash
# 设置 PATH
set PATH=/usr/bin:/bin:/usr/local/bin

# 查看单个变量
set PATH

# 导出变量
export MY_VAR=value
```

### 项目初始化
```bash
# 创建项目结构
mkdir myproject
cd myproject
mkdir src tests docs

# 创建文件
touch README.md
touch src/main.py
touch tests/test_main.py

# 查看结构
ls -R
```

## 快捷技巧

### 提示符定制
提示符自动显示用户名和当前目录，格式根据系统自动调整。

```bash
# 查看当前样式
config get prompt_style

# 切换为极简样式
config set prompt_style simple

# 切换为增强样式（显示时间和主机名）
config set prompt_style poweruser

# 恢复默认样式
config set prompt_style default
```

### 管理设置
```bash
# 查看所有设置
config list

# 关闭启动横幅
config set banner_enabled false

# 开启启动横幅
config set banner_enabled true

# 增大历史记录容量
config set history_size 2000

# 恢复默认设置
config reset
```

### 切换主题
```bash
# 查看当前主题
theme

# 预览所有主题色块
theme preview

# 切换主题（自动保存）
theme ocean
theme monokai
theme solarized

# 列出所有主题
theme list

# 等效方式
config set theme dark
```

设置保存在 `kshell_config.json` 文件中，重启后依然生效。

设置保存在 `kshell_config.json` 文件中，重启后依然生效。

### 命令别名
```bash
# 常用别名
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'
```

### 清理命令
```bash
# 清理测试文件
rm *.log
rm -rf test_*/

# 清理备份文件
rm *.bak
```

## 故障排除

### 命令未找到
```
command not found: xxx
```
- 检查命令拼写
- 确认命令在系统 PATH 中
- 使用绝对路径

### 权限被拒绝
```
Permission denied
```
- 检查文件/目录权限
- 使用管理员权限运行

### 文件不存在
```
No such file or directory
```
- 检查路径是否正确
- 使用 `pwd` 确认当前位置
- 使用 `ls` 查看文件列表

## 下一步

- 阅读 `README.md` 了解完整功能
- 查看 `example.ksh` 学习脚本编写
- 运行 `test.py` 了解测试方法
- 阅读 `STRUCTURE.md` 了解架构设计

## 提示

- 使用 `help` 查看所有可用命令
- 使用 `history` 查看最近执行的命令
- 使用 `Tab` 键（未来版本）自动补全
- 使用 `Ctrl+C` 中断当前命令
- 使用 `exit` 或 `Ctrl+D` 退出终端

享受使用 KShell！