"""A private, offline career review document. Renders recorded data, never summaries."""
import html
import json

from pack_review import COLLECTIONS, PROMPTS
from career_profile import digest

LABELS = {'evidence_atoms':'My achievements','employment':'My career timeline','education':'My education',
          'strengths_profile':'My strengths','positioning_preferences':'What I want next',
          'source_records':'Original sources','field':'Other recorded details'}
FIELDS = {'situation':'Context','task':'Responsibility','action':'Your contribution','result':'What changed',
          'external_safe':'External use recorded in proposal','evidence_status':'Evidence supporting this',
          'self_asserted':'Recorded in your own account','externally_verified':'Independently verified',
          'corroborated':'Supported by others','unresolved':'Unresolved','declined':'Not pursued',
          'interpretation':'Interpretation','evidence_ids':'Supporting achievements','timeframe':'When this applies',
          'limitations':'Limits of this interpretation','status':'Recorded status','text':'Your preference',
          'source_refs':'Source excerpts','private_profile':'Personal details','known_conflicts':'Conflicting information',
          'occurred':'Recorded dates','inferred':'Dates are approximate','start':'From','end':'To',
          'metrics':'Recorded measures','basis':'Measurement information','measured':'Explicitly measured',
          'question_status':'Interview progress','open_questions':'Questions still open', 'scope':'Scope of your role'}


def esc(value):
    return html.escape(str(value), quote=True)


def show(value, key=''):
    if value is None:
        return '<span class="muted">Not recorded</span>'
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, list):
        return '<ul>' + ''.join('<li>' + show(v, key) + '</li>' for v in value) + '</ul>' if value else '<span class="muted">Nothing recorded</span>'
    if isinstance(value, dict):
        technical = {'evidence_fingerprints', 'capture', 'source_id', 'employment_id', 'education_id', 'id'}
        displayed = [(k,v) for k,v in value.items() if k not in technical]
        return '<dl>' + ''.join('<dt>' + esc(FIELDS.get(k,k.replace('_',' ').capitalize())) + '</dt><dd>' + show(v,k) + '</dd>' for k,v in displayed) + '</dl>'
    return esc(FIELDS.get(value,value) if key == 'evidence_status' else value)


def title(row):
    value = row['after'] if row['after'] is not None else row['before']
    if isinstance(value, dict):
        if row['key'].startswith('employment/'):
            return value.get('title','Role') + ' · ' + value.get('employer','')
        return value.get('title') or value.get('interpretation') or value.get('institution') or value.get('text') or value.get('path') or row['key'].split('/',1)[1]
    return FIELDS.get(row['key'].split('/',1)[1], row['key'].split('/',1)[1].replace('_',' ').capitalize())


def render_review(state):
    session = state['session']
    rows = state['items']
    changes = {kind:sum(r['change']==kind for r in rows) for kind in ('added','changed','removed','unchanged')}
    sources = {r['key'].split('/',1)[1]:r['after'] for r in rows if r['key'].startswith('source_records/') and r['after']}
    cards=[]
    for row in rows:
        value = row['after'] if row['after'] is not None else row['before']
        data = value if isinstance(value, dict) else {}
        refs = data.get('source_refs',[])
        excerpts = []
        for ref in refs:
            source = sources.get(ref['source_id'],{})
            excerpts.append('<section class="excerpt"><strong>'+esc(source.get('path',ref['source_id']))+'</strong><p>'+esc(ref.get('locator',''))+'</p><blockquote>'+esc(ref.get('excerpt') or 'No source excerpt recorded')+'</blockquote></section>')
        warnings=[]
        if (data.get('occurred') or {}).get('inferred'):warnings.append('The dates are approximate. Please check them.')
        if data.get('open_questions'):warnings.append('There are questions still open for this item.')
        if row['key'].startswith('strengths_profile/'):warnings.append('This is an interpretation of your achievements, not a new factual claim.')
        permission = data.get('external_safe')
        publication = ''
        if isinstance(permission,bool):
            publication = '<label>Permission for external use<select class="publication"><option value="unchanged">Keep existing permission; changed content stays private</option><option value="private">Keep private</option><option value="external">Allow this exact content externally</option></select></label>'
        status = {'accepted':'Previously reviewed by you','not_reviewed':'Not yet reviewed by you','changed_since_review':'Changed since you reviewed it','awaiting_review':'Awaiting your review'}[row['review_status']]
        evidence = FIELDS.get(data.get('evidence_status'),data.get('evidence_status','Not applicable'))
        public = 'Permitted externally in proposal' if permission is True else 'Private in proposal' if permission is False else 'No publication permission on this item'
        content = show({k:v for k,v in data.items() if k not in ('source_refs','external_safe','evidence_status')} if isinstance(value,dict) else value)
        if row['key'].startswith('strengths_profile/'):
            support = [r for r in rows if r['key'] in ['evidence_atoms/' + aid for aid in data.get('evidence_ids',[])]]
            content += '<details><summary>Achievements supporting this interpretation</summary>' + ''.join('<h4>' + esc(title(r)) + '</h4>' + show((r['after'] or r['before']).get('star',{})) for r in support) + '</details>'
        previous = '<details><summary>What was recorded before</summary>'+show(row['before'])+'</details>' if row['change'] in ('changed','removed') else ''
        if row['change']=='removed':content='<p><strong>This proposal removes this item. Acceptance will remove it from the next pack, not from its history.</strong></p>'+content
        cards.append('<article class="card" data-key="'+esc(row['key'])+'" data-group="'+esc(row['key'].split('/')[0])+'" data-change="'+row['change']+'" data-reviewed="'+row['review_status']+'"><header><span class="tag">'+esc(row['change'].capitalize())+'</span><h3>'+esc(title(row))+'</h3></header><p class="review-state">'+esc(status)+'</p><p class="muted">Evidence: '+esc(evidence)+' · '+esc(public)+'</p>'+''.join('<p class="notice">'+esc(w)+'</p>' for w in warnings)+content+previous+'<details><summary>Show original source excerpts</summary>'+(''.join(excerpts) or '<p>No excerpt attached to this item.</p>')+'</details><details><summary>All stored fields and reference IDs</summary><pre>'+esc(json.dumps(value,indent=2,ensure_ascii=False))+'</pre></details><div class="decide"><label>Your review<select class="action"><option value="">Choose when ready</option><option value="accept">Looks accurate — accept this wording</option><option value="correct">Correct this</option><option value="unsure">Not sure</option><option value="later">Review later</option></select></label>'+publication+'<label>Correction or explanation<textarea class="note" rows="2" placeholder="Your words. Corrections are recorded for follow-up; they do not silently rewrite this item."></textarea></label></div></article>')
    bootstrap={'review_id':session['review_id'],'proposal_sha256':session['proposal']['sha256'],
               'items':[{'key':r['key'],'fingerprint':r['fingerprint'],'decision':r.get('decision')} for r in rows],
               'omissions':state.get('omissions',[])}
    bootstrap['ledger_sha256'] = digest(bootstrap)
    payload=json.dumps(bootstrap,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    groups=''.join('<option value="'+esc(k)+'">'+esc(v)+'</option>' for k,v in LABELS.items())
    omissions=''.join('<label>'+esc(p)+'<textarea class="omission" data-prompt="'+esc(p)+'" rows="3"></textarea></label>' for p in PROMPTS)
    if session.get('validation_warnings'):
        omissions += '<div class="notice"><strong>Some existing information needs correction before a new version can be accepted.</strong><p>You can save your review now. Ask the tool to work through these issues using your answers.</p><details><summary>Recorded validation issues</summary>' + show(session['validation_warnings']) + '</details></div>'
    return PAGE.replace('@@TITLE@@',esc('Review your career record')).replace('@@CHANGES@@',esc(f"{changes['added']} added · {changes['changed']} changed · {changes['removed']} proposed removals · {changes['unchanged']} unchanged")).replace('@@GROUPS@@',groups).replace('@@CARDS@@',''.join(cards)).replace('@@OMISSIONS@@',omissions).replace('@@DATA@@',payload)


PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>@@TITLE@@</title>
<style>
:root{color-scheme:light;--ink:#19332d;--muted:#52665f;--line:#d8e1dc;--green:#205d4c}*{box-sizing:border-box}body{margin:0;background:#f5f5ef;color:var(--ink);font:16px/1.55 system-ui,sans-serif}main{max-width:1040px;margin:auto;padding:32px 24px 100px}h1{font:600 36px/1.15 Georgia,serif;margin:10px 0}h2{font-size:23px}h3{font-size:20px;margin:8px 0}p{max-width:80ch}.eyebrow{color:var(--green);text-transform:uppercase;letter-spacing:.12em;font-size:12px}.muted,.review-state{color:var(--muted);font-size:14px}.notice{background:#fff2cd;padding:12px;border-radius:6px}.toolbar{position:sticky;top:0;background:#f5f5eff5;padding:14px 0;border-bottom:1px solid var(--line);z-index:2;display:flex;flex-wrap:wrap;gap:10px;align-items:center}input,select,textarea,button{font:inherit;border:1px solid #a6b9ae;border-radius:6px;padding:9px;background:white;color:var(--ink)}textarea{width:100%;resize:vertical}label{display:block;font-size:14px;margin:12px 0}label select{display:block;width:100%;margin-top:5px}button{cursor:pointer}button.primary{background:var(--green);color:white}.card,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:24px;margin:18px 0}.tag{font-size:12px;text-transform:uppercase;color:var(--green);letter-spacing:.08em}dl{display:grid;grid-template-columns:minmax(100px,180px) 1fr;gap:8px 16px}dt{font-weight:600;font-size:14px}dd{margin:0;overflow-wrap:anywhere}dd dl{display:block}dd dt{margin-top:8px}ul{margin:0;padding-left:20px}details{border-top:1px solid var(--line);padding:12px 0}summary{cursor:pointer;color:var(--green)}blockquote{border-left:3px solid #b1cfc0;margin:12px 0;padding-left:15px;white-space:pre-wrap}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.decide{border-top:1px solid var(--line);margin-top:15px}.progress{font-weight:600}.pagination{display:flex;gap:12px;align-items:center;margin:18px 0}#save-status{min-height:25px}input[type=search]{min-width:180px;flex:1}footer{font-size:13px;color:var(--muted)}[hidden]{display:none!important}:focus-visible{outline:3px solid #dca946;outline-offset:3px}@media(max-width:650px){main{padding:20px 12px}h1{font-size:30px}.card{padding:16px}dl{grid-template-columns:1fr}dd{margin-bottom:8px}}@media print{.toolbar,.decide,.pagination,button{display:none}.card[hidden]{display:block!important}.card{break-inside:avoid}}
</style></head><body><main><span class="eyebrow">Your career · Private review</span><h1>Does this record reflect you?</h1><p>Check what was captured, compare it with your sources, and tell us what needs correcting or adding. You can pause at any time.</p><p><strong>@@CHANGES@@</strong></p><p class="notice">This private document includes confidential records and personal details. Keep it on your device. Nothing is sent from this page.</p>
<section class="panel"><h2>What your choices mean</h2><p><strong>Looks accurate</strong> accepts the wording you can inspect here. It does not verify the claim independently or authorize external use. New or changed content stays private unless you separately allow it.</p><p><strong>Correct this</strong>, <strong>Not sure</strong> and <strong>Review later</strong> preserve your answer and keep the proposal pending. <strong>Keep private</strong> can restrict an existing item even while its correction is pending.</p><label>Your name<input id="reviewer" autocomplete="name" placeholder="Who reviewed these items?"></label><p id="save-status" role="status" aria-live="polite"></p><button id="download" class="primary">Save review decisions</button> <button id="load">Resume from a saved decisions file</button><input type="file" id="load-file" accept="application/json,.json" hidden><p class="muted">Choices may be kept in this browser for this proposal. Download them to keep a portable copy. The career pack changes only after these decisions are imported and accepted items are saved by the tool.</p></section>
<h2>Review your record</h2><div class="toolbar"><select id="group" aria-label="Career section"><option value="">All career sections</option>@@GROUPS@@</select><select id="change" aria-label="Changes"><option value="attention">Needs attention</option><option value="">All records</option><option value="added">Added</option><option value="changed">Changed</option><option value="removed">Proposed removals</option><option value="unchanged">Unchanged</option></select><input id="search" type="search" aria-label="Search your career" placeholder="Search a role, achievement or source"><span id="progress" class="progress" aria-live="polite"></span></div><div id="cards">@@CARDS@@</div><div class="pagination"><button id="previous">Previous</button><span id="page" aria-live="polite"></span><button id="next">Next five</button></div>
<section class="panel"><h2>What have we missed?</h2><p>An accurate list can still leave out your best work. These answers become follow-up notes, not automatic new achievements.</p>@@OMISSIONS@@</section><footer>Rendered directly from the recorded proposal and its previous version. A saved decision applies only to the exact reviewed content. Closing this page never accepts anything.</footer></main><script type="application/json" id="review-data">@@DATA@@</script><script>
'use strict';
const data=JSON.parse(document.getElementById('review-data').textContent), cards=[...document.querySelectorAll('.card')], byKey=new Map(data.items.map(r=>[r.key,r]));
const storageKey='career-review:'+data.review_id+':'+data.proposal_sha256+':'+data.ledger_sha256;let page=0;let saving=true;
const status=document.getElementById('save-status'), reviewer=document.getElementById('reviewer');
function collect(){return {review_id:data.review_id,proposal_sha256:data.proposal_sha256,reviewed_by:reviewer.value.trim(),decisions:cards.filter(c=>c.querySelector('.action').value||c.querySelector('.note').value.trim()||(c.querySelector('.publication')&&c.querySelector('.publication').value!=='unchanged')).map(c=>({key:c.dataset.key,fingerprint:byKey.get(c.dataset.key).fingerprint,action:c.querySelector('.action').value||'later',publication:c.querySelector('.publication')?.value||'unchanged',note:c.querySelector('.note').value})),omissions:[...document.querySelectorAll('.omission')].filter(t=>t.value.trim()).map(t=>({prompt:t.dataset.prompt,answer:t.value}))};}
function restore(value){if(value.review_id!==data.review_id||value.proposal_sha256!==data.proposal_sha256)throw Error('This decisions file belongs to a different proposal.');for(const d of value.decisions||[]){if(!byKey.has(d.key)||byKey.get(d.key).fingerprint!==d.fingerprint)throw Error('A reviewed item no longer matches.');}reviewer.value=value.reviewed_by||'';for(const d of value.decisions||[]){const c=cards.find(c=>c.dataset.key===d.key);c.querySelector('.action').value=d.action;c.querySelector('.note').value=d.note||'';if(c.querySelector('.publication'))c.querySelector('.publication').value=d.publication||'unchanged';}for(const answer of value.omissions||[]){const t=[...document.querySelectorAll('.omission')].find(t=>t.dataset.prompt===answer.prompt);if(t)t.value=answer.answer;} }
function filter(){const group=document.getElementById('group').value, change=document.getElementById('change').value, term=document.getElementById('search').value.toLowerCase();const visible=cards.filter(c=>(!group||c.dataset.group===group)&&(!change||change==='attention'?(change!=='attention'||c.dataset.reviewed!=='accepted'):c.dataset.change===change)&&c.textContent.toLowerCase().includes(term));page=Math.max(0,Math.min(page,Math.ceil(visible.length/5)-1));for(const c of cards)c.hidden=true;visible.slice(page*5,page*5+5).forEach(c=>c.hidden=false);document.getElementById('page').textContent=visible.length?`${page*5+1}–${Math.min(page*5+5,visible.length)} of ${visible.length}`:'No matching records';document.getElementById('previous').disabled=page===0;document.getElementById('next').disabled=(page+1)*5>=visible.length;document.getElementById('progress').textContent=`${collect().decisions.length} choices recorded here`;}
function save(){if(saving){try{localStorage.setItem(storageKey,JSON.stringify(collect()));status.textContent='Progress saved in this browser. Download a copy before leaving this device.';}catch(e){status.textContent='Browser storage is unavailable. Use Save review decisions to keep your progress.';}}filter();}
for(const c of cards)c.addEventListener('input',save);document.querySelectorAll('.omission').forEach(t=>t.addEventListener('input',save));reviewer.addEventListener('input',save);
for(const id of ['group','change','search'])document.getElementById(id).addEventListener('input',()=>{page=0;filter();});document.getElementById('previous').onclick=()=>{page--;filter();};document.getElementById('next').onclick=()=>{page++;filter();};
document.getElementById('download').onclick=()=>{const value=collect();if(!value.reviewed_by){status.textContent='Enter your name before saving your decisions.';reviewer.focus();return;}if(value.decisions.some(d=>d.action==='correct'&&!d.note.trim())){status.textContent='Please explain each requested correction before saving.';return;}const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=data.review_id+'-decisions.json';a.click();URL.revokeObjectURL(url);status.textContent='Decisions file downloaded. Give this file to the career tool to record your choices; your pack has not changed yet.';};
document.getElementById('load').onclick=()=>document.getElementById('load-file').click();document.getElementById('load-file').onchange=async e=>{try{const value=JSON.parse(await e.target.files[0].text());restore(value);save();}catch(err){status.textContent=err.message;}};
restore({review_id:data.review_id,proposal_sha256:data.proposal_sha256,reviewed_by:'',decisions:data.items.filter(r=>r.decision).map(r=>r.decision),omissions:data.omissions});try{const saved=localStorage.getItem(storageKey);if(saved)restore(JSON.parse(saved));}catch(e){status.textContent='No browser progress loaded. You can resume from a downloaded file.';}filter();
</script></body></html>'''
