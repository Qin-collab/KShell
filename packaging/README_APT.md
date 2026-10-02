# KShell APT 仓库使用说明

## 仓库地址

```
http://39.96.82.163/apt
```

## 客户端安装（任意 Ubuntu/Debian 机器）

### 方式一：一键脚本

```bash
curl -fsSL http://39.96.82.163/apt/install.sh | sudo bash
```

### 方式二：手动配置

```bash
# 添加仓库
echo "deb [trusted=yes] http://39.96.82.163/apt stable main" | sudo tee /etc/apt/sources.list.d/kshell.list

# 更新索引
sudo apt update

# 安装
sudo apt install -y kshell

# 启动
kshell
```

## 卸载

```bash
sudo apt purge -y kshell
sudo rm /etc/apt/sources.list.d/kshell.list
sudo apt update
```

## 服务端维护（在你服务器上）

### 仓库目录

```
/srv/apt/
├── dists/stable/main/binary-amd64/Packages
├── dists/stable/main/binary-amd64/Packages.gz
├── dists/stable/Release
└── pool/main/k/kshell/kshell_1.0.0_amd64.deb
```

### 更新 deb 版本

上传新的 deb 到 `/srv/apt/pool/main/k/kshell/`，然后执行：

```bash
cd /srv/apt
dpkg-scanpackages --arch amd64 pool /dev/null > dists/stable/main/binary-amd64/Packages
gzip -9c dists/stable/main/binary-amd64/Packages > dists/stable/main/binary-amd64/Packages.gz
```

### 相关服务

| 服务 | 说明 |
|------|------|
| `kshell-apt.service` | 8081 端口的 HTTP 仓库服务 |
| `1Panel-openresty-HtYx` | 80 端口反向代理到 /apt |

```bash
# 重启仓库 HTTP 服务
systemctl restart kshell-apt

# 重启 openresty
docker exec 1Panel-openresty-HtYx openresty -s reload
```

## 注意事项

- 仓库使用 `[trusted=yes]`，未做 GPG 签名，适合个人/内网使用
- 如需正式使用，建议使用 GPG 签名 Release 文件
