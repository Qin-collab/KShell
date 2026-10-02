#!/bin/bash
# ============================================================
# KShell 源码打包脚本 (跨平台)
# 生成: dist/kshell-src-<version>.tar.gz
# 包含所有 .py 源码、文档和示例，无需编译即可运行
# ============================================================
set -e

cd "$(dirname "$0")/.."
VERSION="${1:-1.0.0}"
DIST_DIR="dist"
PKG_NAME="kshell-$VERSION-src"

echo "构建源码包 $PKG_NAME.tar.gz ..."

# 创建打包目录
rm -rf "$DIST_DIR/$PKG_NAME"
mkdir -p "$DIST_DIR/$PKG_NAME"

# 复制源码文件
cp *.py "$DIST_DIR/$PKG_NAME/"
cp *.md "$DIST_DIR/$PKG_NAME/"
cp *.ksh "$DIST_DIR/$PKG_NAME/"
cp *.bat "$DIST_DIR/$PKG_NAME/"
cp *.sh "$DIST_DIR/$PKG_NAME/"
cp kshell.spec "$DIST_DIR/$PKG_NAME/" 2>/dev/null || true
cp -r packaging "$DIST_DIR/$PKG_NAME/" 2>/dev/null || true

# 清理临时文件
rm -rf "$DIST_DIR/$PKG_NAME/__pycache__"
rm -f "$DIST_DIR/$PKG_NAME/test_*"

# 压缩
tar -czf "$DIST_DIR/$PKG_NAME.tar.gz" -C "$DIST_DIR" "$PKG_NAME"
rm -rf "$DIST_DIR/$PKG_NAME"

echo "源码包已生成: $DIST_DIR/$PKG_NAME.tar.gz"
