import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {publicPath, readPublic, rewriteLink, renderer, destination} from './build.mjs';

test('publishing rejects personal paths, traversal and hidden workspace files', () => {
  for (const name of ['data/packs/accepted.json','outputs/career.html','reviews/answers.json','backups/career.zip','.git/config','site/node_modules/a.js','docs/../data/person.md','/docs/a.md','docs//a.md','examples/first-pack/.private.json','docs\\secrets.md']) {
    assert.equal(publicPath(name), false, name);
  }
  assert.equal(publicPath('examples/first-pack/data/packs/updated.json'), true);
  assert.equal(publicPath('docs/operators/first-pack.md'), true);
});

test('a listed file or parent symlink cannot publish outside content', async () => {
  const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'career-site-boundary-'));
  try {
    await fs.mkdir(path.join(temp, 'docs'));
    await fs.writeFile(path.join(temp, 'private.md'), 'private sentinel');
    await fs.symlink('../private.md', path.join(temp, 'docs', 'leak.md'));
    await assert.rejects(readPublic('docs/leak.md', temp), /symlinks/);
    await fs.symlink('..', path.join(temp, 'docs', 'outside'));
    await assert.rejects(readPublic('docs/outside/private.md', temp), /symlinks/);
    await fs.writeFile(path.join(temp, 'docs', 'guide.md'), 'public guide');
    assert.equal((await readPublic('docs/guide.md', temp)).toString(), 'public guide');
  } finally { await fs.rm(temp, {recursive: true, force: true}); }
});

test('guide and source links follow their rendered destinations', () => {
  const files = new Set(['docs/README.md','docs/getting-started.md','docs/operators/first-pack.md','examples/first-pack/README.md','examples/first-pack/data/sources/resume.md']);
  assert.equal(destination('docs/README.md'), 'guides/index.html');
  assert.equal(rewriteLink('../README.md#your-career', 'docs/operators/first-pack.md', files), '../index.html#your-career');
  assert.equal(rewriteLink('../examples/first-pack/README.md', 'docs/getting-started.md', files), '../examples/first-pack/README.html');
  assert.equal(rewriteLink('data/sources/resume.md', 'examples/first-pack/review.html', files), 'data/sources/resume.html');
  assert.equal(rewriteLink('#local', 'docs/README.md', files), '#local');
  assert.equal(rewriteLink('https://example.com/a.md?q=x', 'docs/README.md', files), 'https://example.com/a.md?q=x');
  assert.equal(rewriteLink('../scripts/start.py', 'docs/README.md', files, new Set(['scripts/start.py'])), 'https://github.com/rkovar/career-json/blob/main/scripts/start.py');
});

test('Markdown retains tables, nested lists, code, links and stable heading anchors', () => {
  const md = renderer('docs/README.md', new Set(['docs/README.md','docs/getting-started.md']), new Set());
  const html = md.render('# A `saved` record\n\n## Return & review\n\n## Return & review\n\n- Parent\n  - Child\n\n| Claim | Source |\n| --- | --- |\n| Work | [Guide](getting-started.md) |\n\n```sh\nmake start\n```\n\n<script>alert(1)</script>');
  assert.match(html, /id="a-saved-record"/);
  assert.match(html, /id="return--review-1"/);
  assert.match(html, /<table>/);
  assert.match(html, /<ul>[\s\S]*<ul>/);
  assert.match(html, /href="getting-started.html"/);
  assert.match(html, /<code class="language-sh">make start/);
  assert.doesNotMatch(html, /<script>/);
});
