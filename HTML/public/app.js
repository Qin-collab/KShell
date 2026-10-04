/* ==========================================================================
   KShell 官网前端逻辑
   · 从 /api/latest 读取最新版本并渲染下载卡片（失败时降级到静态链接）
   · 终端打字动画、主题预览、选项卡、复制按钮、滚动显现
   无任何第三方依赖
   ========================================================================== */

(function () {
  'use strict';

  /* ---------------------------------------------------------------- 配置 */

  var FALLBACK = {
    version: '2.0.0',
    tag: 'v2.0.0',
    publishedAt: '2026-10-02T08:42:06Z',
    releasesUrl: 'https://github.com/Qin-collab/KShell/releases',
    latestReleaseUrl: 'https://github.com/Qin-collab/KShell/releases/latest',
    repoUrl: 'https://github.com/Qin-collab/KShell',
    license: 'Apache-2.0',
    downloads: []
  };

  var THEMES = [
    { name: 'default',   label: '默认',      colors: ['#00c853', '#2962ff', '#00e5ff', '#e0e0e0', '#ff1744'] },
    { name: 'dark',      label: '暗色',      colors: ['#69f0ae', '#82b1ff', '#18ffff', '#cfd8dc', '#ff5252'] },
    { name: 'light',     label: '亮色',      colors: ['#2e7d32', '#1565c0', '#00838f', '#37474f', '#c62828'] },
    { name: 'ocean',     label: '海洋',      colors: ['#26c6da', '#4dd0e1', '#80deea', '#b2ebf2', '#ffab40'] },
    { name: 'monokai',   label: 'Monokai',   colors: ['#a6e22e', '#66d9ef', '#f92672', '#f8f8f2', '#fd971f'] },
    { name: 'solarized', label: 'Solarized', colors: ['#859900', '#268bd2', '#2aa198', '#93a1a1', '#dc322f'] }
  ];

  /* ---------------------------------------------------------- 小工具函数 */

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function formatDate(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    var pad = function (n) { return n < 10 ? '0' + n : String(n); };
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }

  var prefersReducedMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------------------------------ 版本信息与下载 */

  function applyVersionInfo(data) {
    var v = 'v' + String(data.version || FALLBACK.version).replace(/^v/, '');

    $$('[data-version]').forEach(function (el) { el.textContent = v; });
    $$('[data-license]').forEach(function (el) { el.textContent = data.license || FALLBACK.license; });

    var meta = $('#release-meta');
    if (meta) {
      var date = formatDate(data.publishedAt);
      meta.textContent = date ? ('发布于 ' + date + ' · 版本 ' + v) : ('当前版本 ' + v);
    }

    var dlVer = $('#download-version');
    if (dlVer) dlVer.textContent = date ? ('· ' + v + '（' + date + '）') : ('· ' + v);

    document.title = 'KShell ' + v + ' — 纯 Python 编写的跨平台终端';
  }

  function osIcon(kind) {
    if (kind === 'windows') {
      return '<svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor" aria-hidden="true">' +
        '<path d="M3 5.6l7.2-1v7.1H3V5.6zm0 12.8l7.2 1v-7H3v6zM11.3 4.4L21 3v8.7h-9.7V4.4zm0 15.2L21 21v-8.6h-9.7v7.2z"/></svg>';
    }
    if (kind === 'linux') {
      return '<svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor" aria-hidden="true">' +
        '<path d="M12 2c-2.2 0-4 2.4-4 5.3 0 1.4.3 2.6.3 2.6-.9 1.4-2.6 3.4-3.2 5.6-.5 1.7.1 3.3 1.4 3.6.9.2 1.7-.3 2.3-1 .6.7 1.6 1.2 3.2 1.2s2.6-.5 3.2-1.2c.6.7 1.4 1.2 2.3 1 1.3-.3 1.9-1.9 1.4-3.6-.6-2.2-2.3-4.2-3.2-5.6 0 0 .3-1.2.3-2.6C16 4.4 14.2 2 12 2zm-1.6 4.2a.9.9 0 1 1 1.8 0 .9.9 0 0 1-1.8 0zm3.4 0a.9.9 0 1 1 1.8 0 .9.9 0 0 1-1.8 0z"/></svg>';
    }
    return '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>';
  }

  function dlCard(opts) {
    var featured = opts.featured ? ' is-featured' : '';
    var badge = opts.badge ? '<span class="dl-badge">' + escapeHtml(opts.badge) + '</span>' : '';
    var file = opts.file ? '<p class="dl-file">' + escapeHtml(opts.file) + '</p>' : '';
    var meta = opts.meta && opts.meta.length
      ? '<div class="dl-meta">' + opts.meta.map(function (m) {
          return '<span>' + escapeHtml(m.label) + ' <b>' + escapeHtml(m.value) + '</b></span>';
        }).join('') + '</div>'
      : '<div class="dl-meta"></div>';

    return '<article class="dl-card' + featured + '">' + badge +
      '<div class="dl-os">' + osIcon(opts.kind) + '<h3>' + escapeHtml(opts.title) + '</h3></div>' +
      '<p class="dl-file">' + escapeHtml(opts.desc || '') + '</p>' +
      file + meta +
      '<a class="btn ' + (featured ? 'btn-primary' : 'btn-ghost') + '" href="' + escapeHtml(opts.url) +
      '" target="_blank" rel="noopener">' + escapeHtml(opts.cta) + '</a>' +
      (opts.hint ? '<p class="dl-hint">' + opts.hint + '</p>' : '') +
      '</article>';
  }

  function renderDownloads(data) {
    var host = $('#downloads');
    if (!host) return;

    var downloads = data.downloads || [];
    var byKind = {};
    downloads.forEach(function (d) { byKind[d.kind] = d; });

    var releases = data.releasesUrl || FALLBACK.releasesUrl;
    var cards = [];

    /* Windows —— 优先给出直链 */
    var win = byKind.windows;
    if (win) {
      cards.push(dlCard({
        kind: 'windows', title: 'Windows', featured: true, badge: '推荐',
        desc: '独立可执行文件，无需安装 Python',
        file: win.name,
        meta: [
          { label: '大小', value: win.sizeText || '—' },
          { label: '下载', value: (win.downloadCount || 0) + ' 次' }
        ],
        url: '/dl/windows', cta: '下载 ' + (win.hint || '.exe')
      }));
    } else {
      cards.push(dlCard({
        kind: 'windows', title: 'Windows', featured: true,
        desc: '前往 Releases 获取 Windows 可执行文件',
        meta: [{ label: '版本', value: 'v' + (data.version || FALLBACK.version) }],
        url: releases, cta: '前往 Releases'
      }));
    }

    /* Linux —— 最新版若无可执行产物，则引导源码/APT */
    var deb = byKind.linuxDeb || byKind.linuxTar;
    if (deb) {
      cards.push(dlCard({
        kind: 'linux', title: 'Linux',
        desc: deb.label || 'Debian/Ubuntu 安装包',
        file: deb.name,
        meta: [
          { label: '大小', value: deb.sizeText || '—' },
          { label: '下载', value: (deb.downloadCount || 0) + ' 次' }
        ],
        url: '/dl/linux', cta: '下载 ' + (deb.hint || '')
      }));
    } else {
      cards.push(dlCard({
        kind: 'linux', title: 'Linux',
        desc: '当前版本未提供 Linux 预编译包，可源码运行或使用 APT 仓库',
        meta: [{ label: '方式', value: 'APT / 源码' }],
        url: '#install', cta: '查看安装方式',
        hint: '直接运行 <code>python3 kshell.py</code> 即可，零依赖'
      }));
    }

    /* 源码 —— 提供仓库快照下载 */
    cards.push(dlCard({
      kind: 'source', title: '源码',
      desc: 'Python 3.6+ 即可运行，也可自行构建各平台产物',
      file: (data.repo || 'Qin-collab/KShell') + ' @ ' + (data.tag || FALLBACK.tag),
      meta: [{ label: '协议', value: data.license || FALLBACK.license }],
      url: '/dl/source',
      cta: '下载源码 ZIP',
      hint: '或 <code>git clone ' + escapeHtml(data.repoUrl || FALLBACK.repoUrl) + '</code>'
    }));

    host.innerHTML = cards.join('');
  }

  function renderDownloadError() {
    var host = $('#downloads');
    if (!host || host.children.length) return;
    // 极端情况下（无 JS 之外的失败）也要保证按钮可用
    host.innerHTML = dlCard({
      kind: 'windows', title: '下载', featured: true,
      desc: '无法获取版本信息，请直接前往 GitHub Releases',
      meta: [{ label: '版本', value: FALLBACK.tag }],
      url: FALLBACK.releasesUrl, cta: '前往 Releases 页面'
    });
  }

  /* -------------------------------------------------- 后台可配置内容 */

  /** 读取 /api/site 并应用后台配置（公告条、下载按钮、说明） */
  function loadSiteSettings() {
    if (!window.fetch) return Promise.resolve();

    return fetch('/api/site', { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (cfg) {
        if (!cfg) return;

        // 公告条
        var box = $('#announcement');
        if (box) {
          var a = cfg.announcement || {};
          if (a.enabled && a.text) {
            var tag = { info: '公告', success: '更新', warning: '注意' }[a.type] || '公告';
            box.className = 'announcement is-' + (a.type || 'info');
            box.innerHTML = '<div class="wrap">' +
              '<span class="announcement-tag">' + escapeHtml(tag) + '</span>' +
              '<span>' + escapeHtml(a.text) + '</span>' +
              (a.linkUrl ? '<a href="' + escapeHtml(a.linkUrl) + '" target="_blank" rel="noopener">' +
                escapeHtml(a.linkText || '查看详情') + ' →</a>' : '') +
              '</div>';
            box.hidden = false;
          } else {
            box.hidden = true;
          }
        }

        // 下载区说明
        var note = $('#download-note');
        if (note && cfg.download && cfg.download.note) {
          note.textContent = cfg.download.note;
          note.hidden = false;
        }

        // 主下载按钮地址（后台可覆盖）
        var primary = (cfg.download && cfg.download.primaryUrl) || '/dl/latest';
        ['#download-primary', '#download-all'].forEach(function (sel) {
          var el = $(sel);
          if (el) el.setAttribute('href', primary);
        });

        // 站点标题/简介（后台可改）
        if (cfg.site) {
          if (cfg.site.title) {
            $$('.brand-name, .footer-brand b').forEach(function (el) { el.textContent = cfg.site.title; });
          }
          if (cfg.site.tagline) {
            var fp = $('.footer-brand p');
            if (fp) fp.textContent = cfg.site.tagline;
          }
          if (cfg.site.description) {
            var md = $('meta[name="description"]');
            if (md) md.setAttribute('content', cfg.site.description);
          }
        }
      })
      .catch(function (err) {
        console.warn('无法获取站点设置:', err.message);
      });
  }

  function loadLatest() {
    if (!window.fetch) { applyVersionInfo(FALLBACK); renderDownloads(FALLBACK); return; }

    fetch('/api/latest', { headers: { Accept: 'application/json' } })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        applyVersionInfo(data);
        renderDownloads(data);
      })
      .catch(function (err) {
        // 降级：使用内置回退值，站点仍可正常浏览与下载
        console.warn('无法获取 /api/latest，使用回退数据:', err.message);
        applyVersionInfo(FALLBACK);
        renderDownloads(FALLBACK);
      });
  }

  /* ------------------------------------------------------------ 主题预览 */

  function renderThemes() {
    var host = $('#themes-grid');
    if (!host) return;

    var prompts = [
      { user: '\u25cf', dir: '~/project' },
      { user: '\u25cf', dir: '~/src' }
    ];

    host.innerHTML = THEMES.map(function (t) {
      var bar = t.colors.map(function (c) {
        return '<i style="background:' + c + '"></i>';
      }).join('');

      var swatch = t.colors.map(function (c) {
        return '<span style="color:' + c + '">\u2588\u2588</span>';
      }).join(' ');

      var preview =
        '<span style="color:' + t.colors[0] + '">user</span>' +
        '<span style="color:#5d6b80">:</span>' +
        '<span style="color:' + t.colors[1] + '">' + prompts[0].dir + '</span>' +
        '<span style="color:' + t.colors[0] + '">$ </span>' +
        '<span style="color:' + t.colors[3] + '">ls -l</span>\n' +
        '<span style="color:' + t.colors[1] + '">drwxr-xr-x  docs</span>\n' +
        '<span style="color:' + t.colors[3] + '">-rw-r--r--  kshell.py</span>\n' +
        '<span style="color:' + t.colors[4] + '">Error: 未找到命令</span>';

      return '<div class="theme-card">' +
        '<div class="theme-bar">' + bar + '</div>' +
        '<div class="theme-body">' +
        '<div class="theme-name">' + escapeHtml(t.name) + ' · ' + escapeHtml(t.label) + '</div>' +
        '<div class="theme-preview">' + preview + '</div>' +
        '<div class="theme-preview" style="margin-top:8px">' + swatch + '</div>' +
        '</div></div>';
    }).join('');
  }

  /* -------------------------------------------------------- 终端打字动画 */

  var DEMO = [
    { type: 'dim', text: 'KShell v2.1 - 跨平台 Python 终端' },
    { type: 'dim', text: 'Type help for commands, theme for themes.' },
    { type: 'cmd', text: 'git status' },
    { type: 'out', text: 'On branch main' },
    { type: 'out', text: 'nothing to commit, working tree clean' },
    { type: 'cmd', text: 'plugin list' },
    { type: 'out', text: '  hello     1.0.0  已加载  2  最小示例插件' },
    { type: 'out', text: '  pwgen     1.0.0  已加载  3  密码与 UUID 生成器' },
    { type: 'out', text: '  sysinfo   1.0.0  已加载  2  系统信息速查' },
    { type: 'cmd', text: 'pwgen 2 16' },
    { type: 'ok', text: '  xK9#mQ4vLp2$RtWn' },
    { type: 'ok', text: '  7bF3@hYz1Ns8!cJd' },
    { type: 'cmd', text: 'ping -n 2 127.0.0.1' },
    { type: 'out', text: 'Reply from 127.0.0.1: bytes=32 time<1ms TTL=128' },
    { type: 'out', text: 'Reply from 127.0.0.1: bytes=32 time<1ms TTL=128' },
    { type: 'cmd', text: 'path -s git' },
    { type: 'cyan', text: '    C:\\Program Files\\Git\\cmd\\git.exe' },
    { type: 'cmd', text: 'calc (1+2)*3' },
    { type: 'ok', text: '9' }
  ];

  var PROMPT = '<span class="t-user">user</span><span class="t-dim">:</span>' +
               '<span class="t-dir">~/project</span><span class="t-user">&gt; </span>';

  function renderDemoInstant() {
    var target = $('#term-body code');
    if (!target) return;
    var html = DEMO.map(function (step) {
      if (step.type === 'cmd') {
        return PROMPT + '<span class="t-cmd">' + escapeHtml(step.text) + '</span>';
      }
      var cls = { out: 't-out', ok: 't-ok', dim: 't-dim', cyan: 't-cyan', warn: 't-warn' }[step.type] || 't-out';
      return '<span class="' + cls + '">' + escapeHtml(step.text) + '</span>';
    }).join('\n');
    target.innerHTML = html + '\n' + PROMPT + '<span class="cursor"></span>';
  }

  function runDemoTyping() {
    var target = $('#term-body code');
    if (!target) return;

    if (prefersReducedMotion) { renderDemoInstant(); return; }

    var lines = [];
    var idx = 0;

    function paint(partial) {
      var html = lines.join('\n');
      if (partial) html += (html ? '\n' : '') + partial;
      target.innerHTML = html + '\n' + PROMPT + '<span class="cursor"></span>';
    }

    function nextStep() {
      if (idx >= DEMO.length) return;
      var step = DEMO[idx++];

      if (step.type !== 'cmd') {
        var cls = { out: 't-out', ok: 't-ok', dim: 't-dim', cyan: 't-cyan', warn: 't-warn' }[step.type] || 't-out';
        lines.push('<span class="' + cls + '">' + escapeHtml(step.text) + '</span>');
        paint('');
        setTimeout(nextStep, step.type === 'dim' ? 90 : 130);
        return;
      }

      // 逐字符打印命令
      var typed = '';
      var chars = step.text.split('');
      (function typeChar() {
        if (!chars.length) {
          lines.push(PROMPT + '<span class="t-cmd">' + escapeHtml(typed) + '</span>');
          paint('');
          setTimeout(nextStep, 260);
          return;
        }
        typed += chars.shift();
        paint(PROMPT + '<span class="t-cmd">' + escapeHtml(typed) + '</span>');
        setTimeout(typeChar, 42);
      })();
    }

    // 等页面渲染完毕再开始
    setTimeout(nextStep, 420);
  }

  /* ------------------------------------------------------------ 选项卡 */

  function initTabs() {
    var tabs = $$('.tab');
    if (!tabs.length) return;

    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var panelId = tab.getAttribute('aria-controls');

        tabs.forEach(function (t) {
          var active = t === tab;
          t.classList.toggle('is-active', active);
          t.setAttribute('aria-selected', active ? 'true' : 'false');
        });

        $$('.panel').forEach(function (p) {
          p.classList.toggle('is-active', p.id === panelId);
        });
      });

      // 键盘方向键切换
      tab.addEventListener('keydown', function (e) {
        var i = tabs.indexOf(tab);
        var dir = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (!dir) return;
        e.preventDefault();
        var next = tabs[(i + dir + tabs.length) % tabs.length];
        next.focus();
        next.click();
      });
    });
  }

  /* ---------------------------------------------------------- 复制按钮 */

  function initCopy() {
    $$('.copy-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var text = btn.getAttribute('data-copy') || '';
        var done = function () {
          var old = btn.textContent;
          btn.textContent = '已复制';
          btn.classList.add('is-done');
          setTimeout(function () {
            btn.textContent = old;
            btn.classList.remove('is-done');
          }, 1600);
        };

        if (navigator.clipboard && window.isSecureContext !== false) {
          navigator.clipboard.writeText(text).then(done).catch(fallbackCopy);
        } else {
          fallbackCopy();
        }

        function fallbackCopy() {
          var ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          try { document.execCommand('copy'); done(); } catch (e) { /* 忽略 */ }
          document.body.removeChild(ta);
        }
      });
    });
  }

  /* ---------------------------------------------------------- 滚动显现 */

  function initReveal() {
    var items = $$('.reveal');
    if (!items.length) return;

    if (!('IntersectionObserver' in window) || prefersReducedMotion) {
      items.forEach(function (el) { el.classList.add('is-visible'); });
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    items.forEach(function (el) { io.observe(el); });
  }

  /* ---------------------------------------------------------- 移动端导航 */

  function initNav() {
    var toggle = $('#nav-toggle');
    var nav = $('#site-nav');
    if (!toggle || !nav) return;

    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.setAttribute('aria-label', open ? '收起导航' : '展开导航');
    });

    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ------------------------------------------------------------ 数字滚动 */

  function initCounters() {
    var els = $$('[data-count]');
    if (!els.length || prefersReducedMotion || !('IntersectionObserver' in window)) return;

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        io.unobserve(entry.target);
        var el = entry.target;
        var goal = parseInt(el.getAttribute('data-count'), 10) || 0;
        var start = performance.now();
        var dur = 900;
        (function tick(now) {
          var p = Math.min(1, (now - start) / dur);
          el.textContent = Math.round(goal * (1 - Math.pow(1 - p, 3)));
          if (p < 1) requestAnimationFrame(tick);
        })(start);
      });
    }, { threshold: 0.5 });

    els.forEach(function (el) { io.observe(el); });
  }

  /* ---------------------------------------------------------------- 启动 */

  function init() {
    var year = $('#year');
    if (year) year.textContent = new Date().getFullYear();

    renderThemes();
    initTabs();
    initCopy();
    initReveal();
    initNav();
    initCounters();

    loadLatest();
    loadSiteSettings();
    runDemoTyping();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // 保险：若渲染后下载区仍为空（例如网络异常），填入回退卡片
  window.addEventListener('load', function () {
    setTimeout(function () {
      var host = $('#downloads');
      if (host && !host.children.length) { applyVersionInfo(FALLBACK); renderDownloadError(); }
    }, 2500);
  });

})();
