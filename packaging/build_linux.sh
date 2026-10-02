#!/bin/bash
# ============================================================
# KShell Linux 打包脚本
# 功能:
#   1. 用 PyInstaller 构建 Linux 原生二进制
#   2. 构建 .deb 安装包 (Debian/Ubuntu)
#   3. 构建 .tar.gz 通用压缩包
# 用法: bash build_linux.sh
# 要求: python3 + pip, PyInstaller, dpkg-deb
# ============================================================
set -e

cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"
VERSION="1.0.0"
DIST_DIR="$PROJECT_ROOT/dist"
PACKAGE_DIR="$PROJECT_ROOT/packaging/deb/kshell"

echo "============================================"
echo " KShell Linux 打包"
echo " 版本: v$VERSION"
echo "============================================"

# ---------- 1. 检查依赖 ----------
echo ""
echo "[1/4] 检查依赖..."
if ! command -v python3 &>/dev/null; then
    echo "错误: 未找到 python3" >&2; exit 1
fi
python3 -c "import PyInstaller" 2>/dev/null || {
    echo "安装 PyInstaller..."
    pip3 install pyinstaller
}
command -v dpkg-deb &>/dev/null || echo "警告: 未找到 dpkg-deb，跳过 .deb 构建"
command -v tar &>/dev/null || { echo "错误: 未找到 tar" >&2; exit 1; }
echo "依赖检查完成"

# ---------- 2. PyInstaller 构建 ----------
echo ""
echo "[2/4] 使用 PyInstaller 构建二进制..."
python3 -m PyInstaller kshell.spec --noconfirm --clean
echo "二进制已生成: $DIST_DIR/kshell"

# ---------- 3. 构建 .deb ----------
if command -v dpkg-deb &>/dev/null; then
    echo ""
    echo "[3/4] 构建 .deb 安装包..."
    rm -rf "$PACKAGE_DIR"
    mkdir -p "$PACKAGE_DIR/DEBIAN"
    mkdir -p "$PACKAGE_DIR/usr/bin"
    mkdir -p "$PACKAGE_DIR/usr/share/kshell"
    mkdir -p "$PACKAGE_DIR/usr/share/doc/kshell"
    mkdir -p "$PACKAGE_DIR/usr/share/man/man1"

    # control 文件
    cat > "$PACKAGE_DIR/DEBIAN/control" <<EOF
Package: kshell
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6
Maintainer: KShell Team <kshell@example.com>
Description: KShell - cross-platform Python terminal
 A lightweight cross-platform terminal written in pure Python.
 Supports Windows, macOS and Linux with 60+ built-in commands,
 themes, aliases, scripting and more.
EOF

    # 安装二进制
    cp "$DIST_DIR/kshell" "$PACKAGE_DIR/usr/bin/kshell"
    chmod 755 "$PACKAGE_DIR/usr/bin/kshell"

    # 安装文档
    cp README.md "$PACKAGE_DIR/usr/share/doc/kshell/"
    cp QUICKSTART.md "$PACKAGE_DIR/usr/share/doc/kshell/" 2>/dev/null || true
    cp example.ksh "$PACKAGE_DIR/usr/share/kshell/"

    # man page
    cat > "$PACKAGE_DIR/usr/share/man/man1/kshell.1" <<EOF
.TH KSHELL 1 "$(date +%Y-%m-%d)" "KShell v$VERSION"
.SH NAME
kshell \- cross-platform Python terminal
.SH SYNOPSIS
.B kshell
[\fIscript.ksh\fR]
.SH DESCRIPTION
KShell is a lightweight cross-platform terminal written in pure Python.
It supports Windows, macOS and Linux.
.SH OPTIONS
.TP
.B script.ksh
Execute commands from a script file, then exit.
.SH COMMANDS
Run \fBhelp\fR inside kshell for the full command list.
.SH SEE ALSO
https://github.com/kshell/kshell
EOF

    # 构建 deb
    dpkg-deb --build --root-owner-group "$PACKAGE_DIR" "$DIST_DIR/kshell_${VERSION}_amd64.deb"
    echo ".deb 已生成: $DIST_DIR/kshell_${VERSION}_amd64.deb"
else
    echo ""
    echo "[3/4] 跳过 .deb 构建 (未安装 dpkg-deb)"
fi

# ---------- 4. 构建 .tar.gz ----------
echo ""
echo "[4/4] 构建 .tar.gz 压缩包..."
tar -czf "$DIST_DIR/kshell-${VERSION}-linux-x86_64.tar.gz" \
    -C "$DIST_DIR" kshell \
    -C "$PROJECT_ROOT" README.md QUICKSTART.md example.ksh
echo ".tar.gz 已生成: $DIST_DIR/kshell-${VERSION}-linux-x86_64.tar.gz"

echo ""
echo "============================================"
echo " 打包完成! 产物位于 dist/ 目录:"
ls -lh "$DIST_DIR" | grep kshell
echo "============================================"
