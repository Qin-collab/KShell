# KShell 2.1.0 版本文档

> **版本**：2.1.0（代号 Plugin）  
> **发布日期**：2026-10-04  
> **开源协议**：[Apache License 2.0](LICENSE)  
> **支持平台**：Windows 10/11 · macOS 10.15+ · Linux（主流发行版）  
> **运行环境**：Python 3.6+（核心零第三方依赖）

---

## 目录

- [一、版本概览](#一版本概览)
- [二、版本亮点](#二版本亮点)
- [三、插件系统](#三插件系统)
- [四、plugin 命令](#四plugin-命令)
- [五、开发者社区](#五开发者社区)
- [六、缺陷修复](#六缺陷修复)
- [七、命令与配置](#七命令与配置)
- [八、架构变化](#八架构变化)
- [九、从 2.0 升级](#九从-20-升级)
- [十、安装方式](#十安装方式)
- [十一、测试与验证](#十一测试与验证)
- [十二、已知限制](#十二已知限制)

---

## 一、版本概览

KShell 2.1 的核心是**插件系统**：用「JSON 配置 + Python 实现」扩展终端，无需修改 KShell 本体。

配套地，官网新增**开发者社区**子路由与后台插件注册表管理。

| 项目 | 2.0.0 | 2.1.0 |
|------|-------|-------|
| 内置命令数量 | 68 | **69** |
| 扩展方式 | 修改源码 | **插件目录（免改源码）** |
| 插件系统 | 无 | **JSON 声明 + Python 实现 + 热重载** |
| 插件脚手架 | 无 | **`plugin new` 自动生成** |
| 插件配置 | 无 | **`plugin config` 持久化，支持类型推断** |
| 插件隔离 | 无 | **加载/执行异常均被隔离** |
| 开发者文档 | 无 | **PLUGIN_DEV.md + 社区页面** |
| 官网子路由 | 单页 | **`/community` 开发者社区** |
| 后台功能 | 5 个视图 | **6 个视图（新增插件社区）** |
| 打包体积 | 7.9 MB | 约 12 MB（含插件标准库） |

---

## 二、版本亮点

1. **插件 = 2 个文件** — `plugin.json`（元数据+配置）+ `plugin.py`（实现），放进 `plugins/` 即被自动发现。
2. **热重载** — `plugin reload` 立即生效，改代码无需重启 KShell。
3. **异常隔离** — 插件加载失败或执行出错只提示，不会拖垮 Shell。
4. **脚手架** — `plugin new myplugin` 一键生成可运行的插件骨架。
5. **配置系统** — 插件在 `plugin.json` 声明配置项，用户用 `plugin config` 覆盖并持久化。
6. **开发者社区** — 官网 `/community`，含完整开发文档、示例源码与插件画廊。
7. **后台插件管理** — 可视化增删改插件条目、控制发布状态与推荐置顶。

---

## 三、插件系统

### 3.1 插件结构

```
plugins/
└── myplugin/
    ├── plugin.json     元数据、命令声明、默认配置
    └── plugin.py       Python 实现
```

**搜索目录**（优先级从高到低，同名插件不被低优先级覆盖）：

| 顺序 | 目录 | 说明 |
|------|------|------|
| 1 | `sys._MEIPASS/plugins` | 打包内置（官方示例） |
| 2 | 项目根 `plugins/` | 源码运行 |
| 3 | 可执行文件同级 `plugins/` | **用户插件推荐位置** |
| 4 | `~/.kshell/plugins` | 用户级 |
| 5 | 配置 `plugins.dirs` | 自定义目录 |

### 3.2 plugin.json

```json
{
  "name": "myplugin",
  "version": "1.0.0",
  "author": "你的名字",
  "description": "插件说明",
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
    "greeting": "Hello"
  }
}
```

`commands` 支持三种写法：

- **字符串数组** — `["hello", "greet"]`，函数名约定为 `cmd_<命令名>`
- **对象** — 可指定 `function` / `usage` / `description` / `aliases`
- **省略** — 自动扫描 `plugin.py` 中所有 `cmd_*` 函数（`cmd_auto_one` → 命令 `auto-one`）

**manifest 校验**（不通过则只报错，不影响 KShell）：

| 校验项 | 说明 |
|--------|------|
| JSON 语法 | 解析失败直接报错 |
| `name` 必填且合法 | 只允许字母、数字、`_`、`-` |
| `name` 与目录名一致 | 不一致时报错 |
| `commands` 格式 | 必须是数组或对象 |
| 函数存在性 | 声明的函数必须在 `plugin.py` 中可调用 |
| 版本要求 | `kshell` 字段与当前版本比对 |
| `settings` 类型 | 必须是 JSON 对象 |

### 3.3 plugin.py 与 ctx API

```python
def cmd_hello(args, options, ctx):
    greeting = ctx.get('greeting', 'Hello')     # 读插件配置
    name = args[0] if args else 'World'
    return 0, f'{greeting}, {name}!'            # (退出码, 输出)
```

`ctx` 提供：

| 成员 | 说明 |
|------|------|
| `ctx.name` / `ctx.version` / `ctx.dir` | 插件元信息 |
| `ctx.get(k, d)` / `ctx.set(k, v)` / `ctx.config()` | 插件配置读写 |
| `ctx.fs` / `ctx.platform` / `ctx.settings` / `ctx.theme` | KShell 能力 |
| `ctx.colorize(text, key)` | 主题着色 |
| `ctx.log(msg)` | 日志（加载阶段打印） |
| `ctx.register_command(...)` | 运行期动态注册命令 |

**返回值归一化**：`(code, str)` / `str` / `None` / `int` 都能正确处理。

**可选回调**：`on_load(ctx)` / `on_unload(ctx)`。

### 3.4 加载机制

- **动态编译**：读取源码后 `compile()` + `exec()`，**不使用 importlib 的字节码缓存**
  - 原因：CPython 的 `.pyc` 过期判断依赖「源文件 mtime（秒级）+ 文件大小」，同秒内改动等长代码会命中旧字节码，导致热重载失效
  - 附带好处：不会在用户的插件目录里生成 `__pycache__`
- **异常隔离**：导入异常 → 记录 `load_error`；执行异常 → 返回 `(1, 错误信息)`
- **配置持久化**：`plugins.enabled` / `plugins.config` / `plugins.dirs` 写入 `kshell_config.json`
- **目录可写性检测**：`plugin new` 会实测目录可写，且**排除打包临时目录**（`_MEIPASS` 退出即删）

### 3.5 官方示例插件

| 插件 | 命令 | 演示内容 |
|------|------|---------|
| `hello` | `hello` `greet` | 配置读取、选项解析、返回值、`on_load` 回调、别名 |
| `pwgen` | `pwgen` `uuid` `passwd-strength` | 多命令插件、命令名与函数名不同、`secrets` 加密安全随机 |
| `sysinfo` | `sysinfo` `sys` | `--json` 结构化输出、配置开关、优雅降级 |

---

## 四、plugin 命令

```bash
plugin                      # 列出全部插件
plugin list                 # 同上
plugin info <名称>           # 详情：元数据、命令、配置、失败原因
plugin enable <名称>         # 启用（写入配置）
plugin disable <名称>        # 禁用（写入配置）
plugin reload [名称]         # 重新加载（省略名称则全部）
plugin config <名称>         # 查看插件配置
plugin config <名称> k=v     # 修改插件配置（自动推断类型）
plugin dirs                 # 显示插件搜索目录
plugin new <名称>            # 生成插件骨架
plugin help                 # 子命令帮助
```

**配置值类型推断**：`true/false` → 布尔，`123` → 整数，`1.5` → 浮点，`null` → None，其余为字符串。

示例：

```bash
$ plugin new myplugin
插件骨架已生成: D:\KShell\plugins\myplugin

$ plugin reload myplugin
插件 myplugin 已重新加载（1 条命令）

$ plugin config myplugin greeting=你好
已更新插件 myplugin 的配置: greeting

$ plugin list
KShell 插件（4 个）
  名称            版本      状态    命令数  说明
  hello          1.0.0     已加载     2    最小示例插件…
  myplugin       0.1.0     已加载     1    myplugin 插件
  pwgen          1.0.0     已加载     3    密码与 UUID 生成器…
  sysinfo        1.0.0     已加载     2    系统信息速查…

  已加载 4 · 禁用 0 · 失败 0 · 注册命令 8 条
```

---

## 五、开发者社区

### 5.1 官网子路由 `/community`

面向插件开发者的文档页，包含：

- **30 秒上手** —— 脚手架命令演示
- **插件结构** —— 目录约定与搜索优先级
- **plugin.json 字段** —— 完整字段表 + 三种 commands 写法
- **plugin.py 实现** —— 函数签名、选项解析注意点
- **ctx 上下文 API** —— 全部成员与着色 key
- **返回值约定** —— 四种返回形式与异常隔离行为
- **官方示例插件** —— 三个插件的真实源码（选项卡切换）
- **插件画廊** —— 从 `/api/plugins` 动态加载，支持标签筛选
- **提交你的插件** —— 步骤与发布前自查清单
- **安全须知** —— 权限模型与注意事项

页面自带**侧栏目录**（滚动高亮）、**代码复制按钮**、**移动端适配**。

### 5.2 后台插件管理

后台新增「**插件社区**」视图：

| 功能 | 说明 |
|------|------|
| 注册表统计 | 条目总数、已发布、官方、推荐位、标签汇总 |
| 新增/编辑 | 表单包含名称、版本、作者、说明、仓库、命令、标签 |
| 发布控制 | 未发布的条目只在后台可见，不出现在前台 |
| 推荐置顶 | 标记推荐后在前台画廊中优先排序 |
| 官方标记 | 显示「官方」徽章 |
| 删除 | 二次确认 |
| 补回官方示例 | 幂等操作，仅补齐缺失的内置条目 |

**字段校验**（服务端白名单）：

| 字段 | 规则 |
|------|------|
| `name` | 必填，仅字母数字下划线连字符，最长 60 |
| `version` | 最长 20 |
| `author` | 最长 80 |
| `description` | 最长 400 |
| `repo` / `homepage` | 必须是 http(s) 链接 |
| `commands` | 最多 20 项，单项最长 40（支持逗号分隔输入） |
| `tags` | 最多 8 项，单项最长 20（支持逗号分隔输入） |
| `published` / `featured` / `official` | 布尔 |

### 5.3 公开接口

| 路径 | 说明 |
|------|------|
| `GET /community` | 开发者社区页面 |
| `GET /api/plugins` | 已发布的插件列表 + 标签汇总（带 120 秒缓存） |

---

## 六、缺陷修复

2.1 开发过程中发现并修复的问题（多数由测试与截图验收暴露）：

| # | 问题 | 影响 | 修复 |
|---|------|------|------|
| 1 | **热重载读到旧代码** | 同秒内改动等长源码时，CPython 的 `.pyc` 过期判断（mtime 秒级 + 文件大小）会命中缓存字节码，`plugin reload` 不生效 | 改为直接读取源码 `compile()` + `exec()`，绕过字节码缓存 |
| 2 | **非 GBK 字符导致 Shell 崩溃** | Windows 控制台默认 GBK，插件输出 `✓`、emoji 等字符会抛 `UnicodeEncodeError` 并中断整个 Shell | 新增 `safe_print()`，所有输出走它，无法编码时降级替换 |
| 3 | **配置出现扁平重复键** | `SettingsManager` 只支持扁平键，`plugins.config` 被当成字面键名写进配置，与嵌套默认值重复 | 为 `SettingsManager` 实现点号路径读写（含扁平键回退兼容） |
| 4 | **打包后插件无法导入标准库** | PyInstaller 静态分析看不到动态加载插件的 `import`，`pwgen` 在 exe 中报 `ModuleNotFoundError: secrets` | 新增 `PLUGIN_STDLIB_HINTS` 清单，由 `kshell.spec` 导入并加入 `hiddenimports` |
| 5 | **打包后脚手架写入临时目录** | `plugin new` 把插件生成到 `_MEIPASS`（退出即删），用户拿不到文件 | 新增 `scaffold_dir()`：实测可写、排除临时目录，优先可执行文件同级 |
| 6 | **插件目录生成 `__pycache__`** | 早期 importlib 加载会在用户插件目录留下 `.pyc` | 改为 compile/exec 后不再生成（已验证） |

---

## 七、命令与配置

### 7.1 命令数量

| 类别 | 2.0 | 2.1 |
|------|-----|-----|
| 核心内置 | 36 | 36 |
| 扩展命令 | 32 | 32 |
| **插件管理** | — | **1（`plugin`）** |
| **合计** | 68 | **69** |

此外，插件会注册各自的命令（官方示例贡献 7 条）。

### 7.2 新增配置项

```json
{
  "plugins": {
    "enabled": {},     // { "插件名": true/false }
    "config":  {},     // { "插件名": { "键": 值 } }
    "dirs":    []      // 额外插件搜索目录
  }
}
```

---

## 八、架构变化

### 8.1 新增模块

```
pluginmgr.py           插件系统核心
  · PluginManager      —— 发现、加载、注册、配置、脚手架
  · Plugin / PluginCommand —— 插件与命令描述
  · PluginContext      —— 传给插件函数的上下文
  · PLUGIN_STDLIB_HINTS —— 打包时需包含的插件常用标准库清单

commands_plugin.py     plugin 命令组实现

version.py             版本号单一来源（VERSION / check_requirement）

plugins/               官方示例插件
  hello/ pwgen/ sysinfo/

PLUGIN_DEV.md          插件开发指南
```

### 8.2 加载流程

```
terminal.__init__()
   │
   ├─ BuiltinCommands()            注册 36 核心命令
   │     └─ ExtraCommands()        注册 32 扩展命令
   │     └─ PluginCommands()       注册 plugin 命令
   │
   └─ PluginManager.load_all()
         │
         ├─ resolve_dirs()         解析搜索目录（含 _MEIPASS / 用户目录 / 配置）
         ├─ find_manifests()       扫描 plugin.json
         └─ load() 每个插件
               ├─ 解析并校验 plugin.json
               ├─ 版本要求比对
               ├─ 启用状态检查
               ├─ 读取源码 → compile() → exec()    ← 绕过字节码缓存
               ├─ 包装并注册命令（异常隔离 + 返回值归一化）
               └─ 调用 on_load(ctx)
```

### 8.3 命令派发顺序（未变）

```
command 强制系统命令 → 内置命令（含插件命令）→ 系统 PATH 命令
```

插件命令与内置命令同级，因此**插件命令会覆盖同名内置命令**——这是有意设计（方便插件扩展/覆盖行为），但插件开发者应避免与内置命令重名。

---

## 九、从 2.0 升级

### 9.1 兼容性

✅ **配置文件兼容** — 2.0 的 `kshell_config.json` 可直接使用，`plugins` 段会自动补齐默认值。  
✅ **命令语法兼容** — 所有 2.0 命令行为不变。  
✅ **脚本兼容** — `.ksh` 脚本无需修改。  
✅ **旧版配置的扁平键兼容** — 若存在 `"plugins.config"` 这类扁平键，`SettingsManager` 读取时会回退匹配。

### 9.2 行为变更

| 变更 | 说明 |
|------|------|
| 新增 `plugin` 命令 | 若你之前自定义过 `plugin` 命令，会被覆盖 |
| 启动时扫描插件目录 | 首次启动稍慢（毫秒级）；插件加载失败会在启动时提示 |
| 新增 `plugins` 配置段 | 老配置会自动补默认值 |
| 打包体积增加 | 约 7.9 MB → 12 MB，因为纳入了插件常用标准库模块 |

### 9.3 升级步骤

**Windows**

```bat
:: 备份配置
copy kshell_config.json kshell_config.json.bak

:: 用新的 exe 替换（可选：在 exe 同级建 plugins 目录放插件）
kshell_windows_x64_v2.1.exe
```

**验证**

```bash
kshell            # 横幅应显示 KShell v2.1
plugin list       # 应列出 3 个官方示例插件
plugin help       # 应输出子命令帮助
hello KShell      # 应输出 Hello, KShell!
```

---

## 十、安装方式

### Windows

```bat
kshell_windows_x64_v2.1.exe            :: 交互模式
kshell_windows_x64_v2.1.exe script.ksh :: 脚本模式
```

重新构建：

```bat
packaging\build_windows.bat
```

> 打包时会把 `plugins/`（官方示例）与 `PLUGIN_DEV.md` 一并内嵌。用户自己的插件放在 **exe 同级 `plugins/` 目录** 即可。

### Linux

```bash
# APT 仓库
echo "deb [trusted=yes] http://39.96.82.163/apt stable main" | sudo tee /etc/apt/sources.list.d/kshell.list
sudo apt update && sudo apt install -y kshell

# 或源码
git clone https://github.com/Qin-collab/KShell.git
cd KShell && python3 kshell.py
```

自行构建安装包：`pip3 install pyinstaller && bash packaging/build_linux.sh`

---

## 十一、测试与验证

| 测试套件 | 覆盖范围 | 结果 |
|---------|---------|------|
| `test_v21_plugins.py` | **新增**：版本比较、插件加载、manifest 校验（8 种非法情况）、命令执行、配置读写、启用禁用、热重载、异常隔离、返回值归一化、自动发现、脚手架、自定义目录、统计 | **85 项通过 / 0 失败** |
| `test_v2_syscmd.py` | PATH 解析、选项透传、优先级派发、`command` 绕过、`path`、`calc` | 27 项通过 |
| `test.py` | 平台抽象、文件系统、命令解析、内置命令 | 通过 |
| `test_extra.py` | 扩展命令 | 通过 |
| `test_v21_terminal.ksh` | 端到端：12 个场景（含 3 个插件、配置修改、别名、未知插件） | 通过 |
| 打包后 exe | 插件列表、执行、脚手架、目录解析 | 通过 |
| 后台插件注册表 | CRUD、5 项校验规则、发布状态过滤、推荐置顶、幂等补种 | 通过 |
| 官网 `/community` | 渲染、画廊动态加载、标签筛选、响应式（390/768/1440） | 通过 |

**验证方法说明**：除单元测试外，本轮全程使用 **CDP 无头浏览器截图 + 页面探针**做视觉验收——缺陷 #2、#4、#5 都是靠截图与实机运行发现的，纯接口测试无法暴露。

---

## 十二、已知限制

1. **插件无沙箱** — 插件是普通 Python 代码，拥有与 KShell 相同的权限。只运行可信插件。
2. **插件异常隔离有边界** — 异常会被捕获，但死循环、`sys.exit()`、超大内存分配仍会影响 Shell。
3. **插件命令可覆盖内置命令** — 同名时插件优先；请避免与内置命令重名。
4. **打包后插件依赖受限于预置标准库** — exe 已内嵌 `PLUGIN_STDLIB_HINTS` 中的常用标准库；若插件需要第三方库（如 `requests`），需自行重新打包或使用源码运行。
5. **`plugin enable/disable` 需 reload 才立即生效** — 写入配置后，运行中的命令表不会自动更新（可用 `plugin reload`）。
6. **`plugins.dirs` 需 JSON 数组** — 通过 `config set` 修改时需写成数组形式。
7. **网站后台插件注册表与本地插件目录无关联** — 注册表是「社区目录」，用于展示；不会自动安装插件。
8. **插件热重载不重载其第三方依赖** — 只重新编译插件自身源码。

---

## 附录：2.1.0 变更文件清单

**新增**

| 文件 | 说明 |
|------|------|
| `pluginmgr.py` | 插件系统核心 |
| `commands_plugin.py` | `plugin` 命令组 |
| `version.py` | 版本号单一来源 |
| `plugins/hello/` | 示例：入门 |
| `plugins/pwgen/` | 示例：多命令与加密安全随机 |
| `plugins/sysinfo/` | 示例：结构化输出与降级 |
| `PLUGIN_DEV.md` | 插件开发指南 |
| `RELEASE_2.1.0.md` | 本文档 |
| `test_v21_plugins.py` | 插件测试（85 项） |
| `test_v21_terminal.ksh` | 插件端到端测试 |
| `tools/backup.ps1` | 备份脚本（含 SHA256 校验清单） |
| `HTML/public/community.html/css/js` | 开发者社区页面 |
| `HTML/lib/registry.js` | 后台插件注册表 |

**修改**

| 文件 | 主要变更 |
|------|---------|
| `terminal.py` | 创建并加载插件管理器；新增 `safe_print()`；版本号改用 `version.py` |
| `builtin.py` | 注册 `plugin` 命令；新增 `set_plugin_manager()`；帮助文本更新 |
| `settings.py` | 新增 `plugins` 配置段；实现点号路径读写 |
| `banner.py` | 版本号取自 `version.py` |
| `kshell.spec` | 内嵌 `plugins/` 与文档；加入插件标准库 `hiddenimports` |
| `HTML/server.js` | `/community` 路由、`/api/plugins`、插件注册表后台接口 |
| `HTML/lib/store.js` | 支持 `KSH_DATA_DIR` 指定数据目录（多实例/测试隔离） |
| `HTML/admin/*` | 新增「插件社区」视图 |
| `HTML/public/index.html` | 主导航加入开发者社区入口 |
| `HTML/README.md` | 社区与注册表文档 |

---

**KShell 2.1.0** — 一个用纯 Python 写的、能跑在三类系统上的轻量终端，现在你可以自己扩展它了。
