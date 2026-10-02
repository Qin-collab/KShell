# KShell 打包指南

## 产物说明

| 文件 | 平台 | 说明 |
|------|------|------|
| `dist/kshell.exe` | Windows | 单文件可执行程序（已打包） |
| `dist/kshell_1.0.0_amd64.deb` | Debian/Ubuntu | Linux 安装包（需在 Linux 上构建） |
| `dist/kshell-1.0.0-linux-x86_64.tar.gz` | Linux 通用 | 免安装压缩包（需在 Linux 上构建） |
| `dist/kshell-1.0.0-src.tar.gz` | 跨平台 | 源码包，无需编译直接运行 |

## Windows 打包

### 已打包
`dist/kshell.exe` 已生成（约 8 MB），可直接运行：

```bat
kshell.exe              :: 交互模式
kshell.exe script.ksh   :: 脚本模式
```

### 重新打包

```bat
:: 方式一：直接运行脚本
packaging\build_windows.bat

:: 方式二：命令行
pip install pyinstaller
python -m PyInstaller kshell.spec --noconfirm --clean
```

> 注意：PyInstaller 不支持交叉编译，Windows 的 exe 必须在 Windows 上打包。

## Linux 打包

PyInstaller 不支持从 Windows 交叉编译 Linux 二进制，需要在 Linux 机器上运行打包脚本。

### 方式一：构建原生二进制 + .deb + .tar.gz（推荐）

```bash
# 在 Linux 机器上
sudo apt install python3-pip dpkg-dev   # Debian/Ubuntu
pip3 install pyinstaller

# 拷贝项目到 Linux 后执行
bash packaging/build_linux.sh
```

产物位于 `dist/`：
- `kshell` - 原生 Linux 二进制
- `kshell_1.0.0_amd64.deb` - Debian/Ubuntu 安装包
- `kshell-1.0.0-linux-x86_64.tar.gz` - 通用压缩包

### 安装 .deb 包

```bash
sudo dpkg -i kshell_1.0.0_amd64.deb
kshell                        # 启动
```

### 使用 .tar.gz

```bash
tar -xzf kshell-1.0.0-linux-x86_64.tar.gz
./kshell                      # 直接运行
```

## 源码包（跨平台）

```bash
# 任意平台均可生成（bash 环境）
bash packaging/build_src.sh

# 或指定版本号
bash packaging/build_src.sh 2.0.0
```

解压后直接运行：

```bash
python3 kshell.py
```

## 常见问题

### PyInstaller 报 module 'platform' 无属性
项目早期版本的 `platform.py` 与 Python 标准库同名冲突，已重命名为 `kplatform.py` 解决。如果从旧版本升级，请同步重命名。

### exe 被杀毒软件误报
单文件 exe 使用 PyInstaller 打包，部分杀毒软件可能误报。可：
1. 添加信任/白名单
2. 使用源码包方式运行

### Linux 打包失败
- 确认已安装 `dpkg-deb`（`sudo apt install dpkg-dev`）
- 确认 Python 版本 >= 3.6
- 确认有写权限

## 文件清单

```
packaging/
├── build_windows.bat   # Windows 打包脚本
├── build_linux.sh      # Linux 打包脚本（二进制+deb+tar.gz）
└── build_src.sh        # 源码包脚本（跨平台）

kshell.spec             # PyInstaller 配置文件
dist/                   # 构建产物目录
```

## 版本号

当前版本：`1.0.0`

修改版本号：
- `build_linux.sh` 中的 `VERSION="1.0.0"`
- `build_src.sh` 通过参数传入：`bash packaging/build_src.sh 2.0.0`
