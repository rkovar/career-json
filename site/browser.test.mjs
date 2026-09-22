// Optional real-browser check: npm run build --prefix site && node site/browser.test.mjs
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(root, 'dist/site');
const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'career-site-browser-'));
const mime = {'.html':'text/html','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml','.png':'image/png','.json':'application/json','.md':'text/plain'};
const server = http.createServer(async (request,response) => {
  try {
    const url = new URL(request.url, 'http://localhost');
    if (!url.pathname.startsWith('/career-json/')) { response.writeHead(404).end(); return; }
    let file = path.resolve(output, '.' + decodeURIComponent(url.pathname.slice('/career-json'.length)));
    if (file !== output && !file.startsWith(output + path.sep)) { response.writeHead(404).end(); return; }
    if ((await fs.stat(file)).isDirectory()) file = path.join(file, 'index.html');
    response.writeHead(200, {'Content-Type': mime[path.extname(file)] || 'text/plain'});
    response.end(await fs.readFile(file));
  } catch { response.writeHead(404).end(); }
});
const pause = ms => new Promise(resolve => setTimeout(resolve,ms));
let child,socket;
try {
  await new Promise((resolve,reject) => { server.once('error',reject); server.listen(0,'127.0.0.1',resolve); });
  const address = `http://127.0.0.1:${server.address().port}/career-json/`;
  child = spawn(process.env.CAREER_BROWSER || (process.platform === 'darwin' ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : 'chromium'),
    ['--headless','--disable-gpu','--disable-background-networking','--no-first-run','--disable-extensions','--remote-debugging-port=0','--user-data-dir=' + path.join(temp,'profile'),'about:blank'], {stdio:'ignore'});
  let spawnError;
  child.on('error',error => { spawnError = error; });
  let port;
  for (let i=0; i<100; i++) {
    if (spawnError) throw spawnError;
    try { port=(await fs.readFile(path.join(temp,'profile/DevToolsActivePort'),'utf8')).split('\n')[0]; break; } catch {}
    await pause(100);
  }
  assert.ok(port,'Chrome debugging endpoint available');
  const version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  socket = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((resolve,reject) => {socket.onopen=resolve;socket.onerror=reject;});
  const waiting = new Map(), errors=[]; let counter=0;
  socket.onmessage = event => {
    const message=JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params);
    if (message.method === 'Network.responseReceived' && message.params.response.status >= 400) errors.push(message.params.response.url);
    const pending=waiting.get(message.id);
    if (pending) { waiting.delete(message.id); message.error ? pending.reject(Error(JSON.stringify(message.error))) : pending.resolve(message.result); }
  };
  const send=(method,params={},sessionId) => new Promise((resolve,reject) => {
    const id=++counter; waiting.set(id,{resolve,reject}); socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));
  });
  const {targetId}=await send('Target.createTarget',{url:'about:blank'});
  const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});
  const cdp=(method,params={}) => send(method,params,sessionId);
  await cdp('Page.enable'); await cdp('Runtime.enable'); await cdp('Network.enable');
  const evaluate=async expression => {
    const result=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const load=async route => { await cdp('Page.navigate',{url:address+route}); await pause(250); };
  const screenshot=async name => {
    if (!process.env.CAREER_SITE_SCREENSHOTS) return;
    await fs.mkdir(process.env.CAREER_SITE_SCREENSHOTS,{recursive:true});
    const capture=await cdp('Page.captureScreenshot',{format:'png'});
    await fs.writeFile(path.join(process.env.CAREER_SITE_SCREENSHOTS,name+'.png'),Buffer.from(capture.data,'base64'));
  };
  for (const width of [1440,390]) {
    await cdp('Emulation.setDeviceMetricsOverride',{width,height:width===1440?1000:844,deviceScaleFactor:1,mobile:false});
    for (const route of ['', 'start/', 'demo/', 'guides/', 'guides/getting-started.html', 'guides/nontechnical-start.html', 'guides/files-and-exports.html', 'guides/resume-exports.html', 'privacy/', 'examples/first-pack/career.html']) {
      await load(route);
      assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true,`${width}px ${route}: no horizontal page overflow`);
    }
    await load('guides/nontechnical-start.html');
    assert.equal(await evaluate(`Array.from(document.querySelectorAll('main a')).find(a => a.textContent.includes('Get the career starter')).href`), address + 'start/index.html#download', 'Guide download stays within the current site and project subpath');
    await load('start/');
    assert.equal(await evaluate(`document.querySelector('[download]').getAttribute('href')`), '../downloads/career-json-starter.zip');
    assert.equal(await evaluate(`(async () => { const response = await fetch(document.querySelector('[download]').href); const bytes = new Uint8Array(await response.arrayBuffer()); return response.ok && bytes[0] === 80 && bytes[1] === 75; })()`), true, 'Starter link downloads a ZIP under a project subpath');
    await evaluate(`Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: async text => {window.copiedPrompt = text;}}}); document.querySelector('[data-copy="starter-prompt"]').click()`);
    assert.equal(await evaluate('window.copiedPrompt'), 'Help me start my career notebook.');
    assert.equal(await evaluate(`document.querySelector('#starter-prompt').closest('.terminal').querySelector('.copy-status').textContent.includes('Code tab')`), true);
    await evaluate(`navigator.clipboard.writeText = async () => {throw Error('clipboard unavailable')}; document.querySelector('[data-copy="starter-prompt"]').click()`);
    assert.equal(await evaluate(`document.querySelector('#starter-prompt').closest('.terminal').querySelector('.copy-status').textContent.includes('manually')`), true);
    await load('');
    assert.equal(await evaluate('document.querySelectorAll("[role=tab]").length'),3);
    await evaluate('document.getElementById("tab-leadership").click()');
    assert.equal(await evaluate('!document.getElementById("panel-leadership").hidden && document.getElementById("panel-engineering").hidden'),true);
    assert.equal(await evaluate('document.getElementById("panel-leadership").textContent.includes("Mara Vale")'),true,'Shared ownership survives audience selection');
    await evaluate('document.getElementById("tab-leadership").dispatchEvent(new KeyboardEvent("keydown",{key:"ArrowRight",bubbles:true}))');
    assert.equal(await evaluate('document.activeElement.id === "tab-architecture" && !document.getElementById("panel-architecture").hidden'),true,'Keyboard tabs follow the visible panel');
    await evaluate('document.getElementById("tab-engineering").click(); document.activeElement.blur(); scrollTo({top:0,behavior:"instant"})');
    await screenshot(width===1440?'home-desktop':'home-mobile');
    if (width===1440) {
      await evaluate('scrollTo(0,800)'); await pause(200); await screenshot('home-details');
      await load('start/'); await screenshot('start-desktop');
      await load('guides/getting-started.html'); await screenshot('guide-desktop');
      await load('guides/nontechnical-start.html'); await screenshot('beginner-guide-desktop');
    }
  }
  await cdp('Emulation.setScriptExecutionDisabled',{value:true});
  await load('');
  assert.equal(await evaluate('!document.getElementById("panel-engineering").hidden && document.querySelector("[data-tabs]").hidden'),true,'Default evidence stays readable without JavaScript');
  await load('start/');
  assert.equal(await evaluate(`document.getElementById('starter-prompt').textContent`), 'Help me start my career notebook.', 'Starter message remains copyable without JavaScript');
  await cdp('Page.navigate', {url: pathToFileURL(path.join(root, 'components/starter/START-HERE.html')).href});
  await pause(250);
  assert.equal(await evaluate(`document.getElementById('prompt').textContent`), 'Help me start my career notebook.', 'Downloaded instructions work as a local file without JavaScript');
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true, 'Local starter fits on mobile');
  assert.equal(errors.length,0,JSON.stringify(errors));
  console.log('PASS: desktop/mobile routes, project-subpath links, source ownership, keyboard tabs and no-JavaScript reading; no HTTP or JavaScript errors.');
} finally {
  if (socket) socket.close();
  if (child) child.kill('SIGTERM');
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  await pause(300);
  await fs.rm(temp,{recursive:true,force:true,maxRetries:5});
}
