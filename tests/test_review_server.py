"""Exercise actual loopback saves against disposable fictional workspaces."""
import json
import os
import re
import select
import subprocess
import sys
import unittest
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import test_career_creation as creation
ROOT = creation.ROOT
from pack_review import fingerprint


class ReviewConnectionTests(unittest.TestCase):
    write = creation.CreationTests.write
    put = creation.CreationTests.put
    cli = creation.CreationTests.cli
    state = creation.CreationTests.state
    choices = creation.CreationTests.choices

    def setUp(self):
        creation.CreationTests.setUp(self)
        self.process = subprocess.Popen([sys.executable, '-B', str(ROOT/'scripts/career_core.py'), 'review', 'open',
                                        '--session', self.session], cwd=self.root,
                                       env={**os.environ, 'CAREER_WORKSPACE': str(self.root)},
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.close_server)
        ready, _, _ = select.select([self.process.stdout], [], [], 10)
        if not ready:
            self.fail('Local review did not start in ten seconds.')
        self.url = self.process.stdout.readline().strip()
        if not self.url.startswith('http://127.0.0.1:'):
            self.fail('Local review failed: ' + self.process.stderr.read())
        parsed = urlsplit(self.url)
        self.origin = parsed.scheme + '://' + parsed.netloc
        self.token = parsed.path.split('/')[-1]

    def tearDown(self):
        self.close_server()
        creation.CreationTests.tearDown(self)

    def close_server(self):
        if getattr(self, 'process', None):
            self.process.terminate()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=5)
            self.process.stdout.close(); self.process.stderr.close()
            self.process = None

    def get(self, suffix=''):
        with urlopen(self.url + suffix, timeout=10) as response:
            return response.read().decode()

    def page_data(self):
        return json.loads(re.search(r'<script type="application/json" id="review-data">(.*?)</script>', self.get(), re.S)[1])

    def post(self, action, value, origin=None, token=None):
        request = Request(self.url+'/'+action, data=json.dumps(value).encode(), headers={
            'Content-Type': 'application/json', 'Origin': origin or self.origin,
            'X-Career-Review': token or self.token})
        try:
            with urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def payload(self):
        return {'state_token': self.page_data()['connection']['state_token'],
                'decisions': self.choices({'employment/EMP_CURRENT': 'accept', 'evidence_atoms/E_STORY_1': 'accept'})}

    def test_save_updates_pack_and_reading_view(self):
        code, result = self.post('save', self.payload())
        self.assertEqual(code, 200, result)
        self.assertTrue(result['saved_pack'])
        self.assertIsNone(result['save_blocked'])
        self.assertIn('Saved to your career pack', result['message'])
        self.assertIn('Fictional Fieldwork', self.get('/reading'))
        self.assertEqual(len(list((self.root/'data/packs').glob('*.json'))), 1)

    def test_old_page_cannot_replay_a_save(self):
        request = self.payload()
        self.assertEqual(self.post('save', request)[0], 200)
        code, result = self.post('save', request)
        self.assertEqual(code, 409)
        self.assertIn('Reload', result['error'])
        self.assertEqual(len(list((self.root/'data/packs').glob('*.json'))), 1)

    def test_cross_origin_and_wrong_session_token_cannot_write(self):
        request = self.payload()
        self.assertEqual(self.post('save', request, origin='https://example.invalid')[0], 403)
        self.assertEqual(self.post('save', request, token='not-the-token')[0], 403)
        self.assertFalse(list((self.root/'data/packs').glob('*.json')))
        self.assertFalse(list((self.root/'reviews/pack-reviews/first/decisions').glob('*.json')))

    def test_corrected_wording_is_not_accepted_by_preview(self):
        request = {'state_token': self.page_data()['connection']['state_token'], 'decisions': self.choices({}),
                   'edits': [{'key': 'evidence_atoms/E_STORY_1', 'fingerprint': fingerprint('evidence_atoms/E_STORY_1', self.pack),
                              'fields': {'star.action': 'I co-designed the approach with the team.'}}]}
        code, result = self.post('correct', request)
        self.assertEqual(code, 200, result)
        self.assertTrue(result['reload'])
        self.assertFalse(list((self.root/'data/packs').glob('*.json')))
        data = self.page_data()
        row = next(r for r in data['items'] if r['key'] == 'evidence_atoms/E_STORY_1')
        self.assertIsNone(row['decision'])
        self.assertIn('I co-designed the approach', self.get())

    def test_connection_does_not_serve_source_files(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.origin+'/reviews/onboarding.md', timeout=5)
        self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
