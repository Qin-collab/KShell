/* ==========================================================================
   KShell 开发者社区页面逻辑
   · 从 /api/plugins 加载插件画廊并按标签筛选
   · 从 /api/site 读取站点信息
   · 目录高亮、示例选项卡、复制按钮、移动端导航
   无第三方依赖
   ========================================================================== */

(function () {
  'use strict';

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  var prefersReducedMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------------------------------------ 站点信息 */

  function loadSiteInfo() {
    if (!window.fetch) return;
    fetch('/api/site', { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (cfg) {
        if (!cfg) return;
        if (cfg.site && cfg.site.title) {
          $$('.brand-name, .footer-brand b').forEach(function (el) {
            el.textContent = cfg.site.title;
          });
        }
        if (cfg.site && cfg.site.tagline) {
          var fp = $('.footer-brand p');
          if (fp) fp.textContent = cfg.site.tagline;
        }
      })
      .catch(function () { /* 忽略 */ });
  }

  /* ------------------------------------------------------------ 插件画廊 */

  var allPlugins = [];
  var activeTag = '全部';

  function skeleton(n) {
    var html = '';
    for (var i = 0; i < n; i++) html += '<div class="plugin-skeleton"></div>';
    return html;
  }

  function renderGallery() {
    var grid = $('#plugin-grid');
    var note = $('#gallery-note');
    if (!grid) return;

    var list = activeTag === '全部'
      ? allPlugins
      : allPlugins.filter(function (p) { return (p.tags || []).indexOf(activeTag) !== -1; });

    if (!list.length) {
      grid.innerHTML = '<p class="plugin-empty">' +
        (allPlugins.length ? '该标签下暂无插件' : '社区插件正在征集中，欢迎提交你的插件') +
        '</p>';
      if (note) note.hidden = true;
      return;
    }

    grid.innerHTML = list.map(function (p) {
      var badges = '';
      if (p.official) badges += '<span class="pc-badge official">官方</span>';
      if (p.featured) badges += '<span class="pc-badge featured">推荐</span>';

      var cmds = (p.commands || []).map(function (c) {
        return '<code>' + esc(c) + '</code>';
      }).join('');

      var tags = (p.tags || []).map(function (t) {
        return '<span class="pc-tag">' + esc(t) + '</span>';
      }).join('');

      var link = p.repo || p.homepage || '';
      var linkHtml = link
        ? '<a class="pc-link" href="' + esc(link) + '" target="_blank" rel="noopener">查看源码 →</a>'
        : '';

      return '<article class="plugin-card' + (p.official ? ' is-official' : '') + '">' +
        '<div class="pc-head">' +
          '<span class="pc-name">' + esc(p.name) + '</span>' +
          '<span class="pc-version">v' + esc(p.version || '—') + '</span>' +
          badges +
        '</div>' +
        '<p class="pc-desc">' + esc(p.description) + '</p>' +
        '<p class="pc-meta">作者 ' + esc(p.author || '匿名') +
          (p.kshell ? ' · 需要 KShell ' + esc(p.kshell) : '') + '</p>' +
        (cmds ? '<div class="pc-cmds">' + cmds + '</div>' : '') +
        '<div class="pc-foot">' +
          '<div class="pc-tags">' + tags + '</div>' +
          linkHtml +
        '</div>' +
      '</article>';
    }).join('');

    if (note) note.hidden = true;
  }

  function renderFilter(tags) {
    var box = $('#gallery-filter');
    if (!box) return;
    var items = ['全部'].concat(tags);
    box.innerHTML = items.map(function (t) {
      return '<button class="gfilter' + (t === activeTag ? ' is-active' : '') +
        '" data-tag="' + esc(t) + '">' + esc(t) + '</button>';
    }).join('');

    box.addEventListener('click', function (e) {
      var btn = e.target.closest('.gfilter');
      if (!btn) return;
      activeTag = btn.getAttribute('data-tag');
      $$('.gfilter').forEach(function (b) {
        b.classList.toggle('is-active', b.getAttribute('data-tag') === activeTag);
      });
      renderGallery();
    });
  }

  function loadPlugins() {
    var grid = $('#plugin-grid');
    var note = $('#gallery-note');
    var stat = $('#stat-plugins');
    if (!grid) return;

    grid.innerHTML = skeleton(3);

    if (!window.fetch) {
      if (note) note.textContent = '当前浏览器不支持自动加载，请查看 GitHub 上的插件目录。';
      grid.innerHTML = '<p class="plugin-empty">无法自动加载插件列表</p>';
      return;
    }

    fetch('/api/plugins', { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status)); })
      .then(function (data) {
        allPlugins = data.plugins || [];
        if (stat) stat.textContent = allPlugins.length;
        renderFilter(data.tags || []);
        renderGallery();
      })
      .catch(function (err) {
        console.warn('加载插件列表失败:', err.message);
        if (note) note.textContent = '插件列表加载失败，可前往 GitHub 查看：';
        grid.innerHTML = '<p class="plugin-empty">' +
          '<a href="https://github.com/Qin-collab/KShell/tree/main/plugins" target="_blank" rel="noopener">' +
          '在 GitHub 上查看示例插件 →</a></p>';
      });
  }

  /* ------------------------------------------------------------ 示例选项卡 */

  function initExampleTabs() {
    var tabs = $$('.etab');
    if (!tabs.length) return;

    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var name = tab.getAttribute('data-example');
        tabs.forEach(function (t) { t.classList.toggle('is-active', t === tab); });
        $$('.example-panel').forEach(function (p) {
          p.classList.toggle('is-active', p.id === 'example-' + name);
        });
      });
    });
  }

  /* ------------------------------------------------------------ 目录高亮 */

  function initTocHighlight() {
    var links = $$('.doc-toc a');
    var sections = $$('.doc-section');
    if (!links.length || !sections.length || !('IntersectionObserver' in window)) return;

    var map = {};
    links.forEach(function (a) {
      var id = (a.getAttribute('href') || '').replace('#', '');
      if (id) map[id] = a;
    });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (a) { a.classList.remove('is-active'); });
        var link = map[entry.target.id];
        if (link) link.classList.add('is-active');
      });
    }, { rootMargin: '-88px 0px -70% 0px', threshold: 0 });

    sections.forEach(function (s) { io.observe(s); });
  }

  /* ------------------------------------------------------------ 复制按钮 */

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
          }, 1500);
        };

        if (navigator.clipboard && window.isSecureContext !== false) {
          navigator.clipboard.writeText(text).then(done).catch(fallback);
        } else {
          fallback();
        }

        function fallback() {
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

  /* ------------------------------------------------------------ 移动端导航 */

  function initNav() {
    var toggle = $('#nav-toggle');
    var nav = $('#site-nav');
    if (!toggle || !nav) return;

    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ------------------------------------------------------------ 平滑滚动 */

  function initSmoothScroll() {
    document.addEventListener('click', function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a) return;
      var id = a.getAttribute('href').slice(1);
      if (!id) return;
      var target = document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({
        behavior: prefersReducedMotion ? 'auto' : 'smooth',
        block: 'start',
      });
      history.replaceState(null, '', '#' + id);
    });
  }

  /* ------------------------------------------------------------ 启动 */

  function init() {
    var year = $('#year');
    if (year) year.textContent = new Date().getFullYear();

    window.addEventListener('error', function (e) {
      console.error(e.error || e.message);
    });

    initNav();
    initCopy();
    initExampleTabs();
    initTocHighlight();
    initSmoothScroll();
    loadSiteInfo();
    loadPlugins();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
