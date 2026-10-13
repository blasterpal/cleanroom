import { chromium } from 'playwright-core';
import { lookup } from 'node:dns/promises';
import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

const [command = 'status', target, argument] = process.argv.slice(2);
const endpoint = new URL(process.env.BRAVE_CDP_URL || 'http://host.docker.internal:9222');
// Brave rejects non-IP Host headers; discovery also advertises a loopback WebSocket.
if (endpoint.hostname === 'host.docker.internal') endpoint.hostname = (await lookup(endpoint.hostname, { family: 4 })).address;
let ws = endpoint.href;
if (!['ws:', 'wss:'].includes(endpoint.protocol)) {
  const response = await fetch(new URL('/json/version', endpoint), { signal: AbortSignal.timeout(8000) });
  if (!response.ok) throw new Error(`CDP discovery failed: HTTP ${response.status}`);
  const discovery = await response.json();
  const url = new URL(discovery.webSocketDebuggerUrl);
  url.hostname = endpoint.hostname;
  url.port = endpoint.port;
  ws = url.href;
}
const browser = await chromium.connectOverCDP(ws, { timeout: 10000 });
try {
  const context = browser.contexts()[0];
  if (!context) throw new Error('No existing Brave context');
  const targetId = async page => {
    const session = await context.newCDPSession(page);
    try { return (await session.send('Target.getTargetInfo')).targetInfo.targetId; }
    finally { await session.detach(); }
  };
  const findPage = async id => {
    if (!id) throw new Error('Supply the target ID returned by open');
    for (const page of context.pages()) if (await targetId(page) === id) return page;
    throw new Error('Target not found');
  };
  let result;
  if (command === 'status') {
    result = { connected: true, browser: browser.version(), pages: context.pages().length };
  } else if (command === 'open') {
    if (!target) throw new Error('Supply a URL');
    const page = await context.newPage();
    try {
      await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 });
      result = { targetId: await targetId(page), url: page.url(), title: await page.title() };
    } catch (error) { await page.close(); throw error; }
  } else {
    const page = await findPage(target);
    if (command === 'inspect') result = { url: page.url(), title: await page.title(), text: (await page.locator('body').innerText()).slice(0, 20000) };
    else if (command === 'eval') {
      if (!argument) throw new Error('Supply JavaScript to evaluate');
      result = await page.evaluate(argument);
    } else if (command === 'screenshot') {
      if (!argument) throw new Error('Supply an output path');
      await mkdir(dirname(argument), { recursive: true });
      await page.screenshot({ path: argument, fullPage: true });
      result = { screenshot: argument };
    } else if (command === 'close') { await page.close(); result = { closed: target }; }
    else throw new Error('Use status, open, inspect, eval, screenshot, or close');
  }
  console.log(JSON.stringify(result ?? null, null, 2));
} finally {
  // Disconnect this automation client; leave Brave and all other tabs running.
  await browser.close();
}
