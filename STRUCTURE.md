# KShell 项目结构说明

## 文件清单

### 核心模块
- `kplatform.py` - 平台检测和底层接口抽象
  - 检测操作系统类型（Windows/MacOS/Linux）
  - 提供路径分隔符、环境变量分隔符等平台相关配置
  - 获取默认 shell 和用户主目录
  - （命名为 kplatform 以避免与标准库 platform 模块冲突）

- `syscmd.py` - **v2.0** 系统 PATH 命令解析
  - 扫描 PATH 建立命令索引（识别 PATHEXT 扩展名）
  - 识别 Windows cmd.exe 内部命令（dir/ver/title 等）
  - 提供遮蔽报告（哪些系统命令被内置命令优先接管）

- `version.py` - **v2.1** 版本号单一来源
  - `VERSION` / `VERSION_SHORT` 常量，避免各处硬编码
  - `check_requirement()` 版本要求表达式校验（供插件系统使用）

- `pluginmgr.py` - **v2.1** 插件系统核心
  - `PluginManager` —— 插件发现、加载、注册、配置、脚手架
  - `Plugin` / `PluginCommand` —— 插件与命令描述
  - `PluginContext` —— 传给插件函数的上下文（ctx）
  - `PLUGIN_STDLIB_HINTS` —— 打包时需包含的插件常用标准库清单
  - 关键设计：源码 `compile()` + `exec()` 加载，绕过 .pyc 缓存以保证热重载准确

- `commands_plugin.py` - **v2.1** `plugin` 命令组
  - list / info / enable / disable / reload / config / dirs / new / help

- `plugins/` - **v2.1** 官方示例插件
  - `hello/` 入门示例（配置读取、选项、回调、别名）
  - `pwgen/` 多命令示例（密码/UUID/强度评估，secrets 加密安全随机）
  - `sysinfo/` 结构化输出示例（--json、配置开关、优雅降级）

- `filesystem.py` - 文件系统操作模块
  - 实现目录切换、文件列表、创建/删除等操作
  - 使用 pathlib 和 shutil 替代 os 库
  - 支持文件复制、移动、读写等操作

- `parser.py` - 命令解析器
  - 解析用户输入的命令
  - 支持参数、选项、引号、通配符
  - 支持管道和重定向解析
  - 支持命令别名

- `process.py` - 进程管理模块
  - 使用 subprocess 执行外部命令
  - 管理环境变量
  - 查找命令路径
  - 运行脚本文件

- `builtin.py` - 内置命令实现
  - 实现 25+ 个核心内置命令
  - 包括文件操作、系统信息、环境变量管理等
  - 支持命令历史记录
  - 集成 `config` 命令用于管理设置

- `commands_extra.py` - 扩展命令实现
  - 实现 30+ 个扩展命令
  - 包括 sudo、head/tail/grep、find/tree、ps/kill、哈希工具等
  - 自动注册到内置命令表

- `settings.py` - 设置管理模块
  - 使用 JSON 文件 (`kshell_config.json`) 持久化配置
  - 管理启动横幅、历史大小、提示符样式、主题等
  - 支持别名的持久化存储

- `theme.py` - 颜色主题模块
  - 定义 ANSI 转义码常量和 6 种预设主题
  - ThemeManager 提供着色、主题切换、色块预览
  - Windows 自动启用 VT100 支持
  - strip_ansi 清理颜色码（重定向写入时使用）

- `banner.py` - 启动横幅模块
  - 生成 ASCII 艺术启动画面（支持主题着色）
  - 显示平台信息和版本号

- `terminal.py` - 终端核心逻辑
  - 主终端循环
  - 命令执行调度
  - 提示符生成（支持多样式 + 主题颜色）
  - 管道和重定向处理（重定向自动清理 ANSI）
  - 初始化设置、主题和加载持久化别名

### 启动脚本
- `kshell.py` - Python 启动脚本
- `kshell.bat` - Windows 批处理启动脚本
- `kshell.sh` - Unix/Linux/macOS Shell 启动脚本

### 测试和示例
- `test.py` - 核心功能测试套件
- `test_extra.py` - 扩展命令测试
- `example.ksh` - 示例脚本
- `README.md` - 项目文档

### 其他
- `.gitignore` - Git 忽略文件配置

## 架构设计

### 设计原则
1. **不使用 os 库** - 使用 pathlib、shutil、subprocess 等标准库
2. **跨平台** - 自动适配 Windows/MacOS/Linux
3. **模块化** - 每个模块职责单一，易于扩展
4. **纯 Python** - 无外部依赖，开箱即用

### 模块依赖关系
```
kshell.py (入口)
    └── terminal.py (核心)
        ├── kplatform.py (平台抽象)
        ├── filesystem.py (文件系统)
        ├── parser.py (命令解析)
        ├── process.py (进程管理)
        ├── settings.py (设置管理)
        ├── theme.py (颜色主题)
        ├── banner.py (启动画面)
        ├── builtin.py (内置命令)
        │   └── commands_extra.py (扩展命令)
        └── (builtin depends on) settings.py + theme.py
```

### 数据流
```
启动时:
terminal.__init__()
    ├── settings.load() → 读取 kshell_config.json
    ├── 加载持久化别名到 parser
    └── 初始化 builtin (传入 settings 和 parser)

运行中:
用户输入 → parser.parse() → terminal._process_input()
    ↓
builtin.execute() 或 process_manager.execute()
    ↓
filesystem 操作 或 subprocess 调用
    ↓
输出结果 → 显示或重定向

设置修改:
config set <key> <value> → settings.set() → 写入 kshell_config.json
```

## 设置系统架构

### 配置文件

设置存储在项目根目录的 `kshell_config.json` 文件中，首次运行时自动创建。

### 默认设置

```json
{
    "banner_enabled": true,
    "history_size": 1000,
    "prompt_style": "default",
    "use_colors": true,
    "welcome_message": "Welcome to KShell!",
    "aliases": {},
    "environment": {},
    "theme": "default"
}
```

### 设置管理流程

```
SettingsManager (settings.py)
    ├── load()    - 读取 JSON 文件，合并默认值
    ├── save()    - 写回 JSON 文件
    ├── get()     - 读取单个设置
    ├── set()     - 修改设置并保存
    └── reset()   - 恢复默认设置
```

### config 命令用法

| 动作 | 用法 | 说明 |
|------|------|------|
| list | `config list` | 列出所有设置 |
| get | `config get <key>` | 查看单个设置 |
| set | `config set <key> <value>` | 修改设置（自动推断类型） |
| reset | `config reset` | 重置所有设置为默认 |

### 类型推断

`config set` 会自动推断值的类型：
- `true/false/yes/no/1/0` → 布尔值
- 纯数字 → 整数
- 小数 → 浮点数
- 其他 → 字符串

### 提示符样式

| 样式 | 格式 | 示例 |
|------|------|------|
| default | 平台默认 | `user@D:\path> ` 或 `user:~/path$ ` |
| simple | 极简 | `$ ` |
| poweruser | 增强显示 | `[14:30] user@host:/path\n$ ` |

### 别名持久化

- `alias ll='ls -la'` → 保存到 `kshell_config.json` 的 `aliases` 字段
- 下次启动时自动加载
- `unalias ll` → 同时从运行时和配置文件移除

## 主题系统架构

### 主题模块

```
theme.py
    ├── ANSI 颜色常量 (FG/BG/BOLD/RESET 等)
    ├── THEMES 字典 (6 种预设主题)
    ├── ThemeManager
    │   ├── colorize(text, key) - 为文本着色
    │   ├── set_theme(name)     - 切换主题
    │   ├── list_themes()       - 列出主题
    │   └── preview()           - 生成色块预览
    ├── enable_ansi_windows()   - Windows 启用 VT100
    ├── supports_color()        - 检测终端颜色支持
    └── strip_ansi(text)        - 清理 ANSI 码
```

### 主题切换流程

```
theme ocean
    → builtin.cmd_theme()
    → ThemeManager.set_theme('ocean')
    → settings.set('theme', 'ocean') → 写入 kshell_config.json
    → 重启终端自动加载
```

### 颜色应用位置

| 位置 | 颜色键 |
|------|--------|
| 启动横幅 | banner_logo, banner_title, banner_info |
| 提示符 | prompt_user, prompt_dir, prompt_sym |
| ls 输出 | dir, file, link |
| help 输出 | title, banner_title |
| theme preview | 所有颜色键色块 |

### 颜色自动禁用

- 管道/重定向输出时（非 tty）自动禁用颜色
- 设置 `NO_COLOR` 环境变量可全局禁用
- 重定向写入文件前自动 strip_ansi

## 支持的命令

### 文件操作
- `cd` - 改变目录
- `ls/dir` - 列出目录
- `pwd` - 显示当前目录
- `mkdir/md` - 创建目录
- `rmdir/rd` - 删除目录
- `rm/del` - 删除文件
- `cp/copy` - 复制文件
- `mv/move` - 移动文件
- `cat/type` - 显示文件内容
- `touch` - 创建空文件
- `head` - 显示文件开头
- `tail` - 显示文件末尾
- `grep` - 搜索文本
- `wc` - 统计行数/字数/字节
- `sort` - 排序文本
- `uniq` - 去重
- `nl` - 带行号显示
- `find` - 查找文件
- `tree` - 目录树
- `stat` - 文件状态
- `du` - 目录大小
- `df` - 磁盘使用

### 系统命令
- `sudo` - 提权执行 (Windows UAC / Unix sudo)
- `ps` - 进程列表
- `kill` - 终止进程
- `sleep` - 延迟
- `uptime` - 系统运行时间
- `uname` - 系统信息
- `id` - 用户身份
- `date` - 显示日期
- `time` - 显示时间
- `whoami` - 显示用户
- `hostname` - 显示主机名
- `env` - 显示环境变量

### 环境管理
- `set` - 设置环境变量
- `unset` - 删除环境变量
- `export` - 导出环境变量

### 其他
- `echo` - 打印文本
- `clear/cls` - 清屏
- `history` - 命令历史 (`history -c` 清空)
- `alias` - 设置别名（持久化）
- `unalias` - 删除别名（持久化）
- `which` - 查找命令路径
- `base64` - Base64 编码/解码
- `md5sum` / `sha1sum` / `sha256sum` - 哈希计算
- `seq` - 数字序列
- `yes` - 重复输出
- `true` / `false` - 返回状态
- `man` - 命令帮助
- `theme` - 管理颜色主题（切换/预览）
- `config` - 管理终端设置
- `help` - 帮助信息
- `exit` - 退出终端

## 使用方式

### 交互模式
```bash
python kshell.py
# 或
./kshell.sh  # Unix/Linux/macOS
kshell.bat   # Windows
```

### 脚本模式
```bash
python kshell.py script.ksh
```

## 扩展开发

### 添加新内置命令
1. 在 `builtin.py` 中添加命令方法
2. 在 `__init__` 中注册命令
3. 在 `cmd_help()` 中添加帮助信息

示例：
```python
def cmd_mycommand(self, args: List[str], options: dict) -> Tuple[int, str]:
    """我的命令"""
    # 实现逻辑
    return 0, "Output"

# 在 __init__ 中
self.commands['mycommand'] = self.cmd_mycommand
```

### 添加平台特定功能
在 `kplatform.py` 中添加平台检测方法，然后在其他模块中使用。

## 测试覆盖

测试脚本 `test.py` 包含：
- 平台检测测试
- 文件系统操作测试
- 命令解析测试
- 内置命令测试

测试脚本 `test_extra.py` 包含：
- 文件内容命令测试 (head/tail/grep/wc/sort/uniq/nl)
- 查找信息命令测试 (find/stat/du/df/which)
- 系统命令测试 (sleep/uname/id/uptime/true/false)
- 工具命令测试 (seq/base64/md5/sha/yes/man/history)

运行测试：
```bash
python test.py
python test_extra.py
```

## 已知限制

1. 管道功能为基础实现，复杂场景可能有限制
2. 后台任务支持有限
3. 某些高级 shell 特性（如作业控制）未实现
4. 外部命令执行依赖系统 PATH
5. 设置文件为 JSON 格式，不支持嵌套复杂结构

## 未来改进方向

1. 增强管道功能
2. 添加命令补全
3. 支持更多提示符样式（如颜色、图标）
4. 添加更多内置命令
5. 支持插件系统
6. 添加颜色输出支持
7. 支持配置文件热重载

## 许可证

MIT License