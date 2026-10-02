# KShell 2.0.0 版本文档

> **版本**：2.0.0  
> **发布日期**：2026-10-02  
> **开源协议**：[Apache License 2.0](LICENSE)  
> **支持平台**：Windows 10/11 · macOS 10.15+ · Linux（主流发行版）  
> **运行环境**：Python 3.6+（核心零第三方依赖）

---

## 目录

- [一、版本概览](#一版本概览)
- [二、版本亮点](#二版本亮点)
- [三、新特性详解](#三新特性详解)
- [四、缺陷修复](#四缺陷修复)
- [五、命令参考](#五命令参考)
- [六、配置项](#六配置项)
- [七、架构变化](#七架构变化)
- [八、从 1.0 升级](#八从-10-升级)
- [九、安装方式](#九安装方式)
- [十、测试与验证](#十测试与验证)
- [十一、已知限制](#十一已知限制)

---

## 一、版本概览

KShell 2.0.0 是继 1.0.0 之后的第一个功能版本，核心主题是**打通与操作系统命令行的边界**。

1.0 版本已经实现了完整的终端框架（解析、内置命令、主题、配置、脚本），但它与系统命令之间存在明显的割裂：系统命令的选项会被解析器丢弃，管道不能传递数据，Windows 的 `dir`、`ver` 等命令完全无法调用。

2.0.0 解决的就是这些问题，并确立了明确的命令优先级规则。

| 项目 | 1.0.0 | 2.0.0 |
|------|-------|-------|
| 内置命令数量 | 66 | **68** |
| 系统命令直通 | 部分（选项会丢失） | **完整（argv 透传）** |
| 内置/系统优先级 | 隐含，不可配置 | **显式规则 + 可配置** |
| Windows cmd 内部命令 | 不支持 | **支持 42 个** |
| 管道数据传递 | 不传递 | **上游输出作为下游 stdin** |
| 强制系统命令 | 无 | **`command` 内置命令** |
| 新增命令 | — | **`path`、`calc`** |

---

## 二、版本亮点

1. **系统 PATH 命令直接使用** — 系统里装了什么就能用什么，`git`、`docker`、`python`、`ipconfig` 一律直通，选项完整保留。
2. **内置命令优先** — 同名命令优先走 KShell 自己的实现，行为可预测；需要系统版本时用 `command` 绕过。
3. **新增 `path` 命令** — 查看/搜索/管理 PATH，并可视化"哪些系统命令被内置命令接管"。
4. **新增 `calc` 命令** — 基于 AST 安全求值的计算器，支持运算符优先级与括号。
5. **新增 `syscmd.py` 模块** — 独立的系统命令解析层，启动扫描 PATH 并建立索引。
6. **修复 7 项缺陷** — 其中"外部命令选项被丢弃"和"管道不传数据"是影响最大的两个。

---

## 三、新特性详解

### 3.1 系统 PATH 命令直通

系统 PATH 中的任何命令都可以直接输入执行，无需任何配置或包装。

```bash
git status                  # 调用系统 git
python --version            # 调用系统 python
ipconfig /all               # Windows 命令，选项完整透传
docker ps -a                # 任意已安装命令
ping -n 2 127.0.0.1         # -n 2 不会丢失
```

**实现原理**（`syscmd.py`）：

- 启动时扫描 `PATH` 的所有目录，建立 `命令名 → 可执行文件路径` 索引
- Windows 下识别 `PATHEXT` 扩展名（`.exe` / `.cmd` / `.bat` / `.com` 等）
- Windows 下额外注册 `cmd.exe` 内部命令（`dir`、`ver`、`title`、`color` 等 42 个，磁盘上没有对应文件）
- 命令未命中时，按 **5 秒间隔**惰性重新扫描，因此新安装的软件无需重启 KShell

**注意**：命令名在 Unix 下区分大小写，在 Windows 下不区分。PATH 中靠前的目录优先。

### 3.2 内置命令优先

当同名命令**同时**存在于 KShell 内置和系统 PATH 时，默认执行 KShell 的内置实现。

```bash
ls -l            # 走 KShell 内置 ls
grep foo f.txt   # 走 KShell 内置 grep
find . -name a   # 走 KShell 内置 find
```

**为什么要这样做**：内置实现行为确定、输出统一（含主题着色）、且不依赖系统是否安装了 GNU 工具链。在 Windows 上尤其重要——系统根本没有 `ls`、`grep`。

**强制执行系统版本**（bash 风格的 `command` 内置命令）：

```bash
command ls -l    # 强制系统 ls
command find .   # 强制系统 find
command dir      # 走 cmd.exe 的 dir
```

**切换优先级规则**：

```bash
config set builtin_priority false   # 改为系统命令优先（系统没有时回退内置）
config set builtin_priority true    # 恢复默认：内置优先
```

**查看哪些命令被接管**：

```bash
path -b
```

### 3.3 `path` 命令（新增）

管理并检视系统 PATH。

| 用法 | 说明 |
|------|------|
| `path` | 列出所有 PATH 目录（标注不存在的目录）+ 系统/内置命令总数 |
| `path -s <关键字>` | 搜索系统命令，标注 `[内置优先]` 与被接管的命令 |
| `path -b` | 列出所有被内置命令优先接管的系统命令 |
| `path -a <目录>` | 向 PATH 添加目录（仅当前会话） |
| `path -r <目录>` | 从 PATH 移除目录（仅当前会话） |
| `path -F` | 强制重新扫描系统命令 |

示例：

```bash
$ path
PATH 目录（共 12 个）:
   1. C:\WINDOWS\system32
   2. C:\WINDOWS
   ...
  12. C:\Users\me\AppData\Local\Microsoft\WindowsApps

系统命令总数: 4832
内置命令总数: 68
提示: path -s <关键字> 搜索系统命令 | path -b 查看被接管的命令

$ path -s git
  git
    C:\Program Files\Git\cmd\git.exe
  共 1 条
```

> `path -a` / `path -r` 的修改仅对当前会话有效，不会写入系统环境变量。

### 3.4 `calc` 命令（新增）

内置计算器，使用 **AST 安全求值**，不使用 `eval`。

```bash
$ calc 1+2*3
7
$ calc (1+2)*3
9
$ calc 2**10
1024
$ calc 10/4
2.5
$ calc 10//3
3
$ calc 7%3
1
```

支持的运算符：`+` `-` `*` `/` `//` `%` `**` 与括号。

仅允许数字常量与算术运算，函数调用、属性访问、导入语句一律拒绝：

```bash
$ calc __import__("os").system("rm -rf /")
计算错误: 表达式包含不支持的语法
```

### 3.5 管道数据真正传递

上游命令的输出作为下游命令的标准输入，内置命令与系统命令可以自由混合。

```bash
ls | findstr .py                 # 内置 ls → 系统 findstr
cat app.log | grep ERROR | head  # 内置 cat → 内置 grep → 内置 head
python gen.py | sort | uniq      # 系统 python → 内置 sort → 内置 uniq
```

---

## 四、缺陷修复

| # | 问题 | 影响 | 修复方式 |
|---|------|------|---------|
| 1 | **外部命令选项被解析器丢弃** | `ping -n 2 host` 实际执行 `ping 2 host`；`git --version` 参数丢失 | 新增 `CommandParser.raw_split()`，把别名展开后的原始 token 列表完整透传给系统命令 |
| 2 | **管道不传递数据** | `ls \| findstr .py` 的上游输出被直接丢弃，下游读不到数据 | `run_system()` 新增 `stdin_data` 参数，上游输出作为下游 `input` |
| 3 | **`ls <文件>` 无输出** | 对单个文件路径执行 `ls` 返回空，与 GNU 行为不符 | `FileSystem.list_dir()` 检测文件目标并返回文件自身；`cmd_ls` 同步修正路径拼接 |
| 4 | **非 UTF-8 输出导致崩溃** | Windows 下 GBK 编码输出触发 `UnicodeDecodeError` | `subprocess.run()` 增加 `errors='replace'` |
| 5 | **`calc` 未注册且调用不存在的 API** | 命令落到系统 `calc.exe`，在受限环境下报 `WinError 5` | 正式注册命令，并改用以 `ast` 为基础的安全求值器；修正为 `theme.colorize(text, 'error')` |
| 6 | **`ExtraCommands` 缺少 `theme` 属性** | 任何使用主题着色的扩展命令都会 `AttributeError` | `__init__` 中补充 `self.theme = getattr(builtin, 'theme', None)` |
| 7 | **命令不存在时返回码不准** | 统一返回 `1`，无法与一般错误区分 | 返回标准的 **127**（命令不存在）、**126**（权限不足）、**130**（被中断） |

---

## 五、命令参考

### 5.1 内置命令（36 条）

| 分类 | 命令 |
|------|------|
| 目录操作 | `cd` `pwd` `ls` `dir` `clear` `cls` |
| 文件操作 | `mkdir` `md` `rmdir` `rd` `rm` `del` `cp` `copy` `mv` `move` `cat` `type` `touch` |
| 输出 | `echo` |
| 会话 | `history` `exit` `quit` |
| 帮助与配置 | `help` `config` `theme` |
| 环境变量 | `env` `set` `unset` `export` |
| 别名 | `alias` `unalias` |
| 系统信息 | `date` `time` `whoami` `hostname` |

> `dir` `cls` `md` `rd` `del` `copy` `move` `type` 是 Windows 风格别名，分别映射到 `ls` `clear` `mkdir` `rmdir` `rm` `cp` `mv` `cat`。

### 5.2 扩展命令（32 条）

| 分类 | 命令 |
|------|------|
| 权限 | `sudo` |
| 文本处理 | `head` `tail` `grep` `wc` `sort` `uniq` `nl` `tee` |
| 查找与信息 | `find` `tree` `stat` `du` `df` `which` |
| 系统 | `ps` `kill` `sleep` `uptime` `uname` `id` |
| 工具 | `base64` `md5sum` `sha256sum` `sha1sum` `seq` `yes` `true` `false` `man` |
| **v2.0 新增** | **`path`** **`calc`** |

### 5.3 系统命令（数量取决于环境）

任何存在于 PATH 中的可执行文件都可直接调用，无需登记。Windows 下额外支持 `cmd.exe` 内部命令：

```
assoc  break  call  chdir  cls   color  copy   date   del    dir
echo   endlocal  erase  exit   for   ftype  goto   if     md     mkdir
mklink move   path   pause  popd  prompt pushd  rd     rem    ren
rename rmdir  set    setlocal shift start  time   title  type   ver
verify vol
```

### 5.4 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 成功 |
| `1` | 一般错误 |
| `126` | 权限不足 |
| `127` | 命令不存在 |
| `130` | 被 Ctrl+C 中断 |
| `-1` | KShell 内部信号（`exit` 命令，退出终端） |

退出码由终端内部记录（`Terminal.exit_code`）。当前版本**未实现 `$?` 变量展开**，因此脚本中无法直接读取上一条命令的退出码。

---

## 六、配置项

配置文件位于**当前工作目录**下的 `kshell_config.json`（v2.0 起不再纳入版本控制）。

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `banner_enabled` | bool | `true` | 是否显示启动横幅 |
| `history_size` | int | `1000` | 命令历史保留条数 |
| `prompt_style` | string | `default` | 提示符样式：`default` / `simple` / `poweruser` |
| `use_colors` | bool | `true` | 是否启用 ANSI 颜色（管道/重定向时自动关闭） |
| `welcome_message` | string | `Welcome to KShell!` | 自定义欢迎语（保持默认值则不额外显示） |
| `aliases` | object | `{}` | 持久化别名表，重启后仍生效 |
| `environment` | object | `{}` | 自定义环境变量 |
| `theme` | string | `default` | 颜色主题 |
| **`builtin_priority`** | bool | `true` | **v2.0 新增**：内置命令是否优先于系统同名命令 |

### 内置主题（6 套）

`default` · `dark` · `light` · `ocean` · `monokai` · `solarized`

```bash
theme list          # 列出所有主题
theme preview       # 预览所有主题配色
theme ocean         # 切换到 ocean
```

### 配置操作

```bash
config              # 列出所有配置
config get theme    # 读取单项
config set theme ocean           # 修改
config set builtin_priority false  # 切换优先级规则
config reset        # 恢复默认
```

---

## 七、架构变化

### 7.1 模块结构

```
kshell.py                  程序入口（交互模式 / 脚本模式）
  │
  └── terminal.py          调度中枢：主循环、优先级派发、管道、重定向
        │
        ├── syscmd.py      【v2.0 新增】系统 PATH 命令解析
        │                    · SystemCommandResolver  —— PATH 扫描与索引
        │                    · SystemCommand          —— 命令描述（可执行/cmd内部）
        │                    · WINDOWS_CMD_BUILTINS    —— cmd.exe 内部命令集合
        │
        ├── process.py     进程管理：run_system() 完整 argv 透传
        ├── parser.py      命令解析：parse() 选项提取 + raw_split() 原始切分
        ├── filesystem.py  文件系统：pathlib + shutil
        ├── builtin.py     36 条内置命令
        ├── commands_extra.py  32 条扩展命令（含 path、calc）
        ├── settings.py    配置持久化（JSON）
        ├── theme.py       6 套主题与 ANSI 着色
        ├── banner.py      启动横幅
        └── kplatform.py   平台抽象（避免与标准库 platform 冲突）
```

### 7.2 命令派发流程

```
用户输入
   │
   ▼
parser.expand_alias()          别名展开
   │
   ├──► parser.raw_split()     → 原始 token 列表（供系统命令透传）
   └──► parser.parse()         → (命令, 位置参数, 选项字典)（供内置命令使用）
   │
   ▼
terminal._execute_command()
   │
   ├─ command == 'command' ？ → 强制走系统命令
   │
   ├─ builtin_priority == true（默认）
   │     ├─ 是内置命令 → builtin.execute()
   │     └─ 否         → process_manager.run_system()
   │
   └─ builtin_priority == false
         ├─ PATH 中存在该命令 → run_system()
         ├─ 否则是内置命令    → builtin.execute()
         └─ 都不是            → 返回 127
   │
   ▼
输出处理
   ├─ 有重定向 → strip_ansi() 去色后写入文件
   └─ 无重定向 → 打印（echo -n 不补换行）
```

### 7.3 关键设计决策

**为什么解析两遍？** 内置命令需要结构化的 `选项字典`（如 `ls -la` → `{l: True, a: True}`），而系统命令需要**原封不动的 argv**（如 `ping -n 2` 中 `-n` 必须带值）。1.0 用同一套解析结果服务两者，导致系统命令选项丢失。2.0 改为 `parse()` + `raw_split()` 双通道，各取所需。

**为什么内置优先而非系统优先？** Windows 上没有 `ls`/`grep`/`sort`，若系统优先，同一份脚本在 Linux 与 Windows 上行为不一致。内置优先保证了跨平台一致性，同时用 `command` 提供逃生舱。

---

## 八、从 1.0 升级

### 8.1 兼容性

✅ **配置文件向后兼容** — 1.0 的 `kshell_config.json` 可直接使用，缺失的键（如 `builtin_priority`）会自动补默认值。

✅ **命令语法兼容** — 所有 1.0 命令的参数形式不变。

✅ **脚本文件兼容** — `.ksh` 脚本无需修改。

### 8.2 行为变更（需注意）

| 变更 | 1.0 行为 | 2.0 行为 | 影响 |
|------|---------|---------|------|
| 系统命令选项 | 被丢弃 | 完整传递 | 之前"看似生效"的命令现在会真正带选项执行 |
| 管道 | 不传数据 | 传递数据 | 之前输出全部内容，现在会被下游过滤 |
| 命令不存在 | 返回 1 | 返回 127 | 依赖退出码判断的脚本需调整 |
| `ls <文件>` | 无输出 | 输出该文件 | 属于修复 |
| `calc` | 落到系统 `calc.exe` | KShell 内置计算器 | 如需系统计算器用 `command calc` |
| `kshell_config.json` | 纳入版本控制 | 已 gitignore | 克隆后首次运行自动生成 |

### 8.3 升级步骤

**Windows（可执行文件）**

```bat
:: 1. 备份配置
copy kshell_config.json kshell_config.json.bak

:: 2. 替换 exe
::    下载 kshell_windows_x64_v2.0.exe 覆盖旧的 kshell.exe

:: 3. 验证
kshell.exe
```

**Linux（deb 包）**

```bash
sudo apt update && sudo apt install --only-upgrade kshell
# 或
sudo dpkg -i kshell_2.0.0_amd64.deb
```

**验证升级成功**

```bash
kshell          # 横幅应显示 KShell v2.0
path -b         # 应输出被接管的系统命令清单
calc 1+1        # 应输出 2
```

---

## 九、安装方式

### Windows

```bat
kshell_windows_x64_v2.0.exe            :: 交互模式
kshell_windows_x64_v2.0.exe script.ksh :: 脚本模式
```

重新构建：

```bat
packaging\build_windows.bat
```

### Linux — APT 仓库

```bash
echo "deb [trusted=yes] http://39.96.82.163/apt stable main" | sudo tee /etc/apt/sources.list.d/kshell.list
sudo apt update
sudo apt install -y kshell
```

### Linux — deb 包

```bash
sudo dpkg -i kshell_2.0.0_amd64.deb
sudo apt-get install -f -y     # 如有依赖缺失
```

### 源码运行

```bash
python3 kshell.py            # 交互模式
python3 kshell.py script.ksh # 脚本模式
```

从源码构建 Linux 安装包：

```bash
pip3 install pyinstaller
bash packaging/build_linux.sh   # 生成二进制 + .deb + .tar.gz
```

---

## 十、测试与验证

| 测试套件 | 覆盖范围 | 结果 |
|---------|---------|------|
| `test_v2_syscmd.py` | **v2.0 新增**：PATH 解析、选项透传、优先级派发、`command` 绕过、`path` 三个子功能、`calc` 求值与注入拒绝、`raw_split` | **27 项通过 / 0 失败** |
| `test.py` | 平台抽象、文件系统、命令解析、内置命令 | 通过 |
| `test_extra.py` | 扩展命令（文本处理、查找、系统、哈希） | 通过 |
| 端到端（编译后 exe） | 8 个真实场景：系统命令、选项、内置优先、`command`、`path`、`calc`、管道、错误处理 | 全部通过 |

端到端测试脚本：[test_v2_terminal.ksh](test_v2_terminal.ksh)

---

## 十一、已知限制

1. **管道为串行传递，不是真正的并发管道** — 上游命令完整执行完毕后才把输出交给下游，不支持流式处理，因此 `yes | head` 这类无限输出的管道会挂起。
2. **不支持 `&&` / `||` 逻辑运算符与 `;` 命令分隔符** — 需要多命令串联时请使用 `.ksh` 脚本文件。
3. **通配符 `*` 不做自动展开** — `*` 会原样传给命令，由命令自身（如系统 `dir`）或 KShell 的 `find` 处理。
4. **交互式程序受限** — 输出被捕获，`vim`、`top`、`less` 等需要真实 TTY 的程序无法正常交互。
5. **Windows cmd 内部命令需间接调用** — `dir`、`ver` 等通过 `cmd /c` 执行，行为与原生 cmd 略有差异（如管道语义）。
6. **内置命令遮蔽同名系统命令** — 需要系统版本时必须显式使用 `command <cmd>`。
7. **权限操作受限** — `sudo` 命令在 Windows 下无效；Linux 下依赖系统 `sudo` 配置。
8. **`path -a` / `path -r` 仅当前会话有效** — 不会持久化到系统环境变量或配置文件。

---

## 附录：v2.0.0 变更文件清单

**新增**

| 文件 | 说明 |
|------|------|
| `syscmd.py` | 系统 PATH 命令解析模块 |
| `test_v2_syscmd.py` | v2.0 特性测试（27 项） |
| `test_v2_terminal.ksh` | v2.0 端到端测试脚本 |
| `packaging/` | 构建脚本（Windows / Linux / 源码包 / APT 仓库 / 部署模板） |

**修改**

| 文件 | 主要变更 |
|------|---------|
| `terminal.py` | 优先级派发、`command` 绕过、管道数据传递、原始参数透传 |
| `parser.py` | 新增 `expand_alias()` 与 `raw_split()` |
| `process.py` | 集成 `SystemCommandResolver`、新增 `run_system()`、标准退出码 |
| `commands_extra.py` | 新增 `path`、`calc`、增强 `which`、补充 `theme` 属性 |
| `builtin.py` | 帮助文本更新、`ls` 单文件路径修复 |
| `filesystem.py` | `list_dir()` 支持文件目标 |
| `settings.py` | 新增 `builtin_priority` 默认配置 |
| `banner.py` | 默认版本号更新为 2.0 |
| `kshell.spec` | 打包清单加入 `syscmd` |
| `README.md` / `STRUCTURE.md` | v2.0 文档与模块说明 |
| `.gitignore` | 忽略 `kshell_config.json` 与临时目录 |

---

**KShell 2.0.0** — 一个用纯 Python 写的、能跑在三类系统上的轻量终端，现在可以和系统命令行无缝协作了。
