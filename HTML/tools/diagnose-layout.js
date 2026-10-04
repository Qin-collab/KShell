#!/usr/bin/env node
/**
 * 布局诊断脚本（开发工具）
 *
 * 用 Chrome DevTools Protocol 打开页面，测量真实视口宽度并找出
 * 所有横向溢出（right 超出视口）的元素，用于排查响应式布局问题。
 *
 * 用法: node tools/diagnose-layout.js [url] [viewportWidth] [viewportHeight]
 * 依赖: 无（使用 Node 内置 WebSocket 与 fetch）
 */

'use strict';

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const URL_TO_TEST = process.argv[2] || 'http://127.0.0.1:3000/';
const VW = Number(process.argv[3] || 414);
const VH = Number(process.argv[4] || 900);
const PORT = 9333;

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
  if (!browser) {
    console.error('未找到 Chrome/Edge');
    process.exit(1);
  }

  const userDataDir = path.join(__dirname, '..', '.shots', 'cdp-profile');
  const child = spawn(browser, [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--hide-scrollbars',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${userDataDir}`,
    `--window-size=${VW},${VH}`,
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

  if (!wsUrl) {
    child.kill();
    console.error('无法连接 DevTools');
    process.exit(1);
  }

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

  // 新建页面并启用所需域
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });

  await send('Page.enable', {}, sessionId);

  // 关键：用 Emulation 覆盖设备指标才能模拟真实手机宽度
  // （无头模式的 --window-size 有最小宽度限制，约 500px）
  await send('Emulation.setDeviceMetricsOverride', {
    width: VW,
    height: VH,
    deviceScaleFactor: 1,
    mobile: VW < 768,
  }, sessionId);

  await send('Page.navigate', { url: URL_TO_TEST }, sessionId);
  await sleep(3500); // 等待脚本执行与 API 请求

  const expression = `(() => {
    const vw = window.innerWidth;
    const out = [];
    document.querySelectorAll('*').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.width > vw + 1 || r.right > vw + 1) {
        out.push({
          tag: el.tagName.toLowerCase(),
          cls: String(el.className || '').slice(0, 46),
          id: el.id || '',
          width: Math.round(r.width),
          right: Math.round(r.right),
          text: (el.textContent || '').trim().slice(0, 28)
        });
      }
    });
    out.sort((a, b) => b.right - a.right);
    return JSON.stringify({
      innerWidth: vw,
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      overflowCount: out.length,
      worst: out.slice(0, 14)
    }, null, 2);
  })()`;

  const result = await send('Runtime.evaluate', { expression, returnByValue: true }, sessionId);
  console.log(result.result.value);

  ws.close();
  child.kill();
}

main().catch((err) => {
  console.error('诊断失败:', err.message);
  process.exit(1);
});
