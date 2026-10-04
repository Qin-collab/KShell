# KShell 插件开发指南

> 适用版本：KShell **2.1.0** 及以上

插件让你用 **JSON 配置 + Python 实现** 扩展 KShell，无需修改 KShell 本体。

---

## 目录

- [30 秒上手](#30-秒上手)
- [插件结构](#插件结构)
- [plugin.json 字段](#pluginjson-字段)
- [plugin.py 实现](#pluginpy-实现)
- [上下文 ctx API](#上下文-ctx-api)
- [返回值约定](#返回值约定)
- [完整示例](#完整示例)
- [调试技巧](#调试技巧)
- [命名与版本规范](#命名与版本规范)
- [安全须知](#安全须知)

---

## 30 秒上手

```bash
# 1. 生成插件骨架
plugin new myplugin

# 2. 编辑实现
#    plugins/myplugin/plugin.py

# 3. 加载并测试
plugin reload myplugin
myplugin hello

# 4. 查看注册结果
plugin info myplugin
```

生成的文件：

```
plugins/myplugin/
├── plugin.json    元数据、命令声明、默认配置
└── plugin.py      Python 实现
```

---

## 插件结构

一个插件就是 `plugins/` 下的一个目录：

```
plugins/
└── myplugin/
    ├── plugin.json     必需 · 元数据与配置
    └── plugin.py       必需 · Python 实现
```

KShell 按以下顺序搜索插件目录（**先找到的优先**，同名插件不会被后面的覆盖）：

| 顺序 | 目录 | 用途 |
|------|------|------|
| 1 | 打包内置目录 | 随 KShell 一起发布的示例插件 |
| 2 | 项目 `plugins/` | 源码运行时使用 |
| 3 | 可执行文件同级 `plugins/` | **推荐放自己的插件** |
| 4 | `~/.kshell/plugins` | 用户级插件 |
| 5 | 配置 `plugins.dirs` 中的目录 | 自定义 |

用 `plugin dirs` 查看实际搜索路径。

---

## plugin.json 字段

```json
{
  "name": "myplugin",
  "version": "1.0.0",
  "author": "你的名字",
  "description": "插件的一句话说明",
  "homepage": "https://github.com/you/myplugin",
  "kshell": ">=2.1.0",
  "enabled": true,
  "commands": {
    "myplugin": {
      "function": "cmd_main",
      "usage": "myplugin [参数] [-v]",
      "description": "命令说明",
      "aliases": ["mp"]
    }
  },
  "settings": {
    "greeting": "Hello",
    "count": 3
  }
}
```

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | ✅ | 插件名，**必须与目录名一致**；只允许字母、数字、`_`、`-` |
| `version` | | 插件版本，建议语义化（`1.2.3`） |
| `author` | | 作者 |
| `description` | | 一句话说明，会显示在 `plugin list` |
| `homepage` | | 主页或仓库地址 |
| `kshell` | | 要求的 KShell 版本，支持 `>=` `<=` `>` `<` `==` `!=`，也可只写 `2.1.0`（视为最低版本） |
| `enabled` | | 默认是否启用（用户在配置中的设置优先级更高） |
| `commands` | | 命令声明，见下 |
| `settings` | | 默认配置项，用户可用 `plugin config` 覆盖 |

### commands 的三种写法

**写法一：字符串数组**（函数名约定为 `cmd_<命令名>`）

```json
"commands": ["hello", "greet"]
```
→ 对应 `cmd_hello()` 和 `cmd_greet()`；命令名 `hello`、`greet`

**写法二：对象**（可指定函数名、用法、说明、别名）

```json
"commands": {
  "passwd-strength": {
    "function": "cmd_strength",
    "usage": "passwd-strength <密码>",
    "description": "评估密码强度",
    "aliases": ["pws"]
  }
}
```

**写法三：省略 commands**（自动发现）

不写 `commands` 字段时，KShell 会扫描 `plugin.py` 中所有 `def cmd_xxx` 函数，
命令名由函数名转换而来：`cmd_auto_one` → `auto-one`（下划线转连字符）。

---

## plugin.py 实现

每个命令对应一个函数，**签名固定**：

```python
def cmd_命令名(args, options, ctx):
    return 0, "输出内容"
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `args` | `list[str]` | 位置参数，如 `['KShell', '/tmp']` |
| `options` | `dict` | 选项，如 `{'v': True}`（`-v`）、`{'name': 'x'}`（`--name x`）、`{'sort': 'time'}`（`--sort=time`） |
| `ctx` | `PluginContext` | 上下文，见下节 |

### 选项解析的两个注意点

KShell 的解析器把**短选项一律视为布尔标志**：

```bash
mycmd -v            # options = {'v': True}
mycmd -l 24         # options = {'l': True}，args = ['24']   ← 24 是位置参数
mycmd --length 24   # options = {'length': '24'}
mycmd --length=24   # options = {'length': '24'}
mycmd --no-symbols  # options = {'no-symbols': True}
```

因此**需要带值的选项请用长选项**（`--length 24`），或在代码里从 `args` 里取。

### 可选回调

```python
def on_load(ctx):
    """插件加载完成时调用，适合做初始化、打印提示"""
    ctx.log('myplugin 已加载')

def on_unload(ctx):
    """插件卸载/重载/禁用时调用，适合释放资源（关闭文件、连接）"""
    pass
```

---

## 上下文 ctx API

| 成员 | 说明 |
|------|------|
| `ctx.name` / `ctx.version` | 插件名 / 版本 |
| `ctx.dir` | 插件目录（`pathlib.Path`） |
| `ctx.plugin` | 插件对象（含 `manifest` 原始 JSON） |
| `ctx.get(key, default)` | **读取插件配置**（默认值 + 用户覆盖） |
| `ctx.set(key, value)` | **写入插件配置**（持久化到配置文件） |
| `ctx.config()` | 取全部配置的字典 |
| `ctx.fs` | 文件系统对象（`getcwd()` `list_dir()` `read_file()` 等） |
| `ctx.platform` | 平台信息（`system` `home_dir` `is_windows()` 等） |
| `ctx.settings` | 全局设置（`get()`） |
| `ctx.theme` | 主题（`colorize(text, key)`） |
| `ctx.colorize(text, key)` | 便捷着色，key 见下表 |
| `ctx.log(msg)` | 记录日志（加载阶段会打印） |
| `ctx.command_exists(name)` | 命令是否已存在 |
| `ctx.register_command(name, fn, usage, desc)` | 运行期动态注册命令 |

**可用的着色 key**：`success` `error` `warning` `info` `title` `dir` `file` `link` `command`

---

## 返回值约定

| 返回 | 效果 |
|------|------|
| `return 0, "文本"` | 成功，输出文本 |
| `return 1, "错误"` | 失败，输出错误信息 |
| `return "文本"` | 等价于 `(0, "文本")` |
| `return None` | 等价于 `(0, "")` |
| `return 3` | 退出码 3，无输出 |

异常会被 KShell 捕获并隔离，**不会导致 Shell 崩溃**：

```
[插件 myplugin] 命令 myplugin 执行出错 → ValueError: 故意炸掉
```

---

## 完整示例

### 示例一：最小插件

`plugins/hello/plugin.json`

```json
{
  "name": "hello",
  "version": "1.0.0",
  "commands": {
    "hello": {
      "function": "cmd_hello",
      "usage": "hello [名字] [-v]",
      "description": "打招呼"
    }
  },
  "settings": {
    "greeting": "Hello",
    "punctuation": "!"
  }
}
```

`plugins/hello/plugin.py`

```python
def cmd_hello(args, options, ctx):
    greeting = ctx.get('greeting', 'Hello')
    punctuation = ctx.get('punctuation', '!')
    name = args[0] if args else 'World'

    lines = [f'{greeting}, {name}{punctuation}']
    if 'v' in options:
        lines.append(f'  插件目录: {ctx.dir}')
    return 0, '\n'.join(lines)
```

使用：

```bash
$ hello KShell
Hello, KShell!

$ plugin config hello greeting=你好
已更新插件 hello 的配置: greeting
$ plugin reload hello
$ hello KShell
你好, KShell!
```

### 示例二：多命令 + 加密安全随机

见 `plugins/pwgen/`，演示了：
- 一个插件注册 3 条命令（`pwgen` / `uuid` / `passwd-strength`）
- 命令名与函数名不同（`passwd-strength` → `cmd_strength`）
- 使用 `secrets` 而非 `random` 生成密码

### 示例三：结构化输出与配置开关

见 `plugins/sysinfo/`，演示了：
- `--json` 选项输出机器可读数据，便于脚本处理
- 用 `ctx.get('show_disk', True)` 让用户能关掉某部分输出
- 优雅降级：取不到的信息直接跳过，不让整个插件失败

---

## 调试技巧

```bash
plugin list                 # 看加载状态（已加载 / 已禁用 / 失败）
plugin info <名称>           # 看失败原因、注册了哪些命令、当前配置
plugin reload <名称>         # 改完代码立即生效，无需重启 KShell
plugin dirs                 # 确认插件目录是否在搜索路径里
```

**常见问题**

| 现象 | 原因 |
|------|------|
| `加载失败: plugin.json JSON 解析失败` | JSON 语法错误（多余的逗号、注释） |
| `插件名 "x" 与目录名 "y" 不一致` | `name` 字段必须等于目录名 |
| `命令 "x" 声明的函数 cmd_x() 在 plugin.py 中不存在` | 函数名拼写错误，或 `function` 字段写错 |
| `需要 KShell >=x.y.z，当前 2.1.0` | `kshell` 字段要求的版本高于当前版本 |
| 命令没出现，也没报错 | 插件被禁用了（`plugin list` 显示「已禁用」），执行 `plugin enable <名称>` |
| 改了代码没生效 | 执行 `plugin reload <名称>`（热重载会重新编译源码，不会被字节码缓存影响） |

**在插件里打印调试信息**：用 `ctx.log()`，或直接 `return` 出来看输出（返回值会自动显示）。

---

## 命名与版本规范

- **插件名**：小写 + 连字符，如 `git-tools`；避免与内置命令重名（会覆盖内置命令）
- **命令名**：尽量短且语义清晰；`plugin` 已被 KShell 占用
- **版本号**：语义化版本 `主版本.次版本.修订号`
- **`kshell` 字段**：声明你依赖的最低 KShell 版本，例如 `">=2.1.0"`
- **配置文件**：不要在插件目录外写文件；用户配置请用 `ctx.set()`
- **依赖**：尽量只用 Python 标准库。若必须用第三方库，请在 README 中说明并做好 ImportError 兜底

---

## 安全须知

⚠️ **插件是普通 Python 代码，拥有与 KShell 相同的权限。**

- 只安装你信任的插件——插件可以读写文件、执行命令、访问网络
- 从社区获取插件时，建议先阅读 `plugin.py` 源码
- 不要硬编码密码、Token 等敏感信息；用 `ctx.get()` 让用户在配置中填写
- 生成密码/Token 请使用 `secrets` 模块，**不要用 `random`**
- 插件异常已被隔离，但**死循环、`sys.exit()`、大量内存分配仍会影响 Shell**

KShell 目前**不提供插件沙箱**。如果你需要运行不受信任的插件，请先在隔离环境（容器/虚拟机）中评估。

---

## 发布你的插件

1. 把插件目录推到 GitHub 仓库（推荐结构：仓库根目录即插件目录）
2. 在仓库 README 中说明：插件名、命令列表、KShell 版本要求、配置项
3. 到 KShell 官网的[开发者社区](../../HTML/public/community.html)登记，或在 GitHub 提 Issue 附上仓库地址

发布前自查：

- [ ] `plugin.json` 中 `name` 与目录名一致
- [ ] 所有 `commands` 声明的函数都真实存在
- [ ] 在 `plugin list` 中状态为「已加载」
- [ ] 每条命令都试过：正常参数、缺参数、错误参数
- [ ] 没有硬编码密钥
- [ ] 已声明 `kshell` 最低版本

---

**相关文档**：[README](README.md) · [2.1.0 版本文档](RELEASE_2.1.0.md) · [项目结构](STRUCTURE.md)
