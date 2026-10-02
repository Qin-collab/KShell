# KShell - 跨平台终端

一个支持 Windows/MacOS/Linux 的纯 Python 终端，不使用 os 库，完全自己实现底层逻辑。

## 特性

- ✅ 跨平台支持（Windows/MacOS/Linux）
- ✅ 纯 Python 实现，不依赖 os 库
- ✅ 丰富的内置命令（60+）
- ✅ 命令历史记录（可配置大小）
- ✅ 别名支持（持久化）
- ✅ 管道支持（基础实现）
- ✅ 输入输出重定向
- ✅ 环境变量管理
- ✅ 脚本执行支持
- ✅ 启动横幅
- ✅ 可配置设置（JSON）
- ✅ 多种提示符样式
- ✅ 6 种颜色主题（可预览/切换/持久化）

## 安装

无需安装，只需 Python 3.6+ 即可运行。

```bash
# 克隆仓库
git clone <repository-url>
cd KShell
```

## 使用方法

### 交互模式

```bash
python kshell.py
```

### 执行脚本

```bash
python kshell.py script.ksh
```

## 内置命令

### 文件操作
| 命令 | 描述 |
|------|------|
| `cd <dir>` | 改变当前目录 |
| `ls [dir]` | 列出目录内容 |
| `pwd` | 显示当前目录 |
| `mkdir <dir>` | 创建目录 |
| `rmdir <dir>` | 删除空目录 |
| `rm <file>` | 删除文件 |
| `cp <src> <dst>` | 复制文件 |
| `mv <src> <dst>` | 移动/重命名文件 |
| `cat <file>` | 显示文件内容 |
| `touch <file>` | 创建空文件 |
| `head [-n N] <file>` | 显示文件前 N 行 (默认 10) |
| `tail [-n N] <file>` | 显示文件后 N 行 (默认 10) |
| `grep [-i] [-n] [-r] [-c] <pattern> [file...]` | 搜索文本 |
| `wc [-l] [-w] [-c] <file>` | 统计行数/字数/字节 |
| `sort [-r] [-n] <file>` | 排序文本行 |
| `uniq <file>` | 去除相邻重复行 |
| `nl <file>` | 带行号显示文件 |
| `find [path] [-name pattern] [-type f\|d]` | 查找文件 |
| `tree [path]` | 显示目录树 |
| `stat <file>` | 显示文件详细信息 |
| `du [-h] [path]` | 计算目录/文件大小 |
| `df [-h]` | 显示磁盘使用情况 |

### 系统命令
| 命令 | 描述 |
|------|------|
| `sudo <cmd>` | 以管理员/root 权限执行 (Windows UAC / Unix sudo) |
| `ps` | 显示进程列表 |
| `kill [-f] <pid>` | 终止进程 |
| `sleep <sec>` | 延迟指定秒数 |
| `uptime` | 显示系统运行时间 |
| `uname [-a]` | 显示系统信息 |
| `id` | 显示用户身份 |
| `date` | 显示日期 |
| `time` | 显示时间 |
| `whoami` | 显示当前用户 |
| `hostname` | 显示主机名 |

### 工具命令
| 命令 | 描述 |
|------|------|
| `echo <text>` | 打印文本 |
| `clear/cls` | 清屏 |
| `history` | 显示命令历史 (`history -c` 清空) |
| `env` | 显示环境变量 |
| `set <key=val>` | 设置环境变量 |
| `unset <key>` | 删除环境变量 |
| `alias <name=val>` | 设置别名 |
| `unalias <name>` | 删除别名 |
| `which <cmd>` | 查找命令路径 |
| `base64 [-d] <text\|file>` | Base64 编码/解码 |
| `md5sum <file>` | 计算 MD5 哈希 |
| `sha1sum <file>` | 计算 SHA1 哈希 |
| `sha256sum <file>` | 计算 SHA256 哈希 |
| `seq [start] end [step]` | 生成数字序列 |
| `yes [text]` | 重复输出文本 |
| `true/false` | 返回成功/失败状态 |
| `man <cmd>` | 显示命令帮助 |
| `config [list\|get\|set\|reset]` | 管理终端设置 |
| `help` | 显示帮助 |
| `exit` | 退出终端 |

## 常用选项

- `-l, --long` - 显示详细信息
- `-a, --all` - 显示隐藏文件
- `-r, --recursive` - 递归操作
- `-f, --force` - 强制操作
- `-i` - 忽略大小写 (grep)
- `-n` - 显示行号
- `-h` - 人类可读大小 (du/df)
- `-c` - 统计计数 (grep/wc)

## 示例

### 基本用法

```bash
# 列出当前目录
ls

# 列出详细信息
ls -l

# 显示隐藏文件
ls -la

# 创建目录
mkdir mydir

# 进入目录
cd mydir

# 创建文件
touch test.txt

# 写入内容
echo "Hello, KShell!" > test.txt

# 查看内容
cat test.txt

# 复制文件
cp test.txt test_copy.txt

# 删除文件
rm test_copy.txt

# 返回上级目录
cd ..

# 删除目录
rmdir mydir
```

### 使用别名

```bash
# 设置别名
alias ll='ls -la'

# 使用别名
ll

# 删除别名
unalias ll
```

### 权限提升 (sudo)

```bash
# Windows: 触发 UAC 以管理员身份运行 (弹出确认窗口)
sudo dir C:\

# Unix/Linux/macOS: 调用系统 sudo
sudo ls /root
sudo systemctl restart nginx
```

> Windows 下 `sudo` 会弹出 UAC 确认窗口，命令在新的提升权限窗口中执行；
> Unix 下直接调用系统 `sudo`，按提示输入密码。

### 文本搜索和统计

```bash
# 搜索文件内容
grep error app.log

# 忽略大小写 + 显示行号
grep -in error app.log

# 递归搜索目录
grep -r "class" .

# 统计行数/字数/字节
wc -l app.log

# 查看日志文件头部/尾部
head -n 20 app.log
tail -n 50 app.log
```

### 查找文件

```bash
# 按名字查找
find . -name "*.py"

# 只找目录
find . -type d

# 限制深度
find . -name "*.txt" -maxdepth 2
```

### 管道（基础支持）

```bash
# 列出文件并分页显示
ls -l | more
```

### 重定向

```bash
# 输出重定向
echo "Hello" > output.txt

# 追加输出
echo "World" >> output.txt

# 查看文件
cat output.txt
```

## 脚本示例

创建一个脚本文件 `example.ksh`：

```bash
#!/usr/bin/env kshell
# 示例脚本

echo "开始执行脚本"
echo "当前目录:"
pwd
echo ""
echo "目录内容:"
ls -l
echo "脚本执行完成"
```

运行脚本：

```bash
python kshell.py example.ksh
```

## 设置与配置

KShell 使用 JSON 文件 (`kshell_config.json`) 来保存配置。配置文件会在首次运行时自动创建。

### 使用 `config` 命令

```bash
# 列出所有设置
config list

# 查看特定设置
config get prompt_style

# 修改设置（支持自动类型推断）
config set prompt_style poweruser
config set history_size 2000
config set banner_enabled false

# 重置为默认设置
config reset
```

### 可用的设置项

| 设置项 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `banner_enabled` | bool | true | 是否显示启动横幅 |
| `history_size` | int | 1000 | 命令历史最大条数 |
| `prompt_style` | string | default | 提示符样式 (default/simple/poweruser) |
| `use_colors` | bool | true | 是否使用颜色 (预留) |
| `welcome_message` | string | Welcome... | 启动欢迎消息 |

### 提示符样式

- **default**: 标准提示符 `user@path>` (Windows) 或 `user:path$` (Unix)
- **simple**: 极简提示符 `$`
- **poweruser**: 包含时间和主机名 `[HH:MM] user@host:path\n$`

### 持久化别名

使用 `alias` 命令设置的别名现在会自动保存到配置文件中，下次启动时自动加载。

```bash
# 设置别名（会自动保存）
alias ll='ls -la'

# 查看所有别名（包括持久化的）
alias
```

## 主题功能

KShell 内置 6 种颜色主题，可随时切换并持久化保存。

### 使用 theme 命令

```bash
# 查看当前主题
theme

# 列出所有主题
theme list

# 预览所有主题的颜色方案（色块展示）
theme preview

# 切换主题（自动保存，重启后依然生效）
theme ocean
theme monokai
```

### 可用主题

| 主题 | 风格 |
|------|------|
| `default` | 默认（绿/蓝经典配色） |
| `dark` | 暗色（高亮亮色系） |
| `light` | 亮色（适合浅色背景终端） |
| `ocean` | 海洋（蓝色系） |
| `monokai` | Monokai（高饱和霓虹风） |
| `solarized` | Solarized（暖色调） |

### 通过 config 切换

```bash
# 查看当前主题设置
config get theme

# 切换主题（与 theme 命令等效）
config set theme ocean

# 关闭颜色（管道/重定向场景自动禁用，也可手动关闭）
config set use_colors false
```

### 颜色应用范围

- 启动横幅（logo 和标题）
- 提示符（用户名/目录/符号）
- `ls` 输出（目录蓝色加粗、链接青色、文件白色）
- `help` 输出（分类标题着色）
- 主题预览色块

> 重定向输出到文件时会自动清理 ANSI 颜色码，不会污染文件内容。

## v2.0 新特性

### 1. 系统 PATH 命令直接使用

系统 PATH 中的任何命令都可以直接输入执行，无需额外配置：

```bash
git status          # 直接调用系统 git
python --version    # 直接调用系统 python
ipconfig /all       # Windows 命令（含选项完整透传）
docker ps           # 任意已安装的命令
```

v2.0 会自动扫描 PATH 建立命令索引，并识别 Windows 的 `PATHEXT`（.exe/.cmd/.bat/.com）。
未命中的命令会按间隔自动重新扫描，新安装的软件无需重启 KShell。

### 2. 内置命令优先于系统命令

当同名命令同时存在于 KShell 内置和系统 PATH 时，**优先执行 KShell 的内置实现**：

```bash
ls -l          # 走 KShell 内置 ls（不是系统的 ls）
grep foo f.txt # 走 KShell 内置 grep
```

如需强制执行系统版本，使用 `command` 绕过（bash 风格）：

```bash
command ls -l  # 强制使用系统 ls
command find . # 强制使用系统 find
```

切换优先级（系统命令优先，不存在时回退内置）：

```bash
config set builtin_priority false
```

### 3. 新增 `path` 命令

```bash
path                  # 列出 PATH 目录 + 系统/内置命令总数
path -s <关键字>       # 搜索系统命令
path -b               # 查看被内置命令优先接管的系统命令
path -a <目录>         # 添加 PATH 目录（当前会话）
path -r <目录>         # 移除 PATH 目录（当前会话）
path -F               # 强制重新扫描系统命令
```

### 4. 其它改进

- **选项完整透传**：修复了系统命令选项被解析器丢弃的问题（`ping -n 2` 不再丢失 `-n`）
- **管道数据真正传递**：`内置命令 | 系统命令` 可混合使用，上游输出作为下游标准输入
- **Windows cmd 内部命令**：`dir`、`ver`、`title`、`color` 等非可执行文件命令也可调用
- **非 UTF-8 输出解码**：使用 `errors='replace'`，避免 GBK 输出导致崩溃
- **`ls <文件>`**：现在可以列出单个文件（此前对文件路径无输出）
- **新增 `calc` 计算器**：基于 AST 安全求值，支持 `+ - * / // % **` 和括号
- **`which -a`**：同时显示内置命令与系统命令路径

## 架构说明

### 模块结构

- `kplatform.py` - 平台检测和底层接口抽象（命名避免与标准库冲突）
- `syscmd.py` - **v2.0** 系统 PATH 命令解析（PATH 扫描、PATHEXT、cmd 内部命令、遮蔽报告）
- `filesystem.py` - 文件系统操作（使用 pathlib 和 shutil）
- `parser.py` - 命令解析器（含 `raw_split` 原始参数切分）
- `process.py` - 进程管理（使用 subprocess，完整 argv 透传）
- `builtin.py` - 内置命令实现
- `commands_extra.py` - 扩展命令（`path`、`calc` 等）
- `theme.py` - 颜色主题（ANSI 转义码 + 预设主题）
- `settings.py` - 设置和配置管理（JSON 存储）
- `banner.py` - 启动横幅和 ASCII 艺术
- `terminal.py` - 终端核心逻辑
- `kshell.py` - 启动脚本

### 设计原则

1. **不使用 os 库**：使用 pathlib、shutil、subprocess 等标准库替代
2. **跨平台**：自动检测平台并适配不同系统
3. **模块化**：各功能独立模块，易于扩展
4. **纯 Python**：无外部依赖，开箱即用

## 平台兼容性

- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Linux (主流发行版)

## 打包发布

### Windows (已打包)

```bash
dist\kshell.exe              # 交互模式
dist\kshell.exe script.ksh   # 脚本模式
```

重新打包：`packaging\build_windows.bat`

### Linux

在 Linux 机器上运行 `packaging/build_linux.sh`，可生成：
- 原生二进制 `kshell`
- `.deb` 安装包（`sudo dpkg -i kshell_1.0.0_amd64.deb`）
- `.tar.gz` 压缩包

### 源码包（跨平台）

```bash
bash packaging/build_src.sh
```

详见 `packaging/README.md`。

## 注意事项

1. 部分高级功能（如复杂的管道、后台任务）可能有限制
2. 外部命令执行依赖于系统 PATH
3. Windows 下某些 Unix 风格命令可能不可用

## 开发

### 运行测试

```bash
python test.py
```

### 添加新命令

在 `builtin.py` 中添加新命令方法，然后在 `__init__` 中注册：

```python
def cmd_mycommand(self, args: List[str], options: dict) -> Tuple[int, str]:
    # 实现命令逻辑
    return 0, "Output"

# 在 __init__ 中注册
self.commands['mycommand'] = self.cmd_mycommand
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！