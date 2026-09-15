// Optional real-browser regression: node tests/test_review_navigation.mjs
// Uses only fictional data, a temporary browser profile, and localhost CDP.
import {spawn, execFileSync} from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'career-navigation-browser-'));
const html = path.join(temp, 'review.html');
execFileSync(process.env.PYTHON || 'python3', [path.join(root, 'tests/build_review_navigation_fixture.py'), html], {env: {...process.env, PYTHONDONTWRITEBYTECODE: '1'}});
const browser = process.env.CAREER_BROWSER || (process.platform === 'darwin' ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : 'chromium');
const child = spawn(browser, ['--headless', '--disable-gpu', '--disable-background-networking', '--no-first-run', '--disable-extensions', '--remote-debugging-port=0', '--user-data-dir=' + path.join(temp, 'profile'), 'about:blank'], {stdio: 'ignore'});
let socket, spawnError;
child.on('error', error => { spawnError = error; });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const results = [];
try {
    let port;
    for (let i = 0; i < 100; i++) {
        if (spawnError) throw spawnError;
        try { port = (await fs.readFile(path.join(temp, 'profile/DevToolsActivePort'), 'utf8')).split('\n')[0]; break; } catch (_) {}
        await delay(100);
    }
    assert.ok(port, 'Chrome must expose its temporary debugging endpoint');
    const version = await (await fetch('http://127.0.0.1:' + port + '/json/version')).json();
    socket = new WebSocket(version.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
    let id = 0; const pending = new Map();
    socket.onmessage = event => {
        const message = JSON.parse(event.data), task = pending.get(message.id);
        if (task) { pending.delete(message.id); message.error ? task.reject(Error(JSON.stringify(message.error))) : task.resolve(message.result); }
    };
    const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
        const next = ++id; pending.set(next, {resolve, reject}); socket.send(JSON.stringify({id: next, method, params, ...(sessionId ? {sessionId} : {})}));
    });
    const {targetId} = await send('Target.createTarget', {url: 'about:blank'});
    const {sessionId} = await send('Target.attachToTarget', {targetId, flatten: true});
    const cdp = (method, params = {}) => send(method, params, sessionId);
    await cdp('Page.enable'); await cdp('Runtime.enable');
    const errors = [];
    const originalMessage = socket.onmessage;
    socket.onmessage = event => { const message = JSON.parse(event.data); if (message.method === 'Runtime.exceptionThrown') errors.push(message.params); originalMessage(event); };
    const evaluate = async expression => {
        const result = await cdp('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
        if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
        return result.result.value;
    };
    const check = async (name, expression) => { assert.equal(await evaluate(expression), true, name); results.push(name); };
    const load = async () => { await cdp('Page.navigate', {url: pathToFileURL(html).href}); await delay(350); };
    await cdp('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false});
    await load();
    await check('All 80 pending questions appear, accepted records excluded', `queue.length === 80 && cards.filter(c => !c.hidden).length === 5 && !queue.some(c => c.dataset.key === 'field/name')`);
    await check('Overview and instructions start collapsed', `!document.getElementById('career-overview').parentElement.open && !document.getElementById('review-help').open`);
    await evaluate(`document.getElementById('start-review').click(); cards[0].querySelector('.action').value='accept';cards[0].dispatchEvent(new Event('input'));cards[1].querySelector('.action').value='later';cards[1].dispatchEvent(new Event('input'));`);
    await check('Answering preserves the current five and reports deferred separately', `cards.filter(c => !c.hidden).length === 5 && document.getElementById('progress').textContent === '1 answered · 1 deferred · 78 unanswered'`);
    await evaluate(`window.scrollTo(0, document.body.scrollHeight);document.getElementById('next').click();`);
    await check('Next focuses and scrolls to the first question, navigation remains visible', `page === 1 && document.activeElement === queue[5].querySelector('header') && queue[5].querySelector('header').getBoundingClientRect().top >= 0 && queue[5].querySelector('header').getBoundingClientRect().top < 40 && document.querySelector('.review-navigation').getBoundingClientRect().bottom <= innerHeight`);
    await evaluate(`batchJump.value='9';batchJump.dispatchEvent(new Event('change'));queue[45].querySelector('details').open=true;window.scrollBy(0, 260);rememberPlace();`);
    const position = await evaluate(`({y:scrollY, top:queue[45].getBoundingClientRect().top})`);
    await load();
    await check('Reload restores batch, expanded details and earlier answers', `page === 9 && queue[45].querySelector('details').open && cards[0].querySelector('.action').value === 'accept' && cards[1].querySelector('.action').value === 'later'`);
    assert.ok(Math.abs((await evaluate('scrollY')) - position.y) < 4, 'Reload restores exact scroll position'); results.push('Exact scroll position restored');
    await evaluate(`document.getElementById('previous').click()`);
    await check('Previous also focuses the beginning of its batch', `page === 8 && document.activeElement === queue[40].querySelector('header')`);
    await evaluate(`batchJump.value='15';batchJump.dispatchEvent(new Event('change'));`);
    await check('Final batch includes supporting fields, next is disabled', `page === 15 && !cards.find(c=>c.dataset.key==='field/purpose').hidden && document.getElementById('next').disabled`);
    await evaluate(`document.getElementById('unfinished').click()`);
    await check('Unfinished navigation wraps to deferred or unanswered work', `page === 0 && document.activeElement === cards[1].querySelector('header')`);
    await evaluate(`groupInput.value='employment';groupInput.dispatchEvent(new Event('input'));`);
    await check('Empty filters explain hidden pending work', `queue.length === 0 && !document.getElementById('empty-queue').hidden && document.getElementById('empty-queue').textContent.includes('80 records still need review')`);
    await evaluate(`document.querySelector('#empty-queue button').click();`);
    await check('Reset restores the full pending queue', `queue.length === 80 && page === 0`);
    await cdp('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 1, mobile: false});
    await evaluate(`document.getElementById('next').click();`); await delay(100);
    console.log('Mobile layout', await evaluate(`({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,bar:document.querySelector('.review-navigation').getBoundingClientRect().height,questionTop:queue[5].querySelector('header').getBoundingClientRect().top,overflow:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth).slice(0,5).map(e=>e.tagName+'#'+e.id)})`));
    await check('Narrow screen navigation fits, without horizontal overflow or hiding the question', `document.documentElement.scrollWidth <= innerWidth && document.querySelector('.review-navigation').getBoundingClientRect().height < innerHeight / 2 && queue[5].querySelector('header').getBoundingClientRect().top >= 0 && queue[5].querySelector('header').getBoundingClientRect().top < 40`);
    const screenshot = await cdp('Page.captureScreenshot', {format: 'png'});
    if (process.env.CAREER_REVIEW_SCREENSHOT) await fs.writeFile(process.env.CAREER_REVIEW_SCREENSHOT, Buffer.from(screenshot.data, 'base64'));
    await send('Browser.setDownloadBehavior', {behavior: 'allow', downloadPath: temp});
    await evaluate(`reviewer.value='Fictional Reviewer';reviewer.dispatchEvent(new Event('input'));document.getElementById('pause-nav').click();`);
    let downloaded;
    for (let i=0;i<30;i++) { try { downloaded = JSON.parse(await fs.readFile(path.join(temp, 'navigation-test-decisions.json'), 'utf8')); break; } catch (_) {} await delay(100); }
    assert.ok(downloaded, 'Pause downloads decisions');
    assert.deepEqual(Object.keys(downloaded).sort(), ['decisions','omissions','proposal_sha256','review_id','reviewed_by']);
    assert.equal(downloaded.decisions.length, 2); results.push('Pause retains the existing decisions contract, without navigation metadata or inferred approvals');
    await evaluate(`Storage.prototype.setItem = () => { throw Error('storage unavailable'); }; document.getElementById('next').click();`);
    await check('Unavailable storage is reported honestly and navigation remains usable', `page === 2 && document.getElementById('save-status').textContent.includes('Browser storage is unavailable')`);
    assert.equal(errors.length, 0, JSON.stringify(errors));
    console.log(results.map(name => 'PASS ' + name).join('\n'));
    console.log(`${results.length} browser navigation checks passed`);
} finally {
    if (socket) socket.close(); child.kill('SIGTERM'); await delay(500);
    await fs.rm(temp, {recursive: true, force: true, maxRetries: 5});
}
