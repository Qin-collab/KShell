#!/usr/bin/env node
/**
 * 页面截图工具（开发工具）
 *
 * 用 CDP 做设备模拟并捕获整页截图，支持：
 *   · 真实手机宽度（无头 --window-size 有 ~500px 最小宽度限制）
 *   · 整页捕获（captureBeyondViewport）
 *   · 强制展开滚动动画元素，避免截图出现半透明/空白
 *
 * 用法:
 *   node tools/screenshot.js <输出路径> [url] [宽度] [高度] [起始Y] [裁剪高度]
 *   node tools/screenshot.js .shots/desktop.png http://127.0.0.1:3000/ 1440 900
 *   node tools/screenshot.js .shots/mobile.png  http://127.0.0.1:3000/ 390 844
 *   node tools/screenshot.js .shots/m2.png      http://127.0.0.1:3000/ 390 844 3800 3600
 *
 * 说明: 页面很长时整页截图会超过图片查看上限（8192px），
 *       可用「起始Y + 裁剪高度」分片截取。
 *
 * 依赖: 无（使用 Node 内置 WebSocket / fetch）
 */

'use strict';

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const OUT = process.argv[2] || '.shots/page.png';
const URL_TO_TEST = process.argv[3] || 'http://127.0.0.1:3000/';
const VW = Number(process.argv[4] || 1440);
const VH = Number(process.argv[5] || 900);
const CLIP_Y = process.argv[6] ? Number(process.argv[6]) : null;
const CLIP_H = process.argv[7] ? Number(process.argv[7]) : null;
/** 可选：管理后台密码（用于截图需登录的页面） */
const ADMIN_PASSWORD = process.argv[8] || process.env.KSH_ADMIN_PASSWORD || null;
const PORT = 9334;

const CHROME_CANDIDATES = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
];

function findBrowser() {
  for (const p of CHROME_CANDIDATES) {
    try { if (fs.existsSync(p)) return p; } catch (e) { /* 忽略 */ }
  }
  return null;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const browser = findBrowser();
  if (!browser) { console.error('未找到 Chrome/Edge'); process.exit(1); }

  // 每次运行使用独立的 profile，避免浏览器缓存旧的 JS/CSS 导致截图与代码不一致
  const userDataDir = path.join(__dirname, '..', '.shots', 'profiles', 'p' + Date.now() + '-' + process.pid);
  const child = spawn(browser, [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--hide-scrollbars',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ], { stdio: 'ignore' });

  let wsUrl = null;
  for (let i = 0; i < 40; i++) {
    await sleep(300);
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (res.ok) {
        const info = await res.json();
        wsUrl = info.webSocketDebuggerUrl;
        if (wsUrl) break;
      }
    } catch (e) { /* 还没起来 */ }
  }
  if (!wsUrl) { child.kill(); console.error('无法连接 DevTools'); process.exit(1); }

  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();

  const send = (method, params, sessionId) => new Promise((resolve, reject) => {
    const msgId = ++id;
    pending.set(msgId, { resolve, reject });
    ws.send(JSON.stringify({ id: msgId, method, params: params || {}, sessionId }));
  });

  await new Promise((r) => ws.addEventListener('open', r));
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    }
  });

  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });

  await send('Page.enable', {}, sessionId);
  await send('Runtime.enable', {}, sessionId);

  await send('Emulation.setDeviceMetricsOverride', {
    width: VW,
    height: VH,
    deviceScaleFactor: 1,
    mobile: VW < 768,
  }, sessionId);

  // 后台页面需要登录：先在源站执行登录请求写入会话 Cookie，再访问目标页
  if (ADMIN_PASSWORD) {
    const origin = new URL(URL_TO_TEST).origin;
    await send('Page.navigate', { url: origin + '/' }, sessionId);
    await sleep(1200);
    const login = await send('Runtime.evaluate', {
      expression: `fetch('/admin/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: ${JSON.stringify(ADMIN_PASSWORD)} })
      }).then(r => r.status + ' ' + JSON.stringify(r.ok)).catch(e => 'ERR ' + e.message)`,
      awaitPromise: true,
      returnByValue: true,
    }, sessionId);
    console.log('后台登录:', login.result.value);
  }

  await send('Page.navigate', { url: URL_TO_TEST }, sessionId);
  await sleep(4000); // 等待 API 请求与脚本执行完成

  // 展开所有滚动动画元素，确保整页截图内容完整
  await send('Runtime.evaluate', {
    expression: `document.querySelectorAll('.reveal').forEach(el => el.classList.add('is-visible'));
                 document.querySelectorAll('.cursor').forEach(el => el.style.visibility = 'visible');
                 'ok'`,
    returnByValue: true,
  }, sessionId);

  // 页面状态探针：用于确认关键区域是否渲染成功（便于发现静默失败）
  const probe = await send('Runtime.evaluate', {
    expression: `(() => {
      const len = (sel) => { const el = document.querySelector(sel); return el ? el.innerHTML.length : 0; };
      const lv = document.querySelector('#login-view');
      return JSON.stringify({
        title: document.title,
        releaseKv: len('#release-kv'),
        serverKv: len('#server-kv'),
        chart: len('#mini-chart'),
        downloads: document.querySelectorAll('#downloads .dl-card').length,
        announcement: len('#announcement'),
        alert: (document.querySelector('#alert') || {}).textContent || '',
        loginVisible: lv ? !lv.hidden : null
      });
    })()`,
    returnByValue: true,
  }, sessionId);
  console.log('页面探针:', probe.result.value);
  await sleep(900);

  const shotParams = { format: 'png', captureBeyondViewport: true };
  if (CLIP_Y !== null) {
    shotParams.clip = {
      x: 0,
      y: CLIP_Y,
      width: VW,
      height: CLIP_H || VH,
      scale: 1,
    };
  }

  const shot = await send('Page.captureScreenshot', shotParams, sessionId);

  const outPath = path.resolve(__dirname, '..', OUT);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, Buffer.from(shot.data, 'base64'));
  console.log(`已保存: ${outPath} (${VW}px 视口, 整页)`);

  ws.close();
  child.kill();
}

main().catch((err) => {
  console.error('截图失败:', err.message);
  process.exit(1);
});
