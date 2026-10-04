/* ==========================================================================
   KShell 管理后台前端逻辑
   无第三方依赖 · 所有写操作携带 CSRF 令牌
   ========================================================================== */

(function () {
  'use strict';

  var state = {
    csrf: null,
    username: null,
    view: 'overview',
    settings: null,
    release: null,
  };

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function fmtNum(n) {
    return Number(n || 0).toLocaleString('zh-CN');
  }

  function fmtDuration(sec) {
    sec = Number(sec || 0);
    var d = Math.floor(sec / 86400);
    var h = Math.floor((sec % 86400) / 3600);
    var m = Math.floor((sec % 3600) / 60);
    if (d > 0) return d + ' 天 ' + h + ' 小时';
    if (h > 0) return h + ' 小时 ' + m + ' 分';
    return m + ' 分';
  }

  function fmtTime(ts) {
    if (!ts) return '—';
    var d = new Date(ts);
    if (isNaN(d.getTime())) return '—';
    var p = function (n) { return n < 10 ? '0' + n : String(n); };
    return p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    var p = function (n) { return n < 10 ? '0' + n : String(n); };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }

  /**
   * 生成 <dl class="kv"> 的内容
   * @param {Array} rows [label, value, rawHtml?] 数组
   *   rawHtml 为 true 时 value 按 HTML 渲染（默认转义，防 XSS）
   */
  function kv(rows) {
    return rows.map(function (row) {
      var label = row[0];
      var value = row[1];
      var raw = row[2];
      return '<dt>' + esc(label) + '</dt><dd>' +
        (raw ? String(value == null ? '' : value) : esc(value)) +
        '</dd>';
    }).join('');
  }

  /* ------------------------------------------------------------ 请求封装 */

  function api(method, url, body) {
    var opts = {
      method: method,
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    if (method !== 'GET' && state.csrf) {
      opts.headers['X-CSRF-Token'] = state.csrf;
    }
    return fetch(url, opts).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          var err = new Error(data.error || ('请求失败 (HTTP ' + res.status + ')'));
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }

  var alertTimer = null;
  function showAlert(message, kind) {
    var el = $('#alert');
    if (!el) return;
    el.textContent = message;
    el.className = 'alert is-' + (kind || 'info');
    el.hidden = false;
    if (alertTimer) clearTimeout(alertTimer);
    alertTimer = setTimeout(function () { el.hidden = true; }, 4200);
  }

  /* -------------------------------------------------------------- 登录 */

  function showLogin() {
    $('#login-view').hidden = false;
    $('#app-view').hidden = true;
    var pwd = $('#login-password');
    if (pwd) { pwd.value = ''; pwd.focus(); }
  }

  function showApp(session) {
    state.csrf = session.csrf;
    state.username = session.username;
    $('#login-view').hidden = true;
    $('#app-view').hidden = false;
    $('#who').textContent = session.username + ' · 会话至 ' + fmtTime(session.expiresAt);

    var view = initialView();
    switchView(view, true);
    if (view === 'overview') loadOverview();
  }

  function initLogin() {
    $('#login-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = $('#login-submit');
      var errEl = $('#login-error');
      var pwd = $('#login-password').value;

      errEl.hidden = true;
      btn.disabled = true;
      btn.textContent = '登录中…';

      api('POST', '/admin/api/login', { password: pwd })
        .then(function (data) {
          btn.disabled = false;
          btn.textContent = '登录';
          showApp(data);
        })
        .catch(function (err) {
          btn.disabled = false;
          btn.textContent = '登录';
          errEl.textContent = err.message;
          errEl.hidden = false;
          $('#login-password').select();
        });
    });
  }

  function initLogout() {
    $('#logout-btn').addEventListener('click', function () {
      api('POST', '/admin/api/logout').finally(function () {
        state.csrf = null;
        showLogin();
      });
    });
  }

  /* ------------------------------------------------------------ 视图切换 */

  var VIEW_TITLES = {
    overview: '概览',
    traffic: '访问统计',
    release: '版本发布',
    community: '插件社区',
    settings: '站点设置',
    logs: '请求日志',
    security: '安全设置',
  };

  function switchView(name, skipHash) {
    if (!VIEW_TITLES[name]) name = 'overview';
    state.view = name;
    $$('.nav-item').forEach(function (btn) {
      btn.classList.toggle('is-active', btn.getAttribute('data-view') === name);
    });
    $$('.view').forEach(function (v) {
      v.classList.toggle('is-active', v.id === 'view-' + name);
    });
    $('#view-title').textContent = VIEW_TITLES[name] || name;

    // 同步到地址栏，便于刷新/分享时保持当前视图
    if (!skipHash && location.hash !== '#' + name) {
      history.replaceState(null, '', '#' + name);
    }

    if (name === 'traffic') loadTraffic();
    if (name === 'release') loadRelease();
    if (name === 'community') loadRegistry();
    if (name === 'settings') loadSettings();
    if (name === 'logs') loadLogs();
    if (name === 'security') loadSecurity();
  }

  function initNav() {
    $$('.nav-item').forEach(function (btn) {
      btn.addEventListener('click', function () { switchView(btn.getAttribute('data-view')); });
    });
    window.addEventListener('hashchange', function () {
      switchView((location.hash || '').replace('#', ''), true);
    });
  }

  function initialView() {
    return (location.hash || '').replace('#', '') || 'overview';
  }

  /* -------------------------------------------------------------- 图表 */

  function renderChart(container, series, opts) {
    if (!container) return;
    opts = opts || {};
    var keys = opts.keys || ['visits'];
    var max = 0;
    series.forEach(function (d) {
      keys.forEach(function (k) { max = Math.max(max, d[k] || 0); });
    });
    if (max === 0) max = 1;

    var showLabelEvery = Math.ceil(series.length / 8);
    var cls = { visits: 'v', downloads: 'd', apiCalls: 'a' };
    var names = { visits: '访问', downloads: '下载', apiCalls: 'API' };

    // 计算哪些下标显示日期，避免末尾标签与上一个标签重叠
    var labelIdx = {};
    for (var li = 0; li < series.length; li += showLabelEvery) labelIdx[li] = true;
    var lastIdx = series.length - 1;
    if (!labelIdx[lastIdx] && lastIdx >= 0) {
      var prevIdx = lastIdx - (lastIdx % showLabelEvery);
      if (lastIdx - prevIdx < 2) delete labelIdx[prevIdx];
      labelIdx[lastIdx] = true;
    }

    container.innerHTML = series.map(function (d, i) {
      var bars = keys.map(function (k) {
        var val = d[k] || 0;
        var pct = (val / max) * 100;
        var style = val > 0 ? 'height:max(2px,' + pct.toFixed(2) + '%)' : 'height:0';
        return '<i class="' + (cls[k] || 'v') + '" style="' + style + '" title="' +
          d.date + ' ' + names[k] + ': ' + val + '"></i>';
      }).join('');

      return '<div class="bar">' + bars + (labelIdx[i] ? '<span>' + d.date.slice(5) + '</span>' : '') + '</div>';
    }).join('');
  }

  /* -------------------------------------------------------------- 排行 */

  function renderRank(container, items, emptyText) {
    if (!container) return;
    if (!items || !items.length) {
      container.innerHTML = '<li class="empty">' + esc(emptyText || '暂无数据') + '</li>';
      return;
    }
    var max = items[0].count || 1;
    container.innerHTML = items.map(function (it) {
      var pct = Math.max(4, Math.round((it.count / max) * 100));
      return '<li>' +
        '<span class="r-name" title="' + esc(it.key) + '">' + esc(it.key) + '</span>' +
        '<span class="r-bar"><i style="width:' + pct + '%"></i></span>' +
        '<span class="r-count">' + fmtNum(it.count) + '</span>' +
        '</li>';
    }).join('');
  }

  /* -------------------------------------------------------------- 概览 */

  function loadOverview() {
    return api('GET', '/admin/api/overview').then(function (data) {
      var s = data.stats, t = s.totals;

      $('#s-today').textContent = fmtNum(s.today.visits);
      $('#s-today-sub').textContent = '页面浏览 ' + fmtNum(s.today.apiCalls >= 0 ? s.today.visits : 0) + ' 次';

      $('#s-visits').textContent = fmtNum(t.visits);
      $('#s-pageviews').textContent = '页面浏览 ' + fmtNum(t.pageViews);

      $('#s-downloads').textContent = fmtNum(t.downloads);
      var kindKeys = Object.keys(s.byKind || {});
      $('#s-downloads-sub').textContent = kindKeys.length
        ? kindKeys.map(function (k) { return k + ' ' + s.byKind[k]; }).join(' · ')
        : '暂无下载点击';

      $('#s-api').textContent = fmtNum(t.apiCalls);
      $('#s-uptime').textContent = '运行 ' + fmtDuration(data.server.uptimeSeconds);

      // 发布信息
      state.release = data.release;
      $('#release-kv').innerHTML = kv([
        ['版本', data.release.tag],
        ['数据来源', data.release.source === 'github-api' ? 'GitHub API（实时）' : '回退数据'],
        ['发布日期', fmtDate(data.release.publishedAt)],
        ['资产数量', (data.release.assets || []).length + ' 个'],
        ['缓存', data.cache.cached ? ('已缓存 ' + data.cache.ageSeconds + ' 秒（TTL ' + data.cache.ttlSeconds + ' 秒）') : '未缓存'],
      ]);

      // 运行状态
      $('#server-kv').innerHTML = kv([
        ['Node 版本', data.server.node],
        ['运行平台', data.server.platform],
        ['内存占用', data.server.memoryMB + ' MB'],
        ['进程 PID', data.server.pid],
        ['启动时间', fmtTime(data.server.startedAt)],
        ['活跃会话', data.auth.sessions + ' 个'],
        ['累计登录', fmtNum(data.auth.loginCount)],
        ['最近登录', fmtTime(data.auth.lastLoginAt) + (data.auth.lastLoginIp ? ' · ' + data.auth.lastLoginIp : '')],
      ]);

      renderChart($('#mini-chart'), s.last7Days, { keys: ['visits', 'downloads'] });

      // 迷你图用 14 天数据（overview 只返回 7 天）
      api('GET', '/admin/api/stats?days=14').then(function (d) {
        renderChart($('#mini-chart'), d.series, { keys: ['visits', 'downloads'] });
      }).catch(function () { /* 图表失败不影响其他内容 */ });
    }).catch(handleApiError);
  }

  /* -------------------------------------------------------- 访问统计 */

  function loadTraffic() {
    var days = Number($('#days-select').value) || 30;
    return api('GET', '/admin/api/stats?days=' + days).then(function (data) {
      renderChart($('#main-chart'), data.series, { keys: ['visits', 'downloads', 'apiCalls'] });

      var o = data.overview;
      renderRank($('#rank-paths'), o.topPaths, '暂无访问记录');
      renderRank($('#rank-refs'), o.topReferers, '暂无来源记录');
      renderRank($('#rank-ua'), o.topUA, '暂无客户端记录');

      var kinds = Object.keys(o.byKind || {}).map(function (k) { return { key: k, count: o.byKind[k] }; })
        .sort(function (a, b) { return b.count - a.count; });
      renderRank($('#rank-kinds'), kinds, '暂无下载点击');
    }).catch(handleApiError);
  }

  /* -------------------------------------------------------- 版本发布 */

  function loadRelease() {
    return api('GET', '/admin/api/overview').then(function (data) {
      var r = data.release, c = data.cache;

      $('#release-detail').innerHTML = kv([
        ['标签', r.tag],
        ['版本号', r.version],
        ['名称', r.name || r.tag],
        ['发布时间', fmtDate(r.publishedAt)],
        ['数据来源', r.source],
        ['Release 页面', '<a href="' + esc(r.releaseUrl) + '" target="_blank" rel="noopener">' + esc(r.releaseUrl) + '</a>', true],
      ]);

      var tbody = $('#assets-table tbody');
      if (!r.assets || !r.assets.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">该版本没有发布资产</td></tr>';
      } else {
        tbody.innerHTML = r.assets.map(function (a) {
          return '<tr>' +
            '<td><span class="tag">' + esc(a.kind) + '</span></td>' +
            '<td>' + esc(a.name) + '</td>' +
            '<td>' + esc(a.sizeText || '—') + '</td>' +
            '<td>' + fmtNum(a.downloadCount) + '</td>' +
            '<td><a href="' + esc(a.url) + '" target="_blank" rel="noopener">下载</a></td>' +
            '</tr>';
        }).join('');
      }

      $('#cache-kv').innerHTML = kv([
        ['缓存状态', c.cached ? '已缓存' : '未缓存'],
        ['缓存时间', c.fetchedAt ? fmtTime(c.fetchedAt) : '—'],
        ['缓存时长', c.ttlSeconds + ' 秒'],
        ['数据标签', c.tag || '—'],
        ['数据来源', c.source || '—'],
      ]);
    }).catch(handleApiError);
  }

  function refreshRelease(btn) {
    btn.disabled = true;
    var old = btn.textContent;
    btn.textContent = '刷新中…';
    api('POST', '/admin/api/release/refresh')
      .then(function (data) {
        showAlert('Release 缓存已刷新：' + data.tag + '（' + data.source + '）', 'ok');
        loadRelease();
        loadOverview();
      })
      .catch(handleApiError)
      .finally(function () { btn.disabled = false; btn.textContent = old; });
  }

  /* -------------------------------------------------------- 站点设置 */

  function loadSettings() {
    return api('GET', '/admin/api/settings').then(function (data) {
      state.settings = data.settings;
      fillSettingsForm(data.settings);
    }).catch(handleApiError);
  }

  function fillSettingsForm(s) {
    $$('[data-key]').forEach(function (el) {
      var key = el.getAttribute('data-key');
      var value = key.split('.').reduce(function (o, k) { return (o == null ? undefined : o[k]); }, s);
      if (el.type === 'checkbox') el.checked = !!value;
      else el.value = value == null ? '' : value;
    });
  }

  function collectSettingsForm() {
    var patch = {};
    $$('[data-key]').forEach(function (el) {
      var key = el.getAttribute('data-key');
      if (el.type === 'checkbox') patch[key] = el.checked;
      else if (el.type === 'number') patch[key] = Number(el.value);
      else patch[key] = el.value;
    });
    return patch;
  }

  function initSettings() {
    $('#settings-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = $('#save-settings');
      btn.disabled = true;
      btn.textContent = '保存中…';

      api('PUT', '/admin/api/settings', { patch: collectSettingsForm() })
        .then(function (data) {
          state.settings = data.settings;
          fillSettingsForm(data.settings);
          var msg = '设置已保存';
          if (data.rejected && data.rejected.length) {
            msg += '；被拒绝：' + data.rejected.map(function (r) { return r.key + '（' + r.reason + '）'; }).join(', ');
          }
          showAlert(msg, data.rejected && data.rejected.length ? 'info' : 'ok');
        })
        .catch(handleApiError)
        .finally(function () { btn.disabled = false; btn.textContent = '保存设置'; });
    });

    $('#reload-settings').addEventListener('click', function () {
      if (state.settings) {
        fillSettingsForm(state.settings);
        showAlert('已放弃未保存的修改', 'info');
      }
    });

    $('#reset-settings').addEventListener('click', function () {
      if (!confirm('确定要把所有站点设置恢复为默认值吗？')) return;
      api('POST', '/admin/api/settings/reset')
        .then(function (data) {
          state.settings = data.settings;
          fillSettingsForm(data.settings);
          showAlert('已恢复默认设置', 'ok');
        })
        .catch(handleApiError);
    });
  }

  /* -------------------------------------------------------------- 日志 */

  function loadLogs() {
    return api('GET', '/admin/api/logs?limit=150').then(function (data) {
      var tbody = $('#logs-table tbody');
      if (!data.logs.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">暂无日志</td></tr>';
        return;
      }
      tbody.innerHTML = data.logs.map(function (l) {
        var cls = 'status-' + String(l.status).charAt(0) + 'xx';
        return '<tr>' +
          '<td>' + fmtTime(l.t) + '</td>' +
          '<td>' + esc(l.ip) + '</td>' +
          '<td>' + esc(l.method) + '</td>' +
          '<td title="' + esc(l.ua) + '">' + esc(l.path) + '</td>' +
          '<td class="' + cls + '">' + l.status + '</td>' +
          '<td>' + l.ms + ' ms</td>' +
          '</tr>';
      }).join('');
    }).catch(handleApiError);
  }

  function initLogs() {
    $('#reload-logs').addEventListener('click', loadLogs);
    $('#clear-logs').addEventListener('click', function () {
      if (!confirm('确定清空全部请求日志吗？')) return;
      api('DELETE', '/admin/api/logs')
        .then(function () { showAlert('日志已清空', 'ok'); loadLogs(); })
        .catch(handleApiError);
    });
  }

  /* -------------------------------------------------------------- 安全 */

  function loadSecurity() {
    return api('GET', '/admin/api/session').then(function (s) {
      $('#auth-kv').innerHTML = kv([
        ['用户名', s.username],
        ['会话过期', fmtTime(s.expiresAt)],
        ['会话时长', Math.round((s.sessionTtlSeconds || 0) / 3600) + ' 小时'],
        ['累计登录', fmtNum(s.loginCount)],
        ['最近登录', fmtTime(s.lastLoginAt)],
        ['最近登录 IP', s.lastLoginIp || '—'],
      ]);
    }).catch(handleApiError);
  }

  function initSecurity() {
    $('#password-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var current = $('#pwd-current').value;
      var next = $('#pwd-next').value;
      var confirmPwd = $('#pwd-confirm').value;

      if (next !== confirmPwd) return showAlert('两次输入的新密码不一致', 'err');
      if (next.length < 8) return showAlert('新密码至少 8 位', 'err');

      api('POST', '/admin/api/password', { current: current, next: next })
        .then(function (data) {
          showAlert(data.message || '密码已更新，请重新登录', 'ok');
          state.csrf = null;
          setTimeout(showLogin, 1500);
        })
        .catch(handleApiError);
    });
  }

  /* -------------------------------------------------------- 插件社区 */

  var registry = { plugins: [], stats: {}, updatedAt: null };

  function loadRegistry() {
    return api('GET', '/admin/api/registry').then(function (data) {
      registry.plugins = data.plugins || [];
      registry.stats = data.stats || {};
      registry.updatedAt = data.updatedAt;
      renderRegistry();
    }).catch(handleApiError);
  }

  function renderRegistry() {
    var s = registry.stats;
    $('#registry-kv').innerHTML = kv([
      ['条目总数', (s.total || 0) + ' 个'],
      ['已发布', (s.published || 0) + ' 个'],
      ['官方插件', (s.official || 0) + ' 个'],
      ['推荐位', (s.featured || 0) + ' 个'],
      ['标签', (s.tags || []).join(' · ') || '—'],
      ['最后更新', registry.updatedAt ? fmtTime(registry.updatedAt) : '—'],
    ]);

    var tbody = $('#registry-table tbody');
    if (!registry.plugins.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">还没有插件条目，点击右上角「新增插件」添加</td></tr>';
      return;
    }

    tbody.innerHTML = registry.plugins.map(function (p) {
      var state = [];
      if (p.published === false) state.push('<span class="tag">未发布</span>');
      else state.push('<span class="tag">已发布</span>');
      if (p.official) state.push('<span class="tag">官方</span>');
      if (p.featured) state.push('<span class="tag">推荐</span>');

      return '<tr>' +
        '<td><b>' + esc(p.name) + '</b></td>' +
        '<td>' + esc(p.version || '—') + '</td>' +
        '<td>' + esc(p.author || '—') + '</td>' +
        '<td>' + esc((p.commands || []).join(', ') || '—') + '</td>' +
        '<td>' + esc((p.tags || []).join(', ') || '—') + '</td>' +
        '<td>' + state.join(' ') + '</td>' +
        '<td>' +
          '<button class="link-btn" data-edit="' + esc(p.id) + '">编辑</button> ' +
          '<button class="link-btn" data-del="' + esc(p.id) + '">删除</button>' +
        '</td>' +
      '</tr>';
    }).join('');

    $$('#registry-table tbody [data-edit]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var entry = registry.plugins.find(function (p) { return p.id === btn.getAttribute('data-edit'); });
        if (entry) showRegistryForm(entry);
      });
    });

    $$('#registry-table tbody [data-del]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-del');
        if (!confirm('确定删除插件条目 ' + id + ' 吗？')) return;
        api('DELETE', '/admin/api/registry?id=' + encodeURIComponent(id))
          .then(function (data) {
            registry.plugins = data.plugins || [];
            registry.stats = data.stats || {};
            renderRegistry();
            showAlert('已删除 ' + id, 'ok');
          })
          .catch(handleApiError);
      });
    });
  }

  function showRegistryForm(entry) {
    var form = $('#registry-form');
    form.hidden = false;
    $('#registry-form-title').textContent = entry ? ('编辑插件: ' + entry.name) : '新增插件';
    $('#registry-id').value = entry ? entry.id : '';
    $('#reg-name').value = entry ? (entry.name || '') : '';
    $('#reg-version').value = entry ? (entry.version || '') : '1.0.0';
    $('#reg-author').value = entry ? (entry.author || '') : '';
    $('#reg-kshell').value = entry ? (entry.kshell || '') : '>=2.1.0';
    $('#reg-description').value = entry ? (entry.description || '') : '';
    $('#reg-repo').value = entry ? (entry.repo || '') : '';
    $('#reg-commands').value = entry ? (entry.commands || []).join(', ') : '';
    $('#reg-tags').value = entry ? (entry.tags || []).join(', ') : '';
    $('#reg-published').checked = entry ? entry.published !== false : true;
    $('#reg-featured').checked = entry ? !!entry.featured : false;
    $('#reg-official').checked = entry ? !!entry.official : false;
    form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    $('#reg-name').focus();
  }

  function hideRegistryForm() {
    $('#registry-form').hidden = true;
    $('#registry-id').value = '';
  }

  function collectRegistryForm() {
    return {
      name: $('#reg-name').value.trim(),
      version: $('#reg-version').value.trim(),
      author: $('#reg-author').value.trim(),
      kshell: $('#reg-kshell').value.trim(),
      description: $('#reg-description').value.trim(),
      repo: $('#reg-repo').value.trim(),
      commands: $('#reg-commands').value,
      tags: $('#reg-tags').value,
      published: $('#reg-published').checked,
      featured: $('#reg-featured').checked,
      official: $('#reg-official').checked,
    };
  }

  function initRegistry() {
    $('#registry-add-toggle').addEventListener('click', function () {
      var form = $('#registry-form');
      if (form.hidden) showRegistryForm(null);
      else hideRegistryForm();
    });

    $('#registry-cancel').addEventListener('click', hideRegistryForm);

    $('#registry-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var id = $('#registry-id').value;
      var payload = collectRegistryForm();
      if (!payload.name) return showAlert('插件名不能为空', 'err');

      var btn = $('#registry-save');
      btn.disabled = true;
      btn.textContent = '保存中…';

      var req = id
        ? api('PUT', '/admin/api/registry', { id: id, patch: payload })
        : api('POST', '/admin/api/registry', payload);

      req.then(function (data) {
        registry.plugins = data.plugins || [];
        registry.stats = data.stats || {};
        renderRegistry();
        hideRegistryForm();
        showAlert(id ? '已更新插件条目' : '已新增插件条目', 'ok');
      }).catch(handleApiError).finally(function () {
        btn.disabled = false;
        btn.textContent = '保存';
      });
    });

    $('#registry-reseed').addEventListener('click', function () {
      api('POST', '/admin/api/registry/reseed')
        .then(function (data) {
          registry.plugins = data.plugins || [];
          registry.stats = data.stats || {};
          renderRegistry();
          showAlert(data.added > 0 ? ('已补回 ' + data.added + ' 个官方示例') : '官方示例已齐全', 'ok');
        })
        .catch(handleApiError);
    });
  }

  /* ---------------------------------------------------------- 其他交互 */

  function initMisc() {
    $('#refresh-btn').addEventListener('click', function () {
      var map = {
        overview: loadOverview,
        traffic: loadTraffic,
        release: loadRelease,
        community: loadRegistry,
        settings: loadSettings,
        logs: loadLogs,
        security: loadSecurity,
      };
      var fn = map[state.view];
      if (fn) fn().then(function () { showAlert('数据已刷新', 'ok'); });
    });

    $('#refresh-release').addEventListener('click', function () { refreshRelease(this); });
    $('#refresh-release-2').addEventListener('click', function () { refreshRelease(this); });

    $('#days-select').addEventListener('change', loadTraffic);

    $('#reset-stats').addEventListener('click', function () {
      if (!confirm('确定重置全部统计数据吗？此操作不可恢复。')) return;
      api('POST', '/admin/api/stats/reset')
        .then(function () {
          showAlert('统计数据已重置', 'ok');
          loadTraffic();
        })
        .catch(handleApiError);
    });
  }

  function handleApiError(err) {
    if (err && err.status === 401) {
      showLogin();
      var e = $('#login-error');
      if (e) { e.textContent = '会话已过期，请重新登录'; e.hidden = false; }
      return;
    }
    showAlert(err.message || '请求失败', 'err');
  }

  /* ------------------------------------------------------------ 初始化 */

  function init() {
    // 把未捕获的前端异常显示出来，避免静默失败导致面板空白
    window.addEventListener('error', function (e) {
      console.error(e.error || e.message);
      showAlert('前端脚本错误：' + (e.message || '未知错误'), 'err');
    });
    window.addEventListener('unhandledrejection', function (e) {
      var msg = (e.reason && e.reason.message) || '未知错误';
      console.error(e.reason);
      showAlert('请求出错：' + msg, 'err');
    });

    initLogin();
    initLogout();
    initNav();
    initRegistry();
    initSettings();
    initLogs();
    initSecurity();
    initMisc();

    api('GET', '/admin/api/session')
      .then(function (s) {
        if (s.authenticated) showApp(s);
        else showLogin();
      })
      .catch(function () { showLogin(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
