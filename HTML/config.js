/**
 * KShell 官网配置
 *
 * 所有对外链接、版本回退值集中在此处，便于维护。
 */

module.exports = {
  // GitHub 仓库
  repo: 'Qin-collab/KShell',
  repoUrl: 'https://github.com/Qin-collab/KShell',

  // Releases 相关地址
  releasesUrl: 'https://github.com/Qin-collab/KShell/releases',
  latestReleaseUrl: 'https://github.com/Qin-collab/KShell/releases/latest',
  issuesUrl: 'https://github.com/Qin-collab/KShell/issues',

  // 版本回退值：GitHub API 不可用时使用（限流、离线等）
  fallback: {
    version: '2.0.0',
    tag: 'v2.0.0',
    publishedAt: '2026-10-02T08:42:06Z',
  },

  // 站点信息
  site: {
    title: 'KShell',
    tagline: '纯 Python 编写的跨平台终端',
    license: 'Apache-2.0',
    commandCount: 68,
    builtinCount: 36,
    extraCount: 32,
    themeCount: 6,
    platforms: ['Windows', 'macOS', 'Linux'],
  },

  // 资产识别规则：用于从 release assets 中挑选各平台安装包
  assetRules: {
    windows: { re: /windows.*\.exe$/i, label: 'Windows 可执行文件', hint: '.exe' },
    linuxDeb: { re: /\.deb$/i, label: 'Debian/Ubuntu 安装包', hint: '.deb' },
    linuxTar: { re: /linux.*\.tar\.gz$/i, label: 'Linux 通用压缩包', hint: '.tar.gz' },
    source: { re: /(src|source).*\.(tar\.gz|zip)$/i, label: '源码包', hint: '源码' },
  },

  // GitHub API 缓存时长（毫秒），避免触发 60 次/小时的匿名限流
  apiCacheMs: 10 * 60 * 1000,

  // 服务端口（可被 --port 或 PORT 环境变量覆盖）
  port: 3000,
};
