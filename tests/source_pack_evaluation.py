"""Bounded factual checks for fictional source-to-pack cases, not a prose judge.

Expectations stay outside the model workspace. Patterns allow paraphrases but
cannot prove entailment; reports include separate, unanswered human review prompts.
"""
from html.parser import HTMLParser
import json
from pathlib import Path
import re

FIXTURES = Path(__file__).resolve().parent / 'fixtures/source-to-pack'
SOURCE_CASES = {'source-' + p.name: p.name for p in sorted(FIXTURES.iterdir()) if (p/'expected.json').is_file()}


class ReviewStructure(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids, self.connected, self.targets = set(), [], set()
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if attrs.get('data-key'):
            self.targets.add(attrs['data-key'])
        if tag == 'button' and 'connected' in attrs.get('class', '').split():
            self.connected.append(attrs.get('data-target'))

    @property
    def readable(self):
        return {'career-overview', 'review-data', 'review-heading', 'pause'} <= self.ids and bool(self.targets)

    @property
    def has_connected_review(self):
        return self.readable and any(target in self.targets for target in self.connected)


def text(value):
    """Score claims, not copied source excerpts, IDs, or source filenames."""
    if isinstance(value, dict):
        return ' '.join(text(v) for k, v in value.items() if k not in
                        ('source_refs', 'source_records', 'metadata', 'id', 'employment_id', 'education_id'))
    if isinstance(value, list):
        return ' '.join(map(text, value))
    return '' if value is None else str(value)


def matches(pattern, value):
    return bool(re.search(pattern, value, re.I))


def affirmative_award(value):
    """Remove narrowly scoped denials, not whole records containing 'no'."""
    return re.sub(r'\b(?:no|without|not an?)\s+(?:professional\s+)?(?:certification|certificate|award)(?:\s+(?:was\s+)?(?:awarded|earned|granted))?\b',
                  '', value, flags=re.I)


def asserted_match(pattern, value):
    """A local explicit denial is not a positive claim. Never skip the record."""
    for match in re.finditer(pattern, value, re.I):
        prefix = value[max(0, match.start()-40):match.start()]
        if re.search(r'\b(?:not|never|without|no)\s+(?:an?\s+|the\s+)?$', prefix, re.I):
            continue
        return True
    return False


def evaluate(pack, case):
    expected = json.loads((FIXTURES / case / 'expected.json').read_text())
    result = []
    def check(name, passed):
        result.append({'check': name, 'passed': bool(passed)})
    roles = pack.get('employment', [])
    def role_value(role, key):
        return (role.get('employer_of_record') or role.get('employer')) if key == 'employer' else role.get(key)
    for index, wanted in enumerate(expected['roles']):
        check('role_chronology_' + str(index + 1), any(all(
            role_value(role, key) in value if isinstance(value, list) else str(role_value(role, key)).casefold() == str(value).casefold()
            for key, value in wanted.items()) for role in roles))
    check('no_extra_employers', all(role_value(role, 'employer') in {r['employer'] for r in expected['roles']} for role in roles))
    atoms = pack.get('evidence_atoms', [])
    for wanted in expected['claims']:
        # Match on the generated claim, excluding its quoted source. Copying a
        # whole source into source_refs cannot make an omitted fact pass.
        pool = atoms + (roles if wanted.get('allow_role_context') else [])
        candidates = [a for a in pool if matches(wanted['anchor'], text(a) if wanted.get('allow_role_context') else text({'title':a.get('title'), 'star':a.get('star')}))]
        representations = [re.sub(r'\s+', ' ', text({'title':a.get('title'), 'star':a.get('star')})).casefold() for a in candidates]
        # Equivalent split/merged claims need not use the fixture's record count.
        # Exact duplicated generated wording is still a detectable regression.
        check(wanted['name'] + '_present_once', bool(candidates) and len(representations) == len(set(representations)))
        for n, pattern in enumerate(wanted['patterns']):
            values = [text(a) if wanted.get('allow_role_context') else text({k:a.get(k) for k in ('title', 'star', 'metrics')}) for a in candidates]
            check(wanted['name'] + '_fact_' + str(n + 1), any(matches(pattern, value) for value in values))
        for n, pattern in enumerate(wanted.get('qualification_patterns', [])):
            check(wanted['name'] + '_scope_' + str(n + 1), any(matches(pattern, text(a)) for a in candidates))
        # A correct basis/constraint cannot repair an incompatible metric value.
        # These restrictions belong to a fictional case, not a universal prose rule.
        metric_values = [str(m.get('value', '')) if isinstance(m, dict) else str(m)
                         for a in candidates for m in a.get('metrics', [])]
        for n, pattern in enumerate(wanted.get('forbidden_metric_values', [])):
            check(wanted['name'] + '_metric_value_' + str(n + 1),
                  not any(asserted_match(pattern, value) for value in metric_values))
        check(wanted['name'] + '_role_link', bool(candidates) and all(any(r.get('employment_id') == a.get('employment_id') and
              r.get('title') == wanted['role_title'] for r in roles) for a in candidates))
    qualification = expected['qualification']
    entries = pack.get('education', []) + pack.get('publications', []) + atoms
    qualifying = [text(entry) for entry in entries if matches(qualification['anchor'], text(entry))]
    check('qualification_preserved', any(all(matches(pattern, entry) for pattern in qualification['patterns']) for entry in qualifying))
    check('qualification_date_preserved', any(entry.get('end') == qualification['end'] or
          (qualification.get('award_date_alternative') and (entry.get('start') == qualification['end'] or matches(r'awarded\s+' + qualification['end'], text(entry)))) for entry in pack.get('education', [])
          if matches(qualification['anchor'], text(entry))))
    # Test the asserted qualification/title, not a note explaining that no award was earned.
    awards = ' '.join(str(entry.get('qualification', '')) + ' ' + str(entry.get('title', '')) for entry in entries)
    if qualification.get('forbidden'):
        check('training_not_promoted_to_award', not matches(qualification['forbidden'], affirmative_award(awards)))
    claims = [text({k: v for k, v in entry.items() if k not in ('open_questions', 'constraints', 'limitations')})
              for entry in roles + atoms + pack.get('education', [])]
    for n, pattern in enumerate(expected['forbidden_claims']):
        check('no_unsupported_claim_' + str(n + 1), not any(asserted_match(pattern, claim) for claim in claims))
    if 'conflict' in expected:
        check('date_conflict_visible', all(matches(pattern, text(pack)) for pattern in expected['conflict']['patterns']))
    check('all_facts_private', all(entry.get('external_safe') is False for entry in roles + atoms + pack.get('education', [])))
    check('self_authored_sources_do_not_upgrade_confidence', all(entry.get('evidence_status') in ('self_asserted', 'unresolved', 'declined')
          for entry in roles + atoms + pack.get('education', [])))
    for n, pattern in enumerate(expected.get('representation_patterns', [])):
        check('presentation_preference_' + str(n+1), matches(pattern, text(pack)))
    for n, pattern in enumerate(expected.get('preference_patterns', [])):
        check('recorded_preference_' + str(n+1), matches(pattern, text(pack.get('positioning_preferences', []))))
    return result
