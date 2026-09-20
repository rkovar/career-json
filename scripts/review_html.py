"""A private, offline career review document. Renders recorded data, never summaries."""
import html
import json
from pathlib import Path

from pack_review import COLLECTIONS, PROMPTS
from career_profile import digest

LABELS = {'evidence_atoms':'My achievements','employment':'My career timeline','education':'My education',
          'strengths_profile':'My strengths','positioning_preferences':'What I want next',
          'publications':'Publications, talks and media','source_records':'Original sources','field':'Other recorded details'}
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
        technical = {'evidence_fingerprints', 'capture', 'source_id', 'employment_id', 'education_id', 'publication_id', 'evidence_id', 'id'}
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


def count_label(number, noun):
    return str(number) + ' ' + noun + ('' if number == 1 else 's')


def overview(state):
    """A direct view of career content, before the approval machinery."""
    items = state['items']
    values = lambda group: [r['after'] for r in items if r['key'].startswith(group + '/') and r['after'] is not None]
    roles = sorted(values('employment'), key=lambda r: r.get('start') or '', reverse=True)
    atoms = sorted(values('evidence_atoms'), key=lambda r: (r.get('occurred') or {}).get('start') or '', reverse=True)
    strengths = values('strengths_profile')
    def contributions(rows):
        return '<ul>' + ''.join('<li><strong>' + esc(a['title']) + '</strong><p>'
            + esc((a.get('star') or {}).get('action') or 'Contribution not yet recorded') + '</p><p>'
            + esc((a.get('star') or {}).get('result') or 'Outcome not yet recorded') + '</p></li>' for a in rows) + '</ul>'
    body = ''
    for role in roles:
        from career_state import dates
        body += '<h3>' + esc(role['employer']) + ' · ' + esc(role['title']) + '</h3><p>' + esc(dates(role)) + '</p>'
        body += contributions([a for a in atoms if a.get('employment_id') == role['employment_id']])
    unlinked = [a for a in atoms if a.get('employment_id') not in {r['employment_id'] for r in roles}]
    if unlinked:
        body += '<h3>Other contributions</h3>' + contributions(unlinked)
    for group, heading in [('education', 'Education'), ('publications', 'Publications, talks and media')]:
        if values(group):
            body += '<h3>' + heading + '</h3>' + show(values(group))
    if strengths:
        body += '<details><summary>Recorded strengths (interpretations)</summary>' + show(strengths) + '</details>'
    return ('<section class="panel" id="career-overview"><h2>Your proposed career record</h2><p>This includes every proposed role and achievement. Checking it here does not accept it automatically.</p>'
            + '<p><strong>' + str(len(roles)) + ' roles · ' + str(len(atoms)) + ' achievements</strong></p>'
            + (body or '<p>No career details recorded yet.</p>') + '</section>' + source_coverage_html(state))


def source_coverage_html(state):
    report = state.get('summary', {}).get('source_coverage')
    if not report:
        return ''
    counts = report['counts']
    message = (f"{counts.get('linked', 0)} sources linked to career records · "
               f"{counts.get('pending', 0)} still to process · {counts.get('deferred', 0)} deferred")
    rows = ''.join('<li>' + esc(r['path']) + ': ' + esc(r['outcome'])
                   + (' — ' + esc(r['reason']) if r.get('reason') else '') + '</li>' for r in report['sources'])
    return ('<section class="panel"><h2>Source coverage</h2><p>' + esc(message) + '</p>'
            + ''.join('<p>' + esc(error) + '</p>' for error in report['errors'])
            + '<details><summary>Sources and remaining work</summary><ul>' + rows + '</ul></details></section>')



def achievement_content(value, roles):
    """Show the career story first, keeping full fields and sources available."""
    role = roles.get(value.get('employment_id'), {})
    context = ('<p><strong>' + esc(role.get('employer', '')) + '</strong> · ' + esc(role.get('title', ''))
               + ' · ' + esc(role.get('start') or 'Start not recorded') + ' – ' + esc(role.get('end') or 'End not recorded') + '</p>') if role else ''
    star = value.get('star') or {}
    main = ''.join('<p><strong>' + label + '</strong><br>' + esc(star[field]) + '</p>'
                   for field, label in (('action', 'Your contribution'), ('result', 'What changed')) if star.get(field))
    details = {k: v for k, v in value.items() if k not in ('title', 'star', 'id', 'source_refs', 'external_safe', 'evidence_status')}
    details = {**{k: star[k] for k in ('situation', 'task') if star.get(k)}, **details}
    return context + main + '<details><summary>Context, measures and other recorded details</summary>' + show(details) + '</details>'


def editor_controls(row):
    from career_review import editable_fields
    if not isinstance(row['after'], dict):
        return ''
    fields = editable_fields(row['key'], row['after'])
    if not fields:
        return ''
    labels = {'title': 'Title', 'employer': 'Employer', 'start': 'Start date', 'end': 'End date',
              'star.situation': 'Context', 'star.task': 'Responsibility', 'star.action': 'Your contribution', 'star.result': 'What changed'}
    controls = ''.join('<label>' + esc(labels[field]) + '<textarea class="wording" data-field="' + esc(field)
                       + '" rows="2">' + esc(value or '') + '</textarea></label>' for field, value in fields.items())
    return ('<details class="wording-editor"><summary>Correct the recorded wording</summary>'
            '<p>Edit the details below, then review the revised item before confirming it. Blank dates remain unknown.</p>'
            + controls + '<button type="button" class="correct-wording">Show revised wording</button></details>')


def stopping_point(state):
    summary = state.get('summary', {})
    return ('<section class="panel" id="stopping-point"><h2>A useful place to stop</h2><p>' + esc(summary.get('stopping_point', 'You can pause now and return to this proposal later.')) + '</p>'
            + '<p>' + count_label(summary.get('saved_roles', 0), 'role') + ' and ' + count_label(summary.get('saved_achievements', 0), 'achievement') + ' in your current pack. '
            + str(summary.get('pending_items', len(state['items']))) + ' review items remain; ' + str(summary.get('corrections', 0)) + ' have correction notes.</p>'
            + '<p>' + count_label(summary.get('questions', 0), 'factual clarification') + '; '
            + count_label(summary.get('optional_questions', 0), 'optional question') + '; '
            + count_label(summary.get('deferred_questions', 0), 'deferred question') + '.</p>'
            + '<p class="muted">These counts describe the last saved state when this page was generated. Browser choices still need to be applied by the tool.</p>'
            + '<button id="pause">Save my review and pause</button><p>To return, say: <strong>Continue my career-pack review.</strong></p>'
            + ('<p>Try your saved record: <strong>' + esc(summary['recall_prompt']) + '</strong></p>' if summary.get('recall_prompt') else '<p>Once an achievement is accepted, try: <strong>Show me one recorded achievement and its original source.</strong></p>') + '</section>')


def render_review(state):
    session = state['session']
    order = {'evidence_atoms': 0, 'employment': 1, 'strengths_profile': 2, 'positioning_preferences': 3, 'education': 4, 'field': 5, 'source_records': 6}
    grouped = session.get('review_version') == 2
    rows = sorted(state['items'], key=lambda r: (order.get(r['key'].split('/')[0], 7), r['key']))
    roles = {r['after']['employment_id']: r['after'] for r in rows if r['key'].startswith('employment/') and r['after']}
    if grouped:
        role_order = {r['employment_id']: i for i, r in enumerate(sorted(roles.values(), key=lambda v: v.get('start') or '', reverse=True))}
        def career_order(row):
            value = row['after'] or row['before'] or {}
            if row['key'].startswith(('employment/', 'evidence_atoms/')):
                return (0, role_order.get(value.get('employment_id'), len(role_order)), 0 if row['key'].startswith('employment/') else 1, row['key'])
            return (1, order.get(row['key'].split('/')[0], 7), 0, row['key'])
        rows.sort(key=career_order)
    changes = {kind:sum(r['change']==kind for r in rows) for kind in ('added','changed','removed','unchanged')}
    sources = {r['key'].split('/',1)[1]:r['after'] for r in rows if r['key'].startswith('source_records/') and r['after']}
    cards=[]
    for row in rows:
        if grouped and row.get('source_registration'):
            continue
        value = row['after'] if row['after'] is not None else row['before']
        data = value if isinstance(value, dict) else {}
        refs = data.get('source_refs',[])
        excerpts = []
        for ref in refs:
            source = sources.get(ref['source_id'],{})
            excerpts.append('<section class="excerpt"><strong>'+esc(source.get('path',ref['source_id']))+'</strong><p>'+esc(ref.get('locator',''))+'</p><blockquote>'+esc(ref.get('excerpt') or 'No source excerpt recorded')+'</blockquote></section>')
            annotation = session.get('source_annotations', {}).get(ref['source_id'])
            if annotation:
                excerpts.append('<details><summary>Import commentary (not verified career evidence)</summary>' + show(annotation.get('notes')) + '</details>')
        warnings=[]
        if (data.get('occurred') or {}).get('inferred'):warnings.append('The dates are approximate. Please check them.')
        if data.get('open_questions'):warnings.append('There are questions still open for this item.')
        if row['key'].startswith('strengths_profile/'):warnings.append('This is an interpretation of your achievements, not a new factual claim.')
        permission = data.get('external_safe')
        publication = ''
        if isinstance(permission,bool):
            publication = '<details><summary>External use (optional; you can keep this private)</summary><label>Permission for external use<select class="publication"><option value="unchanged">Keep existing permission; changed content stays private</option><option value="private">Keep private</option><option value="external">Allow this exact content externally</option></select></label></details>'
        status = {'accepted':'Previously reviewed by you','not_reviewed':'Not yet reviewed by you','changed_since_review':'Changed since you reviewed it','awaiting_review':'Awaiting your review','registered':'Source registered; factual claims still need your review'}[row['review_status']]
        evidence = FIELDS.get(data.get('evidence_status'),data.get('evidence_status','Not applicable'))
        public = 'Permitted externally in proposal' if permission is True else 'Private in proposal' if permission is False else 'No publication permission on this item'
        content = show({k:v for k,v in data.items() if k not in ('source_refs','external_safe','evidence_status')} if isinstance(value,dict) else value)
        if grouped and row['key'].startswith('evidence_atoms/'):
            content = achievement_content(data, roles)
        if grouped and row['key'].startswith('employment/'):
            content = '<p class="notice">Confirm this role once. Its dates and title provide the context for the achievements below.</p>' + content
        if row['key'].startswith('strengths_profile/'):
            support = [r for r in rows if r['key'] in ['evidence_atoms/' + aid for aid in data.get('evidence_ids',[])]]
            content += '<details><summary>Achievements supporting this interpretation</summary>' + ''.join('<h4>' + esc(title(r)) + '</h4>' + show((r['after'] or r['before']).get('star',{})) for r in support) + '</details>'
        previous = '<details><summary>What was recorded before</summary>'+show(row['before'])+'</details>' if row['change'] in ('changed','removed') else ''
        if row['change']=='removed':content='<p><strong>This proposal removes this item. Acceptance will remove it from the next pack, not from its history.</strong></p>'+content
        related = next((g['support'] for g in state.get('groups', []) if g['achievement'] == row['key']), [])
        if grouped:
            related = [key for key in related if not next((r.get('source_registration') for r in rows if r['key'] == key), False)]
        if related:
            content += '<section><h4>Role and sources for this achievement</h4>'
            for key in related:
                support_row = next((r for r in rows if r['key'] == key), None)
                if support_row:
                    content += '<details><summary>' + esc(title(support_row)) + '</summary>' + show(support_row['after']) + '<button type="button" class="jump" data-target="' + esc(key) + '">Review this supporting record</button></details>'
            content += '<button type="button" class="connected" data-target="' + esc(row['key']) + '">Show achievement and role together</button></section>'
        if data.get('evidence_status') in ('self_asserted', 'corroborated', 'externally_verified'):
            publication += '<details><summary>Evidence reassessment (separate from wording)</summary><label><input type="checkbox" class="reassess"> Explicitly adopt proposed evidence status: ' + esc(data['evidence_status']) + '</label><label>Why the attached sources justify this change<textarea class="reassessment-reason"></textarea></label><p>Requires acceptance and verifiable cited support. Resolving uncertainty requires your recorded answer; stronger corroboration requires independent support.</p></details>'
        if grouped and state.get('connection'):
            content += editor_controls(row)
        cards.append('<article class="card" data-key="'+esc(row['key'])+'" data-group="'+esc(row['key'].split('/')[0])+'" data-change="'+row['change']+'" data-reviewed="'+row['review_status']+'"><header tabindex="-1"><span class="tag">'+esc(row['change'].capitalize())+'</span><h3>'+esc(title(row))+'</h3></header><p class="review-state">'+esc(status)+'</p><p class="muted">Evidence: '+esc(evidence)+' · '+esc(public)+'</p>'+''.join('<p class="notice">'+esc(w)+'</p>' for w in warnings)+content+previous+'<details><summary>Show original source excerpts</summary>'+(''.join(excerpts) or '<p>No excerpt attached to this item.</p>')+'</details><details><summary>All stored fields and reference IDs</summary><pre>'+esc(json.dumps(value,indent=2,ensure_ascii=False))+'</pre></details><div class="decide"><label>Your review<select class="action"><option value="">Choose when ready</option><option value="accept">Looks accurate — accept this wording</option><option value="correct">Correct this</option><option value="unsure">Not sure</option><option value="later">Review later</option></select></label>'+publication+'<label>Correction or explanation<textarea class="note" rows="2" placeholder="Your words. Corrections are recorded for follow-up; they do not silently rewrite this item."></textarea></label></div></article>')
    bootstrap={'review_id':session['review_id'],'proposal_sha256':session['proposal']['sha256'],
               'items':[{'source_registration':r.get('source_registration',False), 'key':r['key'],'fingerprint':r['fingerprint'],'decision':r.get('decision'), 'title':title(r), 'evidence_status':(r['after'] or {}).get('evidence_status') if isinstance(r['after'],dict) else None, 'source_refs':(r['after'] or {}).get('source_refs',[]) if isinstance(r['after'],dict) else [], 'review_status':r['review_status'], 'change':r['change']} for r in rows], 'groups':state.get('groups',[]), 'grouped': grouped, 'connection': state.get('connection'),
               'omissions':state.get('omissions',[])}
    bootstrap['ledger_sha256'] = digest(bootstrap)
    payload=json.dumps(bootstrap,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    groups=''.join('<option value="'+esc(k)+'">'+esc(v)+'</option>' for k,v in LABELS.items())
    omissions=''.join('<label>'+esc(p)+'<textarea class="omission" data-prompt="'+esc(p)+'" rows="3"></textarea></label>' for p in PROMPTS)
    if session.get('validation_warnings'):
        omissions += '<div class="notice"><strong>Source and record checks need attention.</strong><p>Known mismatches block acceptance. Unavailable sources are reported separately. You can save your review progress now.</p><details><summary>Recorded validation issues</summary>' + show(session['validation_warnings']) + '</details></div>'
    template = PAGE.replace('@@NAVIGATION@@', Path(__file__).with_name('review_navigation.js').read_text(encoding='utf-8'))
    if grouped:
        template = template.replace('<option value="career">Career highlights</option>', '<option value="career" selected>Roles and achievements first</option>')
    template = template.replace('@@CONNECTION@@', '<button id="save-pack" class="primary">Save reviewed changes</button><a id="reading-link" hidden>Read saved career pack</a>' if state.get('connection') else '')
    if grouped:
        template = template.replace('New achievements need their role and source records accepted before they can be saved.',
            'Confirm each role once, then review its achievements. Verifiable source metadata is registered automatically; claims still need your approval. Other source changes remain reviewable.')
    if state.get('connection'):
        template = template.replace('Nothing is sent from this page.', 'This page saves only through the temporary connection to your local career workspace.')
        template = template.replace('Return to the conversation and say: “Apply my saved review decisions and show me what remains.” Tell the tool where you saved the file; it handles the import and refreshes this page.',
            'Use Save reviewed changes to update your career pack, or Save and next five to save and continue. Edit wording, choose Show revised wording, then confirm the revised proposal. Downloads are an optional portable copy.')
        template = template.replace('Browser choices still need to be applied by the tool.', 'The save status below reports later changes made during this session.')
    template = template.replace('@@CONNECTION@@', '')
    return template.replace('@@TITLE@@',esc('Review your career record')).replace('@@CHANGES@@',esc(f"{changes['added']} added · {changes['changed']} changed · {changes['removed']} proposed removals · {changes['unchanged']} unchanged")).replace('@@OVERVIEW@@',overview(state)).replace('@@STOPPING@@',stopping_point(state)).replace('@@GROUPS@@',groups).replace('@@CARDS@@',''.join(cards)).replace('@@OMISSIONS@@',omissions).replace('@@DATA@@',payload)


PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>@@TITLE@@</title>
<style>
:root{color-scheme:light;--ink:#19332d;--muted:#52665f;--line:#d8e1dc;--green:#205d4c}*{box-sizing:border-box}body{margin:0;background:#f5f5ef;color:var(--ink);font:16px/1.55 system-ui,sans-serif}main{max-width:1040px;margin:auto;padding:32px 24px calc(var(--navigation-height, 190px) + 24px)}h1{font:600 36px/1.15 Georgia,serif;margin:10px 0}h2{font-size:23px}h3{font-size:20px;margin:8px 0}p{max-width:80ch}.eyebrow{color:var(--green);text-transform:uppercase;letter-spacing:.12em;font-size:12px}.muted,.review-state{color:var(--muted);font-size:14px}.notice{background:#fff2cd;padding:12px;border-radius:6px}.toolbar{background:#f5f5eff5;padding:14px 0;border-bottom:1px solid var(--line);z-index:2;display:flex;flex-wrap:wrap;gap:10px;align-items:center}input,select,textarea,button{font:inherit;border:1px solid #a6b9ae;border-radius:6px;padding:9px;background:white;color:var(--ink)}textarea{width:100%;resize:vertical}label{display:block;font-size:14px;margin:12px 0}label select{display:block;width:100%;margin-top:5px}button{cursor:pointer}button.primary{background:var(--green);color:white}.card,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:24px;margin:18px 0}.tag{font-size:12px;text-transform:uppercase;color:var(--green);letter-spacing:.08em}dl{display:grid;grid-template-columns:minmax(100px,180px) 1fr;gap:8px 16px}dt{font-weight:600;font-size:14px}dd{margin:0;overflow-wrap:anywhere}dd dl{display:block}dd dt{margin-top:8px}ul{margin:0;padding-left:20px}details{border-top:1px solid var(--line);padding:12px 0}summary{cursor:pointer;color:var(--green)}blockquote{border-left:3px solid #b1cfc0;margin:12px 0;padding-left:15px;white-space:pre-wrap}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.decide{border-top:1px solid var(--line);margin-top:15px}.progress{font-weight:600}.pagination{display:flex;gap:12px;align-items:center;margin:18px 0}#save-status{min-height:25px}.toolbar>*{max-width:100%}input[type=search]{min-width:180px;flex:1}footer{font-size:13px;color:var(--muted)}[hidden]{display:none!important}:focus-visible{outline:3px solid #dca946;outline-offset:3px}.review-navigation{position:fixed;bottom:0;left:0;right:0;z-index:3;background:#fff;border-top:1px solid var(--line);box-shadow:0 -3px 12px #0001;padding:12px max(16px,calc((100vw - 992px)/2));padding-bottom:max(12px,env(safe-area-inset-bottom))}.batch-summary,.batch-controls{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}.batch-controls{margin-top:8px}.batch-controls label{margin:0}.batch-controls select{max-width:240px;min-width:0}.review-navigation #save-status{font-size:13px;min-height:0;margin:6px 0 0}.card header,#review-heading{scroll-margin-top:16px}button:disabled{opacity:.5;cursor:default}#career-overview{border:0;padding:0}details.panel>summary{font-weight:600} @media(max-width:650px){main{padding:20px 12px calc(var(--navigation-height, 240px) + 24px)}.batch-controls{display:grid;grid-template-columns:1fr 1fr;gap:6px}.batch-controls label{display:none}.batch-controls select{grid-column:1/-1;grid-row:1;max-width:none;width:100%}.batch-controls button,.batch-controls select{font-size:14px;padding:8px}.review-navigation{padding-top:8px}.batch-summary{font-size:14px}h1{font-size:30px}.card{padding:16px}dl{grid-template-columns:1fr}dd{margin-bottom:8px}}@media print{.toolbar,.decide,.pagination,.review-navigation,button{display:none}.card[hidden]{display:block!important}.card{break-inside:avoid}}
</style></head><body><main><span class="eyebrow">Your career · Private review</span><h1>Does this record reflect you?</h1><p>Check what was captured, compare it with your sources, and tell us what needs correcting or adding. You can pause at any time.</p><p><strong>@@CHANGES@@</strong></p><p class="notice">This private document includes confidential records and personal details. Keep it on your device. Nothing is sent from this page.</p>
<p><button id="start-review" class="primary">Continue review</button></p><details class="panel"><summary>View my career overview</summary>@@OVERVIEW@@</details><details class="panel" id="review-help"><summary>How review and saving work</summary><h2>Review at your own pace</h2><p>Start with the contributions that matter to you. You can correct one item, save your progress and return later. External-use choices can wait.</p><h3>What your choices mean</h3><p><strong>Looks accurate</strong> accepts the wording you can inspect here. It does not verify the claim independently or authorize external use. New or changed content stays private unless you separately allow it.</p><p><strong>Correct this</strong>, <strong>Not sure</strong> and <strong>Review later</strong> preserve your answer and keep the proposal pending. <strong>Keep private</strong> can restrict an existing item even while its correction is pending.</p><label>Your name<input id="reviewer" autocomplete="name" placeholder="Who reviewed these items?"></label><button id="preview-choices">Preview what will be saved</button><section id="choices-preview" aria-live="polite" hidden></section><button id="download" class="primary">Download review decisions</button> <button id="load">Resume from a saved decisions file</button><input type="file" id="load-file" accept="application/json,.json" hidden><p class="muted">Choices may be kept in this browser for this proposal. Download them to keep a portable copy. Return to the conversation and say: “Apply my saved review decisions and show me what remains.” Tell the tool where you saved the file; it handles the import and refreshes this page. Your pack changes only when accepted items are saved.</p></details>
<h2 id="review-heading" tabindex="-1">Review your record</h2><p>Sources and personal details are also reviewable in “All career sections”. New achievements need their role and source records accepted before they can be saved.</p><div class="toolbar"><select id="group" aria-label="Career section"><option value="">All career sections, including supporting details</option><option value="career">Career highlights</option>@@GROUPS@@</select><select id="change" aria-label="Changes"><option value="attention">Needs attention</option><option value="unfinished">Unanswered or deferred</option><option value="">All records</option><option value="added">Added</option><option value="changed">Changed</option><option value="removed">Proposed removals</option><option value="unchanged">Unchanged</option></select><input id="search" type="search" aria-label="Search your career" placeholder="Search a role, achievement or source"></div><div id="cards">@@CARDS@@</div><p id="empty-queue" role="status" hidden></p><nav class="review-navigation" aria-label="Review batches"><div class="batch-summary"><strong id="page" aria-live="polite"></strong><span id="progress" aria-live="polite"></span></div><div class="batch-controls"><button id="previous">Previous five</button><label for="batch-jump">Batch</label><select id="batch-jump" aria-label="Jump to batch"></select><button id="unfinished">Next unfinished</button><button id="next" class="primary">Save and next five</button><button id="pause-nav">Save and pause</button></div>@@CONNECTION@@<p id="save-status" role="status" aria-live="polite">Decisions stay in your browser until you download and apply them with the career tool.</p></nav>
<details class="panel"><summary>What have we missed? (optional)</summary><h2>What have we missed?</h2><p>An accurate list can still leave out your best work. These answers become follow-up notes, not automatic new achievements.</p>@@OMISSIONS@@</details>@@STOPPING@@<footer>Rendered directly from the recorded proposal and its previous version. A saved decision applies only to the exact reviewed content. Closing this page never accepts anything.</footer></main><script type="application/json" id="review-data">@@DATA@@</script><script>
@@NAVIGATION@@
</script></body></html>'''
