#!/bin/bash
# ============================================================
# 通过 apt 安装 KShell（使用公网仓库）
# 适用: Debian / Ubuntu 及其衍生发行版
# ============================================================
set -e

REPO_URL="http://39.96.82.163/apt"

echo "正在添加 KShell APT 仓库..."
echo "deb [trusted=yes] ${REPO_URL} stable main" | tee /etc/apt/sources.list.d/kshell.list

echo "正在更新 apt 索引..."
apt-get update

echo "正在安装 kshell..."
apt-get install -y kshell

echo ""
echo "安装完成！版本信息:"
which kshell
apt-cache policy kshell | head -3

echo ""
echo "启动 KShell:"
echo "  kshell              # 交互模式"
echo "  kshell script.ksh   # 脚本模式"
