#!/usr/bin/env python3
"""The reading page is a projection of recorded facts, never raw-source extraction."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'scripts'))
import career_page
from career_profile import digest


class CareerPageTests(unittest.TestCase):
    def setUp(self):
        self.pack = json.loads((ROOT/'examples/career.example.json').read_text())

    def test_no_raw_sources_or_external_fonts_are_loaded(self):
        self.pack['publications'] = []
        self.pack['source_records'] = [
            {'source_id': 'SRC_PUBLICATIONS', 'path': '/must/not/read'},
            {'source_id': 'SRC_URL_SPLUNK_AUTHOR_1', 'saved_copy': '/must/not/read'}]
        with patch.object(Path, 'read_text', side_effect=AssertionError('raw source was read')):
            page = career_page.build(self.pack, 'data/packs/example.json')
        self.assertIn('No publication records saved', page)
        self.assertNotIn('fonts.googleapis', page)
        self.assertNotIn('splunk.com', page)

    def test_empty_and_independent_careers_render_without_invented_dates(self):
        self.pack['employment'] = []
        for atom in self.pack['evidence_atoms']:
            atom['employment_id'] = None
        page = career_page.build(self.pack, 'candidate.json')
        self.assertIn('Other recorded work', page)
        for atom in self.pack['evidence_atoms']:
            self.assertIn(atom['title'], page)
        self.assertNotIn(' yrs', page)

    def test_unknown_end_is_not_present_and_nested_positions_remain_visible(self):
        root = copy.deepcopy(self.pack['employment'][0])
        root.update(employment_id='EMP_ROOT', start='2020', end=None, parent_employment_id=None)
        child = dict(root, employment_id='EMP_CHILD', start='2021', title='Senior engineer', parent_employment_id='EMP_ROOT')
        grandchild = dict(root, employment_id='EMP_LATEST', start='2022', title='Principal engineer', parent_employment_id='EMP_CHILD')
        self.pack['employment'] = [root, child, grandchild]
        self.pack['evidence_atoms'][0]['employment_id'] = 'EMP_LATEST'
        page = career_page.build(self.pack, 'candidate.json')
        self.assertIn('end not recorded', page)
        self.assertNotIn(' – present', page)
        self.assertIn('Principal engineer', page)
        self.assertIn(self.pack['evidence_atoms'][0]['title'], page)

    def test_cycle_is_reported_instead_of_losing_roles(self):
        root = dict(self.pack['employment'][0], employment_id='EMP_ROOT', parent_employment_id='EMP_ROOT')
        self.pack['employment'] = [root]
        with self.assertRaisesRegex(ValueError, 'cycle'):
            career_page.build(self.pack, 'candidate.json')

    def test_publication_links_are_safe_and_titles_escaped(self):
        self.pack['publications'] = [{'publication_id':'PUB_ONE', 'kind':'article',
            'title':'<script>bad</script>', 'url':'javascript:alert(1)', 'evidence_status':'self_asserted',
            'external_safe':False}]
        page = career_page.build(self.pack, 'candidate.json')
        self.assertNotIn('href="javascript:', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('class="private"', page)

    def test_stale_strength_is_not_presented_as_confirmed(self):
        atom = self.pack['evidence_atoms'][0]
        self.pack['strengths_profile'] = [{'id':'S_JUDGEMENT', 'status':'confirmed',
            'interpretation':'Architectural judgement', 'basis':'single_achievement',
            'evidence_ids':[atom['id']], 'evidence_fingerprints':{atom['id']:digest(atom)}}]
        atom['star']['action'] += ' Changed support.'
        page = career_page.build(self.pack, 'candidate.json')
        self.assertIn('Stale', page)
        self.assertNotIn('>Confirmed<', page)

    def test_publication_caveats_and_sources_survive_readable_projection(self):
        pub = {'publication_id': 'PUB_ONE', 'kind': 'talk', 'title': 'Conference panel',
               'role': 'co_speaker', 'evidence_status': 'self_asserted', 'external_safe': False,
               'constraints': ['The card advertises a panel; attendance is not established.'],
               'notes': 'The two programmes name different collaborators.',
               'source_refs': [{'source_id': 'SRC_CARD', 'locator': 'Name strip', 'excerpt': '<Alex & colleagues>'}]}
        self.pack['publications'] = [pub]
        page = career_page.publications_html(self.pack)
        self.assertIn(pub['constraints'][0], page)
        self.assertIn(pub['notes'], page)
        self.assertIn('SRC_CARD', page)
        self.assertIn('Name strip', page)
        self.assertIn('&lt;Alex &amp; colleagues&gt;', page)
        self.assertIn('<details', page)
        self.assertNotIn('<Alex & colleagues>', page)

    def test_achievement_notes_are_available_without_loading_sources(self):
        atom = self.pack['evidence_atoms'][0]
        atom['notes'] = 'Retired wording: <obsolete claim>. See the original review.'
        page = career_page.atom_html(atom)
        self.assertIn('Retired wording: &lt;obsolete claim&gt;', page)


if __name__ == '__main__':
    unittest.main()
