"""Offline reading guide for the fictional Jules example; no review logic here."""
from html import escape


def landing(summaries, recalled):
    cards = [
        ('1. Inspect the proposal', 'review.html', 'Four roles, twelve proposed achievements and four sources. Look for shared ownership, duplicate accounts and unsupported numbers.'),
        ('2. See a partial save', 'after-review.html', 'Nine achievements are accepted. Corrections, the uncertain metric and strengths questions remain pending.'),
        ('3. Review corrected wording', 'correction-review.html', 'Compare the coaching correction and combined dashboard account with the earlier sources. New wording needs a new decision.'),
        ('4. See the corrected record', 'corrected-career.html', 'Ten achievements and one confirmed interpretation, with original review history retained.'),
        ('5. Add new work later', 'update-review.html', 'A quick migration note becomes a proposed achievement after a follow-up account. The launch has not happened yet.'),
        ('6. Read the current career pack', 'career.html', 'Eleven accepted achievements across sixteen years. Private material and an open coaching question remain visible in this private reading view.'),
    ]
    steps = ''.join(f'<article><h3><a href="{url}">{title}</a></h3><p>{text}</p></article>' for title, url, text in cards)
    cases = [
        ('Peer review ownership', 'The initial proposal credits Jules with designing the entire review format and coaching every engineer.',
         'The manager review and Jules’s clarification identify Mara and Theo as the format designers. Jules sponsored the pilot and coached three managers.'),
        ('Two accounts of one dashboard', 'The resume uses two names for the March 2016 dashboard. Both appear as proposed achievements.',
         'The correction keeps one achievement, attaches both accounts and preserves the five-service adoption detail. It does not double-count delivery.'),
        ('A tempting 35% claim', 'Project notes mention a 35% improvement, but the baseline and measurement period are missing.',
         'The claim stays unresolved and outside every accepted pack. The original source and pending question remain available.'),
        ('Sensitive work', 'The supplier review demonstrates useful technical judgment, but includes employer-sensitive context.',
         'It is accepted as accurate and explicitly kept private. Accuracy and external-use permission are separate decisions.'),
        ('Strength versus overstatement', 'Practical adoption appears repeatedly; enterprise-scale transformation is also proposed.',
         'Jules confirms the narrower interpretation in a recorded answer. The enterprise claim remains a correction request; a leadership title does not establish it.'),
        ('A note is not a finished outcome', 'Jules records migration planning in August 2026.',
         'Capture leaves the accepted pack unchanged. Later review accepts planning and agreement, without inventing a successful launch or reduced incidents.'),
    ]
    case_html = ''.join(f'<article><h3>{title}</h3><p>{question}</p><details><summary>See the scripted review outcome</summary><p>{answer}</p></details></article>' for title, question, answer in cases)
    use_cases = [
        ('Prepare an annual review', 'What did I contribute to developing other engineers?', 'coaching'),
        ('Prepare for a Staff Engineer interview', 'Show the service-separation decision and who delivered it.', 'architecture'),
        ('Update the latest review', 'What can I accurately say about the customer-data migration?', 'migration'),
    ]
    uses = []
    for title, question, key in use_cases:
        records = []
        for item in recalled[key]:
            sources = ''.join(f'<blockquote>{escape(r["excerpt"])}</blockquote>' for r in item['source_refs'])
            records.append(f'<h4>{escape(item["title"])}</h4><p><strong>Contribution:</strong> {escape(item["star"]["action"])}</p>'
                           f'<p><strong>Recorded result:</strong> {escape(item["star"]["result"])}</p>'
                           f'<details><summary>Original supporting excerpts</summary>{sources}</details>')
        uses.append(f'<article><h3>{title}</h3><p class="question">“{question}”</p>{"".join(records)}</article>')
    count = summaries['initial']['saved_achievements']
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jules Elm — a career you can review</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f5f1;color:#1d3038;font:17px/1.6 system-ui,sans-serif}
main{max-width:1060px;margin:auto;padding:36px 24px 64px}h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.15;max-width:18ch}
h2{margin-top:48px;font-size:1.65rem}h3{font-size:1.1rem;margin-top:0}h4{margin-bottom:8px}p{max-width:76ch}
a{color:#075b64;text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid #a96c13;outline-offset:5px}
.label{font-size:.8rem;letter-spacing:.08em;font-weight:700;text-transform:uppercase}.intro{font-size:1.2rem}
.notice{border-left:4px solid #b47e29;padding:10px 16px;background:#fff1d7}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:18px}
article{border:1px solid #d6dddd;border-radius:10px;background:white;padding:22px;min-width:0}article p:last-child{margin-bottom:0}
.buttons{display:flex;gap:12px;flex-wrap:wrap;margin:26px 0}.button{padding:10px 16px;border:1px solid #075b64;border-radius:6px;text-decoration:none;font-weight:650}
.primary{background:#075b64;color:white}.timeline{padding-left:24px}.timeline li{padding:0 0 18px 8px}.timeline strong{display:block}
details{margin-top:16px}summary{cursor:pointer;color:#075b64;font-weight:600}blockquote{margin:14px 0;padding:8px 16px;border-left:3px solid #aabfc1;color:#40545b}
.question{font-style:italic}code{overflow-wrap:anywhere}footer{margin-top:48px;border-top:1px solid #d6dddd;padding-top:18px;font-size:.9rem}
@media(max-width:480px){main{padding:24px 16px}article{padding:18px}.button{width:100%;text-align:center}}
</style></head><body><main>
<p class="label">career.json / fictional walkthrough</p><h1>A career you can actually review</h1>
<p class="intro">Meet Jules Elm: a software engineer who grew into technical leadership, with useful older work, shared achievements and a few claims that need a second look.</p>
<p class="notice"><strong>Entirely fictional.</strong> People, employers, sources, answers and decisions are authored examples. The pages use the real review and recall tools; they do not measure model extraction accuracy or represent a real person’s approval.</p>
<nav class="buttons" aria-label="Start exploring"><a class="button primary" href="career.html">Read Jules’s current career pack</a><a class="button" href="review.html">Try reviewing the initial proposal</a><a class="button" href="#review-stages">Follow the stages</a></nav>
<h2>Who is Jules?</h2><p>Jules works at the intersection of software architecture, service operations and engineering development. The current remit is 18 engineers through three managers. The recurring contribution is helping teams adopt workable approaches, while leaving implementation credit with the people who did the work.</p>
<ol class="timeline"><li><strong>2010–2014 · Software Engineer · Fictional Civic Atlas</strong>Data imports, recovery tools and learning how operators use software.</li>
<li><strong>2014–2017 · Senior Software Engineer · Fictional North Quay Systems</strong>Shared observability and incident practice across service teams.</li>
<li><strong>2018–June 2022 · Staff Engineer · Fictional Fieldwork Ltd</strong>Deployment practice, service architecture and influence without line authority.</li>
<li><strong>July 2022–present · Head of Engineering · Fictional Fieldwork Ltd</strong>A promotion at the same employer: planning capacity, developing managers and making technical tradeoffs explicit.</li></ol>
<p>The sources do not establish revenue impact, enterprise-wide transformation or an outage-reduction percentage. A useful career record keeps those limits alongside the achievements.</p>
<h2 id="review-stages">Follow the review</h2><p>Start anywhere. Each page is a separate snapshot, so your experiments with one review do not change the others. ''' + str(count) + ''' achievements can be saved while other questions remain open.</p>
<div class="grid">''' + steps + '''</div>
<h2>Six things worth reviewing critically</h2><p>Try the initial proposal before opening the scripted outcomes. Expand supporting excerpts in each review card when you need more context. The review uses five items per batch; you can jump, defer or pause.</p>
<div class="grid">''' + case_html + '''</div>
<h2>Use the same career record in different situations</h2><p>These excerpts come from actual deterministic searches of the final accepted pack. They are private preparation examples, not completed resumes.</p>
<div class="grid">''' + ''.join(uses) + '''</div>
<p>For a leadership resume, Jules could ask to emphasize manager coaching and adoption planning. For an architecture role, the service-separation and deployment examples may matter more. External permissions still need review: this example only explicitly allows the shared talk and its Staff Engineer role externally.</p>
<h2>See the source material</h2><ul><li><a href="data/sources/resume.md">Career resume</a></li><li><a href="data/sources/manager-review-2025.md">Manager review: shared ownership</a></li><li><a href="data/sources/project-notes.md">Project notes: duplicate account and missing metric baseline</a></li><li><a href="data/sources/conference-programme.md">Conference programme: co-presenter credit</a></li><li><a href="data/sources/review-answers.md">Jules’s scripted correction and strengths answers</a></li><li><a href="data/sources/captured-note.json">Quick note before review</a></li><li><a href="data/sources/update-2026.md">Later migration-planning account</a></li></ul>
<h2>What stays unfinished?</h2><p>The 35% estimate is still pending. The value of Jules’s coaching needs feedback from the engineers. Cross-team tradeoffs remain a proposed strength; the enterprise-scale wording needs correction. Sensitive supplier work stays private. None of these prevents Jules from retrieving the accepted record.</p>
<footer><p>Open this folder locally; no server is needed. Browser choices affect only that browser until you download and apply them with the tool. Keep the whole folder to inspect its linked sources and history. <a href="README.md">Walkthrough and regeneration instructions</a>.</p></footer>
</main></body></html>'''
