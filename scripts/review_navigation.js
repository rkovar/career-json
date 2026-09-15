'use strict';
// Browser draft/navigation state is separate from the person-sourced decisions contract.
const data = JSON.parse(document.getElementById('review-data').textContent);
const cards = [...document.querySelectorAll('.card')];
const byKey = new Map(data.items.map(row => [row.key, row]));
const storageKey = 'career-review:' + data.review_id + ':' + data.proposal_sha256 + ':' + data.ledger_sha256;
const navigationKey = storageKey + ':navigation:v1';
const batchSize = 5;
let page = 0, connectedKeys = null, queue = [], restoring = true, scrollTimer;
const status = document.getElementById('save-status'), reviewer = document.getElementById('reviewer');
const groupInput = document.getElementById('group'), changeInput = document.getElementById('change');
const searchInput = document.getElementById('search'), batchJump = document.getElementById('batch-jump');
function collect(){return {review_id:data.review_id,proposal_sha256:data.proposal_sha256,reviewed_by:reviewer.value.trim(),decisions:cards.filter(c=>c.querySelector('.action').value||c.querySelector('.reassess')?.checked||c.querySelector('.note').value.trim()||(c.querySelector('.publication')&&c.querySelector('.publication').value!=='unchanged')).map(c=>({key:c.dataset.key,fingerprint:byKey.get(c.dataset.key).fingerprint,action:c.querySelector('.action').value||'later',publication:c.querySelector('.publication')?.value||'unchanged',note:c.querySelector('.note').value,...(c.querySelector('.reassess')?.checked?{reassessment:{status:byKey.get(c.dataset.key).evidence_status,reason:c.querySelector('.reassessment-reason').value,source_refs:byKey.get(c.dataset.key).source_refs.map(r=>({source_id:r.source_id,excerpt:r.excerpt||''}))}}:{})})),omissions:[...document.querySelectorAll('.omission')].filter(t=>t.value.trim()).map(t=>({prompt:t.dataset.prompt,answer:t.value}))};}
function restore(value){if(value.review_id!==data.review_id||value.proposal_sha256!==data.proposal_sha256)throw Error('This decisions file belongs to a different proposal.');for(const d of value.decisions||[]){if(!byKey.has(d.key)||byKey.get(d.key).fingerprint!==d.fingerprint)throw Error('A reviewed item no longer matches.');}reviewer.value=value.reviewed_by||'';for(const d of value.decisions||[]){const c=cards.find(c=>c.dataset.key===d.key);c.querySelector('.action').value=d.action;c.querySelector('.note').value=d.note||'';if(c.querySelector('.reassess')){c.querySelector('.reassess').checked=!!d.reassessment;c.querySelector('.reassessment-reason').value=d.reassessment?.reason||'';}if(c.querySelector('.publication'))c.querySelector('.publication').value=d.publication||'unchanged';}for(const answer of value.omissions||[]){const t=[...document.querySelectorAll('.omission')].find(t=>t.dataset.prompt===answer.prompt);if(t)t.value=answer.answer;} }

function answerState(card) {
    const action = card.querySelector('.action').value;
    const note = card.querySelector('.note').value.trim();
    if (action === 'correct') return note ? 'answered' : 'unanswered';
    if (action === 'later' || action === 'unsure') return 'deferred';
    if (action === 'accept' || card.dataset.reviewed === 'accepted') return 'answered';
    // Notes and privacy-only decisions are retained for follow-up, not called acceptance.
    const publication = card.querySelector('.publication')?.value;
    if (note || (publication && publication !== 'unchanged')) return 'deferred';
    return 'unanswered';
}
function counts(items) {
    const result = {answered: 0, deferred: 0, unanswered: 0};
    for (const card of items) result[answerState(card)]++;
    return result;
}
function matchingCards() {
    const group = groupInput.value, change = changeInput.value, term = searchInput.value.toLowerCase();
    return cards.filter(card => {
        if (connectedKeys && !connectedKeys.has(card.dataset.key)) return false;
        if (group === 'career' && ['field', 'source_records'].includes(card.dataset.group)) return false;
        if (group && group !== 'career' && card.dataset.group !== group) return false;
        if (change === 'attention' && card.dataset.reviewed === 'accepted') return false;
        if (change === 'unfinished' && (card.dataset.reviewed === 'accepted' || answerState(card) === 'answered')) return false;
        if (change && !['attention', 'unfinished'].includes(change) && card.dataset.change !== change) return false;
        return card.textContent.toLowerCase().includes(term);
    });
}
function updateProgress() {
    const total = queue.length, tally = counts(queue), batches = Math.ceil(total / batchSize);
    document.getElementById('page').textContent = total
        ? `Questions ${page * batchSize + 1}–${Math.min((page + 1) * batchSize, total)} of ${total}`
        : 'No questions in this view';
    document.getElementById('progress').textContent = `${tally.answered} answered · ${tally.deferred} deferred · ${tally.unanswered} unanswered`;
    batchJump.replaceChildren();
    for (let n = 0; n < batches; n++) {
        const batch = counts(queue.slice(n * batchSize, (n + 1) * batchSize));
        const option = document.createElement('option');
        option.value = String(n);
        option.textContent = `${n + 1} of ${batches} · ${batch.unanswered} unanswered · ${batch.deferred} deferred`;
        batchJump.append(option);
    }
    batchJump.value = String(page); batchJump.disabled = !total;
    document.getElementById('previous').disabled = page === 0;
    document.getElementById('next').disabled = page + 1 >= batches;
    document.getElementById('unfinished').disabled = !queue.some(card => answerState(card) !== 'answered');
}
function renderQueue() {
    queue = matchingCards();
    page = Math.max(0, Math.min(page, Math.ceil(queue.length / batchSize) - 1));
    for (const card of cards) card.hidden = true;
    for (const card of queue.slice(page * batchSize, (page + 1) * batchSize)) card.hidden = false;
    const empty = document.getElementById('empty-queue');
    empty.hidden = !!queue.length;
    if (!queue.length) {
        const pending = cards.filter(card => card.dataset.reviewed !== 'accepted');
        empty.replaceChildren(document.createTextNode(pending.length
            ? `${pending.length} records still need review, but none match these filters. `
            : 'All records in this proposal have already been reviewed. You can browse them using All records.'));
        if (pending.length) {
            const reset = document.createElement('button'); reset.textContent = 'Show all pending records';
            reset.onclick = () => { groupInput.value = ''; changeInput.value = 'attention'; searchInput.value = ''; connectedKeys = null; page = 0; renderQueue(); focusBatch(); };
            empty.append(reset);
        }
    }
    updateProgress();
}
function navigationState() {
    const anchor = queue.slice(page * batchSize, (page + 1) * batchSize)
        .find(card => card.getBoundingClientRect().bottom > 0);
    return {page, group: groupInput.value, change: changeInput.value, search: searchInput.value,
        connected: connectedKeys ? [...connectedKeys] : null, scrollY: window.scrollY,
        anchor: anchor ? {key: anchor.dataset.key, top: anchor.getBoundingClientRect().top} : null,
        expanded: [...document.querySelectorAll('details')].flatMap((item, index) => item.open ? [index] : [])};
}
function rememberPlace() {
    if (restoring) return;
    try { localStorage.setItem(navigationKey, JSON.stringify(navigationState())); } catch (_) { /* Saving decisions reports storage failures. */ }
}
function saveDraft() {
    try {
        localStorage.setItem(storageKey, JSON.stringify(collect()));
        status.textContent = 'Draft saved in this browser. Career pack unchanged; download decisions to apply them.';
    } catch (_) {
        status.textContent = 'Browser storage is unavailable. Your choices remain on this page; download decisions before closing it.';
    }
    rememberPlace();
    // Do not refilter while answering: the five questions stay stable until navigation.
    updateProgress();
}
function focusBatch(card = queue[page * batchSize]) {
    const target = card?.querySelector('header') || document.getElementById('review-heading');
    target.focus({preventScroll: true});
    target.scrollIntoView({block: 'start', behavior: 'instant'});
    rememberPlace();
}
function goToBatch(next) {
    saveDraft();
    page = next;
    renderQueue();
    focusBatch();
}
for (const card of cards) card.addEventListener('input', saveDraft);
document.querySelectorAll('.omission').forEach(input => input.addEventListener('input', saveDraft));
reviewer.addEventListener('input', saveDraft);
for (const input of [groupInput, changeInput, searchInput]) input.addEventListener('input', () => {
    connectedKeys = null; page = 0; renderQueue();
    // Search retains typing focus, but changed results are brought into view.
    if (input === searchInput) document.getElementById('review-heading').scrollIntoView({block: 'start', behavior: 'instant'});
    else focusBatch();
    rememberPlace();
});
document.getElementById('previous').onclick = () => goToBatch(page - 1);
document.getElementById('next').onclick = () => goToBatch(page + 1);
batchJump.onchange = () => goToBatch(Number(batchJump.value));
document.getElementById('unfinished').onclick = () => {
    const start = (page + 1) * batchSize;
    const candidates = queue.slice(start).concat(queue.slice(0, start));
    const card = candidates.find(item => answerState(item) !== 'answered');
    if (card) { goToBatch(Math.floor(queue.indexOf(card) / batchSize)); focusBatch(card); }
};
document.getElementById('start-review').onclick = () => focusBatch();
function downloadDecisions() {
    saveDraft();
    const value = collect();
    if (!value.reviewed_by) {
        document.getElementById('review-help').open = true;
        status.textContent = 'Enter your name to download your review decisions.';
        reviewer.focus(); return;
    }
    const incomplete = value.decisions.find(row => row.action === 'correct' && !row.note.trim());
    if (incomplete) {
        groupInput.value = ''; changeInput.value = ''; searchInput.value = ''; connectedKeys = null;
        renderQueue();
        const card = cards.find(item => item.dataset.key === incomplete.key);
        page = Math.floor(queue.indexOf(card) / batchSize); renderQueue(); focusBatch(card);
        card.querySelector('.note').focus({preventScroll: true});
        status.textContent = 'Explain this correction before downloading. Your draft is retained.'; return;
    }
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2) + '\n'], {type: 'application/json'}));
    const link = document.createElement('a'); link.href = url; link.download = data.review_id + '-decisions.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    status.textContent = 'Decisions downloaded. Give the file to the career tool to apply them; your career pack has not changed yet.';
    rememberPlace();
}
document.getElementById('download').onclick = downloadDecisions;
document.getElementById('pause').onclick = downloadDecisions;
document.getElementById('pause-nav').onclick = downloadDecisions;
document.querySelectorAll('.jump,.connected').forEach(button => button.onclick = () => {
    const key = button.dataset.target, group = data.groups.find(item => item.achievement === key);
    connectedKeys = new Set(button.classList.contains('connected') ? [key, ...(group?.support || [])] : [key]);
    groupInput.value = ''; changeInput.value = ''; searchInput.value = ''; page = 0; renderQueue();
    const card = cards.find(item => item.dataset.key === key);
    page = Math.floor(queue.indexOf(card) / batchSize); renderQueue(); focusBatch(card);
});
function previewChoices(){const choices=collect(), accepted=new Set(choices.decisions.filter(d=>d.action==='accept').map(d=>d.key));const panel=document.getElementById('choices-preview');panel.hidden=false;panel.replaceChildren();const heading=document.createElement('h3');heading.textContent='Your proposed save';panel.append(heading);for(const d of choices.decisions){const line=document.createElement('p');line.textContent=byKey.get(d.key).title+': '+(d.action==='accept'?'accept exact wording':d.action==='correct'?'save correction for follow-up':'leave pending')+'; external use: '+d.publication+(d.reassessment?'; explicitly reassess evidence as '+d.reassessment.status:'');panel.append(line);}for(const g of data.groups.filter(g=>accepted.has(g.achievement))){const missing=g.support.filter(k=>!accepted.has(k)&&byKey.get(k)?.change!=='unchanged'&&byKey.get(k)?.review_status!=='accepted');if(missing.length){const line=document.createElement('p');line.className='notice';line.textContent='Also review the supporting records for '+byKey.get(g.achievement).title+': '+missing.map(k=>byKey.get(k)?.title||k).join(', ')+'. No supporting record is automatically accepted.';panel.append(line);}}const pending=document.createElement('p');pending.textContent=data.items.filter(r=>r.review_status!=='accepted'&&!accepted.has(r.key)).length+' items remain pending. The assistant checks source integrity and exact dependencies before saving; this preview does not change your pack.';panel.append(pending);}

document.getElementById('preview-choices').onclick = previewChoices;
document.getElementById('load').onclick = () => document.getElementById('load-file').click();
document.getElementById('load-file').onchange = async event => {
    if (!event.target.files.length) return;
    try { restore(JSON.parse(await event.target.files[0].text())); renderQueue(); saveDraft(); }
    catch (error) { status.textContent = error.message; }
};
restore({review_id: data.review_id, proposal_sha256: data.proposal_sha256, reviewed_by: '',
    decisions: data.items.filter(row => row.decision).map(row => row.decision), omissions: data.omissions});
let savedNavigation;
try {
    const saved = localStorage.getItem(storageKey);
    if (saved) restore(JSON.parse(saved));
    savedNavigation = JSON.parse(localStorage.getItem(navigationKey) || 'null');
    if (savedNavigation) {
        groupInput.value = savedNavigation.group || ''; changeInput.value = savedNavigation.change || '';
        searchInput.value = savedNavigation.search || '';
        page = Number.isInteger(savedNavigation.page) ? savedNavigation.page : 0;
        if (Array.isArray(savedNavigation.connected)) connectedKeys = new Set(savedNavigation.connected.filter(key => byKey.has(key)));
        const details = [...document.querySelectorAll('details')];
        for (const index of savedNavigation.expanded || []) if (details[index]) details[index].open = true;
    }
} catch (_) { status.textContent = 'No browser progress loaded. You can resume from a downloaded decisions file.'; }
renderQueue();
const navigation = document.querySelector('.review-navigation');
function fitNavigation() { document.documentElement.style.setProperty('--navigation-height', navigation.getBoundingClientRect().height + 'px'); }
new ResizeObserver(fitNavigation).observe(navigation); fitNavigation();
if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
requestAnimationFrame(() => requestAnimationFrame(() => {
    if (savedNavigation) {
        const anchor = cards.find(card => card.dataset.key === savedNavigation.anchor?.key && !card.hidden);
        const top = savedNavigation.anchor?.top;
        if (anchor && Number.isFinite(top)) window.scrollTo(0, window.scrollY + anchor.getBoundingClientRect().top - top);
        else if (Number.isFinite(savedNavigation.scrollY)) window.scrollTo(0, savedNavigation.scrollY);
    }
    restoring = false;
}));
window.addEventListener('scroll', () => { clearTimeout(scrollTimer); scrollTimer = setTimeout(rememberPlace, 150); }, {passive: true});
document.querySelectorAll('details').forEach(item => item.addEventListener('toggle', rememberPlace));
window.addEventListener('pagehide', rememberPlace);
