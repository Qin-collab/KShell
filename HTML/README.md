# KShell 官网

KShell 官方网站 + 管理后台 + 开发者社区，基于 **Node.js**，**零第三方依赖**（无需 `npm install`）。

- **前台** `/`：产品介绍、命令参考、主题预览、下载区。下载按钮自动指向 GitHub Releases，版本与安装包信息实时来自 GitHub API。
- **开发者社区** `/community`：插件开发文档（JSON 配置 + Python 实现）、ctx API 参考、官方示例源码、插件画廊（标签筛选）、提交指南与安全须知。
- **后台** `/admin`：密码登录、访问/下载统计、站点设置（改完前台立即生效）、发布信息刷新、插件社区管理、请求日志、密码管理。

---

## 快速开始

```bash
cd HTML
node server.js
```

| 入口 | 地址 |
|------|------|
| 前台 | http://localhost:3000 |
| 开发者社区 | http://localhost:3000/community |
| 后台 | http://localhost:3000/admin |

**首次运行**会自动生成管理员密码并打印在控制台，请立即保存：

```
  ⚠ 首次运行，已生成管理员密码（请立即保存）：

      用户名 : admin
      密  码 : xxxxxxxxxxxxx
```

也可以用环境变量自己指定（推荐用于自动化部署）：

```bash
KSH_ADMIN_PASSWORD=你的强密码 node server.js
```

其他启动参数：

```bash
node server.js --port 8080        # 指定端口
node server.js --host 127.0.0.1   # 仅本机可访问
npm start                          # 等价于 node server.js
```

> 要求 Node.js **18+**（用到内置 `fetch` 与 `AbortSignal.timeout`）。已在 Node 22 上验证。

---

## 目录结构

```
HTML/
├── package.json              # 项目元信息与脚本
├── config.js                 # 静态配置（仓库地址、回退版本、资产识别规则）
├── server.js                 # 服务端：前台静态 + 公开接口 + 后台 API
│
├── lib/                      # 服务端模块
│   ├── store.js              # JSON 持久化（原子写入 + 写盘防抖）
│   ├── auth.js               # scrypt 密码哈希、会话、CSRF、登录限流
│   ├── stats.js              # 访问/下载/API 统计、日志环形缓冲
│   ├── site.js               # 站点设置（白名单校验 + 前台安全投影）
│   └── registry.js           # 插件注册表（社区画廊数据 + 字段校验）
│
├── public/                   # 前台与开发者社区
│   ├── index.html            # 首页
│   ├── styles.css            # 首页样式
│   ├── app.js                # 首页逻辑
│   ├── community.html        # 开发者社区（插件开发文档 + 画廊）
│   ├── community.css         # 社区页样式
│   ├── community.js          # 社区页逻辑
│   ├── favicon.svg
│   └── 404.html
│
├── admin/                    # 管理后台
│   ├── index.html            # 登录 + 控制台（单页，hash 路由）
│   ├── style.css
│   └── app.js
│
├── data/                     # 运行时数据（已 gitignore，含密码哈希）
│   ├── admin.json            # 账户与登录记录
│   ├── settings.json         # 站点设置
│   ├── stats.json            # 统计数据与日志
│   └── plugins.json          # 插件注册表（社区画廊条目）
│
└── tools/                    # 开发工具（不参与部署）
    ├── diagnose-layout.js    # 布局诊断：找出横向溢出元素
    └── screenshot.js         # 截图工具：设备模拟 + 整页捕获 + 后台登录
```

---

## 开发者社区

`/community` 是面向插件开发者的文档页，内容与 KShell 仓库的 [PLUGIN_DEV.md](../PLUGIN_DEV.md) 对应：

| 章节 | 内容 |
|------|------|
| 30 秒上手 | `plugin new` 脚手架命令演示 |
| 插件结构 | 目录约定与 5 级搜索优先级 |
| plugin.json | 完整字段表 + 三种 commands 写法 |
| plugin.py | 函数签名、**选项解析注意点**（短选项是布尔标志） |
| ctx API | 全部上下成员与着色 key |
| 返回值约定 | 四种返回形式与异常隔离行为 |
| 官方示例 | hello / pwgen / sysinfo 的真实源码（选项卡切换） |
| 插件画廊 | 动态加载 + 标签筛选 |
| 提交指南 | 步骤与发布前自查清单 |
| 安全须知 | 权限模型与注意事项 |

页面特性：侧栏目录（滚动高亮）、代码复制按钮、整页响应式（390 / 768 / 1440 均无横向溢出）。

### 插件画廊数据

画廊通过 `GET /api/plugins` 读取 `data/plugins.json`，只返回**已发布**的条目：

```json
{
  "plugins": [
    {
      "id": "pwgen",
      "name": "pwgen",
      "version": "1.0.0",
      "author": "KShell Team",
      "description": "密码与 UUID 生成器…",
      "repo": "https://github.com/Qin-collab/KShell/tree/main/plugins/pwgen",
      "commands": ["pwgen", "uuid", "passwd-strength"],
      "tags": ["示例", "安全", "工具"],
      "kshell": ">=2.1.0",
      "official": true,
      "featured": false
    }
  ],
  "tags": ["入门", "安全", "工具", "示例", "系统"],
  "count": 3
}
```

首次启动会写入 3 个官方示例作为种子数据，后台可增删改。

---

## 管理后台

访问 `/admin`，使用管理员密码登录。

### 七个功能视图

| 视图 | 内容 |
|------|------|
| **概览** | 今日访问 / 累计访问 / 下载点击 / API 调用四张卡片；当前发布信息；运行状态（Node 版本、内存、PID、活跃会话、最近登录）；14 天趋势图 |
| **访问统计** | 7/14/30/90 天趋势图（访问·下载·API 三条）；热门页面、来源、客户端 Top 榜；下载分布；重置统计 |
| **版本发布** | GitHub Release 详情与资产表格（含 GitHub 侧下载数）；缓存状态；一键刷新缓存 |
| **插件社区** | 插件注册表增删改；发布状态控制；推荐置顶；官方标记；字段校验；幂等补回官方示例 |
| **站点设置** | 站点标题/简介/描述、首页公告条、下载按钮地址与说明、缓存时长、统计开关 |
| **请求日志** | 最近 300 条请求（时间、IP、方法、路径、状态码、耗时），状态码按 2xx/3xx/4xx/5xx 着色，可清空 |
| **安全设置** | 当前会话信息；修改密码（改后所有会话失效） |

### 后台改设置，前台立即生效

「站点设置」写入的是 `data/settings.json`，前台通过 `/api/site` 读取，**无需重启服务，也无需重新部署**。

例如开启首页公告条：后台勾选「启用公告条」并填写内容 → 刷新前台即可看到顶部公告。

可修改的字段（服务端有白名单校验，非法值会被拒绝并返回原因）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `site.title` | string(80) | 站点标题（同时更新页脚） |
| `site.tagline` | string(120) | 一句话简介 |
| `site.description` | string(400) | 站点描述（同步 `<meta name="description">`） |
| `announcement.enabled` | bool | 是否显示首页公告条 |
| `announcement.type` | info/success/warning | 公告配色 |
| `announcement.text` | string(200) | 公告内容 |
| `announcement.linkText` | string(40) | 链接文字 |
| `announcement.linkUrl` | string(500) | 链接地址（必须是 http(s)） |
| `download.primaryUrl` | string(500) | 主下载按钮地址，留空用 Releases 最新版 |
| `download.note` | string(300) | 下载区补充说明 |
| `api.cacheSeconds` | number(0-86400) | GitHub Release 缓存时长 |
| `stats.enabled` | bool | 是否记录访问与下载统计 |

### 安全设计

- **密码**：`scrypt` 加盐哈希存储，不保存明文；校验使用 `crypto.timingSafeEqual` 恒定时间比较
- **会话**：32 字节随机令牌，仅存内存（重启即失效），有效期 12 小时
- **Cookie**：`HttpOnly` + `SameSite=Strict`，HTTPS 下自动追加 `Secure`
- **CSRF**：每个会话独立令牌，所有写操作（PUT/POST/DELETE）必须携带 `X-CSRF-Token` 头
- **登录限流**：同一 IP 连续失败 5 次锁定 10 分钟
- **改密即踢**：修改密码会让所有会话（含当前）立即失效
- **数据目录**：`data/` 已加入 `.gitignore`，切勿提交

### 忘记密码

停止服务后删除 `data/admin.json`，重启会重新生成密码并打印到控制台：

```bash
rm data/admin.json
node server.js
```

---

## 接口一览

### 前台公开接口

| 路径 | 说明 |
|------|------|
| `GET /` | 首页 |
| `GET /api/latest` | GitHub Releases 代理（版本号、发布日期、各平台下载直链），带缓存与降级 |
| `GET /api/site` | 站点公开设置（公告、标题等安全子集） |
| `GET /api/health` | 健康检查 |
| `GET /dl/:kind` | **下载计数跳转**，302 到 GitHub；`:kind` 为 `windows` / `linux` / `source` / `latest` |
| `GET /download` `/releases` `/github` | 302 便捷跳转 |

下载按钮都走 `/dl/*`，因此后台能看到真实的下载点击量（GitHub 侧的下载数只反映资产下载，看不到来源页面）。

### 后台接口

所有接口位于 `/admin/api/`，除 `login` 外均需登录；写操作还需 `X-CSRF-Token`。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/api/login` | 登录，返回 CSRF 令牌并设置会话 Cookie |
| POST | `/admin/api/logout` | 退出 |
| GET | `/admin/api/session` | 当前会话信息 |
| GET | `/admin/api/overview` | 概览：服务器状态 + 统计 + 发布 + 缓存 |
| GET | `/admin/api/stats?days=30` | 时间序列与排行数据 |
| GET / DELETE | `/admin/api/logs` | 请求日志查询 / 清空 |
| GET / PUT | `/admin/api/settings` | 读取 / 修改站点设置 |
| POST | `/admin/api/settings/reset` | 恢复默认设置 |
| POST | `/admin/api/release/refresh` | 刷新 Release 缓存 |
| POST | `/admin/api/password` | 修改密码 |
| POST | `/admin/api/stats/reset` | 重置统计 |
| GET | `/admin/api/registry` | 读取插件注册表（含统计） |
| POST | `/admin/api/registry` | 新增插件条目 |
| PUT | `/admin/api/registry` | 修改条目（body: `{id, patch}`） |
| DELETE | `/admin/api/registry?id=x` | 删除条目 |
| POST | `/admin/api/registry/reseed` | 补回官方示例（幂等） |

**插件注册表字段约束**（服务端白名单校验）：

| 字段 | 规则 |
|------|------|
| `name` | 必填；仅字母数字下划线连字符；最长 60 |
| `version` / `author` | 最长 20 / 80 |
| `description` | 最长 400 |
| `repo` / `homepage` | 必须是 http(s) 链接 |
| `commands` | 最多 20 项，单项最长 40（支持逗号分隔输入） |
| `tags` | 最多 8 项，单项最长 20（支持逗号分隔输入） |
| `published` / `featured` / `official` | 布尔 |

---

## 配置

### 静态配置（config.js）

仓库地址、回退版本、资产识别规则等：

```js
module.exports = {
  repo: 'Qin-collab/KShell',
  repoUrl: 'https://github.com/Qin-collab/KShell',
  releasesUrl: 'https://github.com/Qin-collab/KShell/releases',
  latestReleaseUrl: 'https://github.com/Qin-collab/KShell/releases/latest',

  fallback: { version: '2.0.0', tag: 'v2.0.0' },   // API 不可用时使用

  assetRules: {                                     // 资产归类规则
    windows:  { re: /windows.*\.exe$/i, label: 'Windows 可执行文件', hint: '.exe' },
    linuxDeb: { re: /\.deb$/i,          label: 'Debian/Ubuntu 安装包', hint: '.deb' },
    linuxTar: { re: /linux.*\.tar\.gz$/i, label: 'Linux 通用压缩包', hint: '.tar.gz' },
    source:   { re: /(src|source).*\.(tar\.gz|zip)$/i, label: '源码包', hint: '源码' }
  },

  apiCacheMs: 10 * 60 * 1000,
  port: 3000,
};
```

**发布新版本后无需改代码**：新 Release 一旦发布（并上传符合规则的资产），页面版本号、日期、文件大小与下载直链会自动更新。

### 动态设置

见上文「站点设置」，保存在 `data/settings.json`，优先级高于 `config.js` 中的同类默认值。

---

## 开发工具

### 布局诊断：找出横向溢出

```bash
node tools/diagnose-layout.js http://127.0.0.1:3000/ 390 844
```

输出：

```json
{ "innerWidth": 390, "scrollWidth": 390, "overflowCount": 0, "worst": [] }
```

`overflowCount > 0` 时会列出所有超出视口的元素及其宽度、右边界。

> 使用 CDP 的 `Emulation.setDeviceMetricsOverride`，因为无头模式的 `--window-size` 存在约 500px 最小宽度限制，无法模拟真实手机宽度。

### 整页截图（支持后台登录）

```bash
node tools/screenshot.js .shots/desktop.png http://127.0.0.1:3000/ 1440 900
node tools/screenshot.js .shots/mobile.png  http://127.0.0.1:3000/ 390 844
# 页面很长时按「起始Y + 裁剪高度」分片
node tools/screenshot.js .shots/m2.png http://127.0.0.1:3000/ 390 844 3800 3600
# 后台页面：第 9 个参数为管理员密码，会自动登录
node tools/screenshot.js .shots/admin.png http://127.0.0.1:3000/admin#traffic 1440 900 0 900 你的密码
```

工具会输出**页面探针**（关键区域渲染长度、公告条、下载卡片数量等），便于发现静默失败：

```
页面探针: {"title":"KShell 管理后台","releaseKv":159,"serverKv":247,"chart":2148,...}
```

---

## 技术要点

- **零依赖**：仅用 Node 内置模块（`http`/`fs`/`path`/`zlib`/`crypto`）与内置 `fetch`
- **原子持久化**：数据写入先落临时文件再 `rename`，避免写入中断损坏文件；统计写入带防抖
- **静态资源服务**：MIME 类型、`ETag` + `304` 协商缓存、gzip 压缩、`HEAD` 支持
- **安全**：路径穿越防护（解码后校验前缀，返回 403）、仅允许 `GET/HEAD/POST/PUT/DELETE`、`X-Content-Type-Options: nosniff`、设置字段白名单校验
- **XSS 防护**：后台所有动态渲染走 `esc()` 转义，仅白名单位置允许原始 HTML
- **无 JS 降级**：`<noscript>` 提供可用的下载链接；滚动动画仅在 JS 可用时启用
- **无障碍**：语义化标签、`aria-*`、键盘方向键切换选项卡、`prefers-reduced-motion`、打印样式
- **响应式**：390 / 768 / 1440 三个断点均无横向溢出（已用诊断工具验证）

---

## 部署

### 直接运行

```bash
KSH_ADMIN_PASSWORD='强密码' node server.js --port 3000
```

### systemd 示例

```ini
[Unit]
Description=KShell Website
After=network.target

[Service]
WorkingDirectory=/opt/kshell/HTML
Environment=KSH_ADMIN_PASSWORD=请改成强密码
ExecStart=/usr/bin/node server.js --port 3000
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

### 反向代理

站点可挂在 Nginx / OpenResty 后面，注意保留 `/api/` 与 `/dl/` 的转发，并传递真实协议（HTTPS 下会话 Cookie 才会带 `Secure`）：

```nginx
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

> 后台会显示客户端 IP，若经反向代理务必配置 `X-Forwarded-For` / `X-Real-IP`，否则日志里都是代理 IP。

### 纯静态托管

`public/` 可单独部署到 GitHub Pages / OSS / CDN，但此时：

- `/api/*`、`/dl/*` 不可用 → 页面自动降级为 `app.js` 中的 `FALLBACK` 常量与 Releases 直链
- 后台与统计不可用

需要完整功能请部署 Node 服务。

---

## 协议

本目录遵循 KShell 项目协议：[Apache License 2.0](../LICENSE)
