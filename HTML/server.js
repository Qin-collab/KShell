#!/usr/bin/env node
/**
 * KShell 官网服务器（含管理后台）
 *
 * 纯 Node.js 实现，零第三方依赖（不需要 npm install）。
 *
 * 前台:
 *   GET  /                     首页
 *   GET  /api/latest           GitHub Releases 代理（带缓存与降级）
 *   GET  /api/site             站点公开设置（公告、标题等）
 *   GET  /api/health           健康检查
 *   GET  /dl/:kind             下载计数跳转（windows / linux / source / latest）
 *
 * 后台:
 *   GET  /admin                管理后台页面
 *   POST /admin/api/login      登录
 *   POST /admin/api/logout     退出
 *   GET  /admin/api/session    当前会话
 *   GET  /admin/api/overview   概览（统计 + 发布 + 运行状态）
 *   GET  /admin/api/stats      时间序列
 *   GET  /admin/api/logs       请求日志
 *   GET  /admin/api/settings   读取设置
 *   PUT  /admin/api/settings   修改设置
 *   POST /admin/api/settings/reset   恢复默认设置
 *   POST /admin/api/release/refresh  刷新 Release 缓存
 *   POST /admin/api/password   修改密码
 *   POST /admin/api/stats/reset      重置统计
 *
 * 用法:
 *   node server.js [--port 3000] [--host 0.0.0.0]
 *   KSH_ADMIN_PASSWORD=你的密码 node server.js
 */

'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const config = require('./config');

const { Auth } = require('./lib/auth');
const { Stats } = require('./lib/stats');
const { SiteSettings, PATCHABLE } = require('./lib/site');
const { PluginRegistry } = require('./lib/registry');

const PUBLIC_DIR = path.join(__dirname, 'public');
const ADMIN_DIR = path.join(__dirname, 'admin');
const START_TIME = Date.now();

// ---------------------------------------------------------------------------
// 初始化
// ---------------------------------------------------------------------------

const auth = new Auth();
const stats = new Stats();
const site = new SiteSettings();
const registry = new PluginRegistry();

// ---------------------------------------------------------------------------
// 命令行参数
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const opts = { port: Number(process.env.PORT) || config.port, host: '0.0.0.0' };
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--port' || arg === '-p') opts.port = Number(argv[++i]);
    else if (arg === '--host') opts.host = argv[++i];
    else if (arg === '--help' || arg === '-h') {
      console.log('用法: node server.js [--port 3000] [--host 0.0.0.0]');
      process.exit(0);
    }
  }
  return opts;
}

// ---------------------------------------------------------------------------
// MIME 与响应工具
// ---------------------------------------------------------------------------

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
};

const COMPRESSIBLE = /^(text\/|application\/(javascript|json|xml)|image\/svg)/;

function formatSize(bytes) {
  if (!bytes || bytes < 0) return '';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) { value /= 1024; idx++; }
  return `${value.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`;
}

function classifyAssets(assets) {
  const downloads = [];
  for (const [kind, rule] of Object.entries(config.assetRules)) {
    const hit = (assets || []).find((a) => rule.re.test(a.name || ''));
    if (!hit) continue;
    downloads.push({
      kind,
      label: rule.label,
      hint: rule.hint,
      name: hit.name,
      url: hit.browser_download_url,
      size: hit.size || 0,
      sizeText: formatSize(hit.size),
      downloadCount: hit.download_count || 0,
    });
  }
  return downloads;
}

function fallbackPayload(reason) {
  return {
    version: config.fallback.version,
    tag: config.fallback.tag,
    publishedAt: config.fallback.publishedAt,
    releaseUrl: `${config.releasesUrl}/tag/${config.fallback.tag}`,
    releasesUrl: config.releasesUrl,
    latestReleaseUrl: site.get('download.primaryUrl') || config.latestReleaseUrl,
    repoUrl: config.repoUrl,
    license: config.site.license,
    source: 'fallback',
    reason: reason || 'GitHub API 不可用',
    downloads: [],
  };
}

function finish(req, res, status, body, headers, compressible) {
  const accept = String(req.headers['accept-encoding'] || '');
  const type = headers['Content-Type'] || '';
  const canGzip = compressible !== false && COMPRESSIBLE.test(type) &&
    /\bgzip\b/.test(accept) && body.length >= 1024;
  if (canGzip) {
    headers['Content-Encoding'] = 'gzip';
    headers['Vary'] = 'Accept-Encoding';
    body = zlib.gzipSync(body);
  }
  headers['Content-Length'] = body.length;
  res.writeHead(status, headers);
  res.end(req.method === 'HEAD' ? undefined : body);
}

function sendJson(req, res, status, obj, extraHeaders) {
  finish(req, res, status, Buffer.from(JSON.stringify(obj), 'utf8'),
    Object.assign({
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
    }, extraHeaders || {}));
}

function sendText(req, res, status, text, headers) {
  finish(req, res, status, Buffer.from(text, 'utf8'),
    Object.assign({ 'Content-Type': 'text/plain; charset=utf-8' }, headers || {}), false);
}

function sendRedirect(res, location, extraHeaders) {
  res.writeHead(302, Object.assign({ Location: location, 'Cache-Control': 'no-store' }, extraHeaders || {}));
  res.end();
}

function clientIp(req) {
  const xff = req.headers['x-forwarded-for'];
  if (xff) return String(xff).split(',')[0].trim();
  const real = req.headers['x-real-ip'];
  if (real) return String(real).trim();
  return (req.socket && (req.socket.remoteAddress || '')) || 'unknown';
}

function isHttps(req) {
  return (req.headers['x-forwarded-proto'] || '').split(',')[0].trim() === 'https' ||
    !!(req.socket && req.socket.encrypted);
}

/** 读取请求体（限制大小，防滥用） */
function readBody(req, limit = 64 * 1024) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > limit) {
        reject(new Error('请求体过大'));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

async function readJsonBody(req) {
  const raw = await readBody(req);
  if (!raw.trim()) return {};
  try {
    return JSON.parse(raw);
  } catch (e) {
    throw new Error('JSON 格式错误');
  }
}

// ---------------------------------------------------------------------------
// GitHub Releases 代理（缓存时长由后台设置控制）
// ---------------------------------------------------------------------------

const releaseCache = { payload: null, fetchedAt: 0, inflight: null };

async function getLatestRelease() {
  const ttl = site.cacheMs(config.apiCacheMs);
  const now = Date.now();
  if (releaseCache.payload && now - releaseCache.fetchedAt < ttl) {
    return Object.assign({}, releaseCache.payload, { cached: true, cacheTtlMs: ttl });
  }
  if (releaseCache.inflight) return releaseCache.inflight;

  releaseCache.inflight = (async () => {
    try {
      const url = `https://api.github.com/repos/${config.repo}/releases/latest`;
      const res = await fetch(url, {
        headers: { 'User-Agent': 'kshell-website', Accept: 'application/vnd.github+json' },
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) throw new Error(`GitHub API 返回 ${res.status}`);
      const rel = await res.json();
      const payload = {
        version: String(rel.tag_name || '').replace(/^v/, '') || config.fallback.version,
        tag: rel.tag_name || config.fallback.tag,
        name: rel.name || rel.tag_name || '',
        publishedAt: rel.published_at || rel.created_at || '',
        releaseUrl: rel.html_url || config.latestReleaseUrl,
        releasesUrl: config.releasesUrl,
        latestReleaseUrl: site.get('download.primaryUrl') || config.latestReleaseUrl,
        repoUrl: config.repoUrl,
        license: config.site.license,
        source: 'github-api',
        downloads: classifyAssets(rel.assets),
      };
      releaseCache.payload = payload;
      releaseCache.fetchedAt = Date.now();
      return payload;
    } catch (err) {
      console.warn(`[api] 拉取 GitHub Releases 失败: ${err.message}（使用回退数据）`);
      if (releaseCache.payload) return releaseCache.payload;
      return fallbackPayload(err.message);
    } finally {
      releaseCache.inflight = null;
    }
  })();

  return releaseCache.inflight;
}

function releaseStatus() {
  return {
    cached: !!releaseCache.payload,
    fetchedAt: releaseCache.fetchedAt ? new Date(releaseCache.fetchedAt).toISOString() : null,
    ageSeconds: releaseCache.fetchedAt ? Math.round((Date.now() - releaseCache.fetchedAt) / 1000) : null,
    ttlSeconds: Math.round(site.cacheMs(config.apiCacheMs) / 1000),
    tag: releaseCache.payload ? releaseCache.payload.tag : null,
    source: releaseCache.payload ? releaseCache.payload.source : null,
  };
}

// ---------------------------------------------------------------------------
// 静态资源
// ---------------------------------------------------------------------------

function serveFile(req, res, rootDir, relPath, notFound) {
  let rel = relPath || '/';
  if (rel.endsWith('/') || rel === '') rel += 'index.html';
  const filePath = path.resolve(rootDir, '.' + (rel.startsWith('/') ? rel : '/' + rel));

  if (filePath !== rootDir && !filePath.startsWith(rootDir + path.sep)) {
    return sendText(req, res, 403, '403 Forbidden');
  }

  fs.stat(filePath, (err, st) => {
    if (err || !st.isFile()) return notFound(req, res);

    const ext = path.extname(filePath).toLowerCase();
    const mime = MIME_TYPES[ext] || 'application/octet-stream';
    const etag = `W/"${st.size.toString(16)}-${st.mtimeMs.toString(16)}"`;

    if (req.headers['if-none-match'] === etag) {
      res.writeHead(304, { ETag: etag });
      return res.end();
    }

    fs.readFile(filePath, (readErr, data) => {
      if (readErr) return sendText(req, res, 500, '500 Internal Server Error');
      finish(req, res, 200, data, {
        'Content-Type': mime,
        'ETag': etag,
        'Last-Modified': st.mtime.toUTCString(),
        'X-Content-Type-Options': 'nosniff',
        'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=86400',
      });
    });
  });
}

function send404(req, res) {
  const custom = path.join(PUBLIC_DIR, '404.html');
  fs.readFile(custom, (err, data) => {
    if (err) return sendText(req, res, 404, '404 Not Found');
    finish(req, res, 404, data, { 'Content-Type': 'text/html; charset=utf-8' });
  });
}

// ---------------------------------------------------------------------------
// 后台鉴权辅助
// ---------------------------------------------------------------------------

function currentSession(req) {
  const cookies = Auth.parseCookies(req.headers.cookie);
  const token = cookies[Auth.COOKIE_NAME];
  const session = auth.getSession(token);
  return session ? { token, session } : null;
}

/** 未登录 → 401；写操作缺少或错误 CSRF → 403 */
function guard(req, res, sess) {
  if (!sess) {
    sendJson(req, res, 401, { error: '未登录或会话已过期' });
    return false;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    const csrf = req.headers['x-csrf-token'];
    if (!csrf || csrf !== sess.session.csrf) {
      sendJson(req, res, 403, { error: 'CSRF 校验失败，请刷新页面重试' });
      return false;
    }
  }
  return true;
}

// ---------------------------------------------------------------------------
// 后台 API
// ---------------------------------------------------------------------------

async function handleAdminApi(req, res, pathname) {
  const method = req.method;
  const sess = currentSession(req);

  // ---------------------------------------------------------- 登录
  if (pathname === '/admin/api/login' && method === 'POST') {
    const ip = clientIp(req);
    const lockMs = auth.lockRemainingMs(ip);
    if (lockMs > 0) {
      return sendJson(req, res, 429, {
        error: `登录失败次数过多，请 ${Math.ceil(lockMs / 60000)} 分钟后再试`,
      });
    }

    let body;
    try { body = await readJsonBody(req); } catch (e) { return sendJson(req, res, 400, { error: e.message }); }

    if (!auth.verify(body.password || '')) {
      auth.recordFailure(ip);
      return sendJson(req, res, 401, { error: '密码错误' });
    }

    auth.clearFailures(ip);
    const created = auth.createSession(ip, req.headers['user-agent'] || '');
    stats.recordLogin();
    return sendJson(req, res, 200, {
      ok: true,
      username: auth.store.data.username,
      csrf: created.csrf,
      expiresAt: new Date(created.expiresAt).toISOString(),
    }, { 'Set-Cookie': auth.buildCookie(created.token, isHttps(req)) });
  }

  // ---------------------------------------------------------- 退出
  if (pathname === '/admin/api/logout' && method === 'POST') {
    if (sess) auth.destroySession(sess.token);
    return sendJson(req, res, 200, { ok: true }, { 'Set-Cookie': auth.buildLogoutCookie(isHttps(req)) });
  }

  // ---------------------------------------------------------- 会话
  if (pathname === '/admin/api/session' && method === 'GET') {
    if (!sess) return sendJson(req, res, 200, { authenticated: false });
    return sendJson(req, res, 200, {
      authenticated: true,
      username: auth.store.data.username,
      csrf: sess.session.csrf,
      expiresAt: new Date(sess.session.expiresAt).toISOString(),
      loginCount: auth.store.data.loginCount || 0,
      lastLoginAt: auth.store.data.lastLoginAt,
      lastLoginIp: auth.store.data.lastLoginIp,
      sessionTtlSeconds: Math.floor(Auth.SESSION_TTL_MS / 1000),
    });
  }

  // ---------------------------------------------------------- 概览
  if (pathname === '/admin/api/overview' && method === 'GET') {
    if (!guard(req, res, sess)) return;
    const release = await getLatestRelease();
    return sendJson(req, res, 200, {
      server: {
        uptimeSeconds: Math.round((Date.now() - START_TIME) / 1000),
        node: process.version,
        platform: process.platform,
        memoryMB: Math.round(process.memoryUsage().rss / 1048576),
        pid: process.pid,
        startedAt: new Date(START_TIME).toISOString(),
      },
      stats: stats.overview(),
      release: {
        tag: release.tag,
        version: release.version,
        publishedAt: release.publishedAt,
        source: release.source,
        releaseUrl: release.releaseUrl,
        assets: (release.downloads || []).map((d) => ({
          kind: d.kind, name: d.name, sizeText: d.sizeText, downloadCount: d.downloadCount, url: d.url,
        })),
      },
      cache: releaseStatus(),
      auth: {
        sessions: auth.activeSessionCount(),
        loginCount: auth.store.data.loginCount || 0,
        lastLoginAt: auth.store.data.lastLoginAt,
        lastLoginIp: auth.store.data.lastLoginIp,
        sessionTtlSeconds: Math.floor(Auth.SESSION_TTL_MS / 1000),
      },
      site: { updatedAt: site.get('updatedAt'), statsEnabled: site.get('stats.enabled') },
    });
  }

  // ---------------------------------------------------------- 统计
  if (pathname === '/admin/api/stats' && method === 'GET') {
    if (!guard(req, res, sess)) return;
    const days = Math.min(Math.max(Number(new URL(req.url, 'http://x').searchParams.get('days')) || 30, 1), 120);
    return sendJson(req, res, 200, {
      days,
      series: stats.series(days),
      overview: stats.overview(),
    });
  }

  // ---------------------------------------------------------- 日志
  if (pathname === '/admin/api/logs' && method === 'GET') {
    if (!guard(req, res, sess)) return;
    const limit = Math.min(Math.max(Number(new URL(req.url, 'http://x').searchParams.get('limit')) || 100, 1), 300);
    return sendJson(req, res, 200, { logs: stats.getLogs(limit) });
  }

  if (pathname === '/admin/api/logs' && method === 'DELETE') {
    if (!guard(req, res, sess)) return;
    stats.clearLogs();
    return sendJson(req, res, 200, { ok: true });
  }

  // ---------------------------------------------------------- 设置
  if (pathname === '/admin/api/settings' && method === 'GET') {
    if (!guard(req, res, sess)) return;
    return sendJson(req, res, 200, { settings: site.all(), patchable: Object.keys(PATCHABLE) });
  }

  if (pathname === '/admin/api/settings' && method === 'PUT') {
    if (!guard(req, res, sess)) return;
    let body;
    try { body = await readJsonBody(req); } catch (e) { return sendJson(req, res, 400, { error: e.message }); }
    const result = site.patch(body.patch || body, auth.store.data.username);
    return sendJson(req, res, 200, {
      ok: true,
      settings: site.all(),
      applied: result.applied,
      rejected: result.rejected,
    });
  }

  if (pathname === '/admin/api/settings/reset' && method === 'POST') {
    if (!guard(req, res, sess)) return;
    return sendJson(req, res, 200, { ok: true, settings: site.reset(auth.store.data.username) });
  }

  // ---------------------------------------------------------- Release 缓存
  if (pathname === '/admin/api/release/refresh' && method === 'POST') {
    if (!guard(req, res, sess)) return;
    releaseCache.payload = null;
    releaseCache.fetchedAt = 0;
    const release = await getLatestRelease();
    return sendJson(req, res, 200, { ok: true, tag: release.tag, source: release.source, cache: releaseStatus() });
  }

  // ---------------------------------------------------------- 修改密码
  if (pathname === '/admin/api/password' && method === 'POST') {
    if (!guard(req, res, sess)) return;
    let body;
    try { body = await readJsonBody(req); } catch (e) { return sendJson(req, res, 400, { error: e.message }); }

    if (!auth.verify(body.current || '')) {
      return sendJson(req, res, 400, { error: '当前密码不正确' });
    }
    const next = String(body.next || '');
    if (next.length < 8) return sendJson(req, res, 400, { error: '新密码至少 8 位' });

    auth.setPassword(next);   // 同时使所有会话失效
    return sendJson(req, res, 200, { ok: true, message: '密码已更新，请重新登录' },
      { 'Set-Cookie': auth.buildLogoutCookie(isHttps(req)) });
  }

  // ---------------------------------------------------------- 重置统计
  if (pathname === '/admin/api/stats/reset' && method === 'POST') {
    if (!guard(req, res, sess)) return;
    stats.reset();
    return sendJson(req, res, 200, { ok: true, message: '统计数据已重置' });
  }

  // ---------------------------------------------------------- 插件注册表
  if (pathname === '/admin/api/registry' && method === 'GET') {
    if (!guard(req, res, sess)) return;
    return sendJson(req, res, 200, {
      plugins: registry.all(),
      stats: registry.stats(),
      updatedAt: registry.store.data.updatedAt,
    });
  }

  if (pathname === '/admin/api/registry' && method === 'POST') {
    if (!guard(req, res, sess)) return;
    let body;
    try { body = await readJsonBody(req); } catch (e) { return sendJson(req, res, 400, { error: e.message }); }
    const result = registry.add(body);
    if (!result.ok) return sendJson(req, res, 400, { error: result.error });
    return sendJson(req, res, 200, { ok: true, entry: result.entry, plugins: registry.all(), stats: registry.stats() });
  }

  if (pathname === '/admin/api/registry' && method === 'PUT') {
    if (!guard(req, res, sess)) return;
    let body;
    try { body = await readJsonBody(req); } catch (e) { return sendJson(req, res, 400, { error: e.message }); }
    const id = String(body.id || '').trim();
    if (!id) return sendJson(req, res, 400, { error: '缺少 id' });
    const result = registry.update(id, body.patch || body);
    if (!result.ok) return sendJson(req, res, 400, { error: result.error });
    return sendJson(req, res, 200, { ok: true, entry: result.entry, plugins: registry.all(), stats: registry.stats() });
  }

  if (pathname === '/admin/api/registry' && method === 'DELETE') {
    if (!guard(req, res, sess)) return;
    const id = new URL(req.url, 'http://x').searchParams.get('id');
    if (!id) return sendJson(req, res, 400, { error: '缺少 id 参数' });
    const result = registry.remove(id);
    if (!result.ok) return sendJson(req, res, 400, { error: result.error });
    return sendJson(req, res, 200, { ok: true, entry: result.entry, plugins: registry.all(), stats: registry.stats() });
  }

  if (pathname === '/admin/api/registry/reseed' && method === 'POST') {
    if (!guard(req, res, sess)) return;
    const result = registry.reseed();
    return sendJson(req, res, 200, {
      ok: true, added: result.added,
      plugins: registry.all(), stats: registry.stats(),
    });
  }

  return sendJson(req, res, 404, { error: '接口不存在' });
}

// ---------------------------------------------------------------------------
// 主路由
// ---------------------------------------------------------------------------

async function handleRequest(req, res) {
  const started = Date.now();
  let pathname;
  try {
    pathname = new URL(req.url, `http://${req.headers.host || 'localhost'}`).pathname;
  } catch (e) {
    return sendText(req, res, 400, '400 Bad Request');
  }
  const method = req.method;

  res.on('finish', () => {
    const ms = Date.now() - started;
    const isAsset = /\.(css|js|svg|png|jpe?g|webp|ico|woff2?|map)$/i.test(pathname);
    if (!isAsset) {
      stats.pushLog({
        t: Date.now(),
        ip: clientIp(req),
        method,
        path: pathname,
        status: res.statusCode,
        ms,
        ua: req.headers['user-agent'] || '',
      });
      if (site.get('stats.enabled') && (method === 'GET' || method === 'HEAD') &&
          !pathname.startsWith('/admin/api/')) {
        stats.recordVisit(pathname, req.headers.referer, req.headers['user-agent'], clientIp(req));
      }
    }
    console.log(`${method} ${pathname} → ${res.statusCode} (${ms}ms)`);
  });

  if (!['GET', 'HEAD', 'POST', 'PUT', 'DELETE'].includes(method)) {
    res.writeHead(405, { Allow: 'GET, HEAD, POST, PUT, DELETE' });
    return res.end();
  }

  // ------------------------------------------------------------- 后台接口
  if (pathname.startsWith('/admin/api/')) {
    return handleAdminApi(req, res, pathname);
  }

  // 除后台接口外，其余路由都是只读的（页面、静态资源、公开接口、跳转）
  if (method !== 'GET' && method !== 'HEAD') {
    res.writeHead(405, { Allow: 'GET, HEAD' });
    return res.end();
  }

  // ------------------------------------------------------------- 后台页面
  if (pathname === '/admin' || pathname === '/admin/') {
    return serveFile(req, res, ADMIN_DIR, '/index.html', send404);
  }
  if (pathname.startsWith('/admin/')) {
    return serveFile(req, res, ADMIN_DIR, pathname.slice('/admin'.length), send404);
  }

  // ------------------------------------------------------------- 下载计数跳转
  if (pathname.startsWith('/dl/')) {
    const kind = pathname.slice(4).replace(/\/+$/, '') || 'latest';
    const release = await getLatestRelease();
    let target = release.latestReleaseUrl || config.latestReleaseUrl;

    if (kind === 'source') {
      const asset = (release.downloads || []).find((d) => d.kind === 'source');
      target = asset ? asset.url : `${config.repoUrl}/archive/refs/heads/main.zip`;
    } else if (kind !== 'latest') {
      const asset = (release.downloads || []).find((d) => d.kind === kind);
      if (asset) target = asset.url;
    }

    if (site.get('stats.enabled')) stats.recordDownload(kind);
    return sendRedirect(res, target);
  }

  // ------------------------------------------------------------- 开发者社区
  if (pathname === '/community' || pathname === '/community/') {
    return serveFile(req, res, PUBLIC_DIR, '/community.html', send404);
  }

  // ------------------------------------------------------------- 公开接口
  if (pathname === '/api/latest') {
    stats.recordApiCall();
    return sendJson(req, res, 200, Object.assign({}, await getLatestRelease(), {
      site: config.site,
      serverTime: new Date().toISOString(),
    }));
  }

  if (pathname === '/api/site') {
    stats.recordApiCall();
    return sendJson(req, res, 200, site.publicView());
  }

  // 社区插件画廊数据
  if (pathname === '/api/plugins') {
    stats.recordApiCall();
    const stats_ = registry.stats();
    return sendJson(req, res, 200, {
      plugins: registry.published(),
      tags: stats_.tags,
      count: stats_.published,
      updatedAt: registry.store.data.updatedAt,
      submitUrl: `${config.repoUrl}/issues`,
    }, { 'Cache-Control': 'public, max-age=120' });
  }

  if (pathname === '/api/health') {
    return sendJson(req, res, 200, {
      status: 'ok',
      uptimeSeconds: Math.round((Date.now() - START_TIME) / 1000),
      node: process.version,
      cachedRelease: releaseCache.payload ? releaseCache.payload.tag : null,
    });
  }

  // ------------------------------------------------------------- 便捷跳转
  if (pathname === '/download' || pathname === '/download/') {
    return sendRedirect(res, site.get('download.primaryUrl') || config.latestReleaseUrl);
  }
  if (pathname === '/releases' || pathname === '/releases/') {
    return sendRedirect(res, config.releasesUrl);
  }
  if (pathname === '/github' || pathname === '/github/') {
    return sendRedirect(res, config.repoUrl);
  }

  // ------------------------------------------------------------- 前台静态
  return serveFile(req, res, PUBLIC_DIR, pathname, send404);
}

// ---------------------------------------------------------------------------
// 启动
// ---------------------------------------------------------------------------

const opts = parseArgs(process.argv);
const generated = auth.init();

const server = http.createServer((req, res) => {
  handleRequest(req, res).catch((err) => {
    console.error('[error]', err);
    if (!res.headersSent) sendText(req, res, 500, '500 Internal Server Error');
  });
});

server.listen(opts.port, opts.host, () => {
  const shown = opts.host === '0.0.0.0' ? 'localhost' : opts.host;
  console.log('');
  console.log('  KShell 官网已启动');
  console.log('  ─────────────────────────────────────────────');
  console.log(`  前台     : http://${shown}:${opts.port}`);
  console.log(`  后台     : http://${shown}:${opts.port}/admin`);
  console.log(`  仓库地址 : ${config.repoUrl}`);
  console.log('  ─────────────────────────────────────────────');
  if (generated) {
    console.log('  ⚠ 首次运行，已生成管理员密码（请立即保存）：');
    console.log('');
    console.log(`      用户名 : ${auth.store.data.username}`);
    console.log(`      密  码 : ${generated}`);
    console.log('');
    console.log('    登录后请在「安全设置」中修改密码。');
    console.log('    也可用环境变量固定：KSH_ADMIN_PASSWORD=xxx node server.js');
  } else {
    console.log(`  后台账号 : ${auth.store.data.username}`);
  }
  console.log('  ─────────────────────────────────────────────');
  console.log('  按 Ctrl+C 停止');
  console.log('');
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`端口 ${opts.port} 已被占用，请换一个：node server.js --port 3001`);
  } else {
    console.error('服务启动失败:', err.message);
  }
  process.exit(1);
});

/** 优雅退出：落盘未保存的统计数据 */
function shutdown(signal) {
  console.log(`\n收到 ${signal}，正在保存数据并关闭服务...`);
  try { stats.flush(); } catch (e) { /* 忽略 */ }
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 3000).unref();
}

for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => shutdown(sig));
