// The website has its own build dependencies; the career tools remain Python stdlib.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import MarkdownIt from 'markdown-it';
import {layout, home, start, demo, privacy, notFound, htmlEscape as escape} from './pages.mjs';

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const website = path.join(root, 'site');
export const output = path.join(root, 'dist/site');
export const slug = value => value.toLowerCase().replace(/[^\p{L}\p{N}_\- ]/gu, '').replaceAll(' ', '-');
const github = 'https://github.com/rkovar/career-json/blob/main/';
const allowed = /^(docs\/[^\\]+\.md|graphics\/(?:[^\\]+\.(?:svg|png))|examples\/first-pack\/[^\\]+\.(?:html|md|json|jsonl|txt))$/;

export function publicPath(name) {
  return typeof name === 'string' && allowed.test(name) && !name.split('/').some(p => !p || p === '.' || p === '..' || p.startsWith('.'));
}

export async function readPublic(name, base = root) {
  if (!publicPath(name)) throw Error('Not an allowed public website path: ' + name);
  let current = base;
  for (const part of name.split('/')) {
    current = path.join(current, part);
    if ((await fs.lstat(current)).isSymbolicLink()) throw Error('Website sources cannot be symlinks: ' + name);
  }
  return fs.readFile(current);
}

export function destination(name) {
  if (name === 'docs/README.md') return 'guides/index.html';
  if (name.startsWith('docs/')) return name.replace(/^docs\//, 'guides/').replace(/\.md$/, '.html');
  return name.replace(/\.md$/, '.html');
}

export function rewriteLink(href, source, published, tracked = new Set()) {
  // Public Markdown must work on GitHub as well as in the rendered site. Keep
  // its full website links in source, but resolve them locally in site builds
  // so starter downloads work on previews, Pages subpaths and custom domains.
  for (const base of ['https://career-json.com/', 'https://www.career-json.com/', 'https://rkovar.github.io/career-json/']) {
    if (href?.startsWith(base)) {
      const url = new URL(href);
      let target = url.pathname.slice(new URL(base).pathname.length);
      if (!target || target.endsWith('/')) target += 'index.html';
      return path.posix.relative(path.posix.dirname(destination(source)), target) + url.search + url.hash;
    }
  }
  if (!href || href.startsWith('#') || /^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(href)) return href;
  const resolved = new URL(href, 'https://source.invalid/' + source);
  const target = decodeURIComponent(resolved.pathname.slice(1));
  if (published.has(target)) {
    let relative = path.posix.relative(path.posix.dirname(destination(source)), destination(target));
    if (!relative) relative = path.posix.basename(destination(target));
    return relative + resolved.search + resolved.hash;
  }
  if (tracked.has(target)) return github + target.split('/').map(encodeURIComponent).join('/') + resolved.hash;
  return href;
}

export function renderer(source, published, tracked) {
  const md = new MarkdownIt({html: false, linkify: false, typographer: false});
  const seen = new Map();
  md.core.ruler.push('website-links-and-headings', state => {
    state.tokens.forEach((token, index) => {
      if (token.type === 'heading_open') {
        const inline = state.tokens[index + 1];
        const label = (inline.children || []).filter(t => !t.type.endsWith('_open') && !t.type.endsWith('_close')).map(t => t.content).join('');
        const base = slug(label), count = seen.get(base) || 0;
        token.attrSet('id', base + (count ? '-' + count : '')); seen.set(base, count + 1);
      }
      for (const child of token.children || []) {
        for (const attr of ['href', 'src']) {
          const value = child.attrGet(attr);
          if (value) child.attrSet(attr, rewriteLink(value, source, published, tracked));
        }
      }
    });
  });
  return md;
}

async function write(name, data) {
  const target = path.join(output, name);
  await fs.mkdir(path.dirname(target), {recursive: true});
  await fs.writeFile(target, data);
}

export async function build() {
  const names = JSON.parse(await fs.readFile(path.join(website, 'public-files.json'), 'utf8'));
  if (!Array.isArray(names) || new Set(names).size !== names.length || names.some(n => !publicPath(n))) throw Error('Invalid public-file manifest');
  const published = new Set(names);
  const tracked = new Set(execFileSync('git', ['ls-files', '-z'], {cwd: root, encoding: 'utf8'}).split('\0').filter(Boolean));
  // Read and verify all inputs before replacing the previous website build.
  const files = new Map();
  for (const name of names) files.set(name, await readPublic(name));
  if (!files.get('examples/first-pack/FICTIONAL_DEMO.txt')?.toString().toLowerCase().includes('fictional')) throw Error('Missing fictional demo declaration');
  const versions = {};
  for (const component of ['core','resume']) versions[component] = JSON.parse(await fs.readFile(path.join(root, 'components', component, 'component.json'), 'utf8')).version;
  const origin = new URL(process.env.SITE_URL || 'https://career-json.com');
  if (!['https:', 'http:'].includes(origin.protocol) || origin.username || origin.password || origin.search || origin.hash) throw Error('SITE_URL must be a public HTTP(S) base URL');
  const siteUrl = origin.href.replace(/\/$/, '');
  const pack = JSON.parse(files.get('examples/first-pack/data/packs/updated.json'));
  const context = {versions, siteUrl, pack};
  // Output is fixed to dist/site; refuse links that could redirect deletion/writes.
  for (const candidate of [path.dirname(output), output]) {
    try { if ((await fs.lstat(candidate)).isSymbolicLink()) throw Error('Website output cannot be a symlink'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  await fs.rm(output, {recursive: true, force: true});
  await fs.mkdir(output, {recursive: true});
  for (const name of ['style.css','site.js']) await write('assets/' + name, await fs.readFile(path.join(website, name)));
  for (const [name, content] of files) {
    if (name.endsWith('.md')) {
      const markdown = content.toString();
      const title = markdown.match(/^# (.+)$/m)?.[1] || path.basename(name, '.md');
      const html = renderer(name, published, tracked).render(markdown);
      const page = destination(name);
      await write(page, layout({page, title, description: 'career.json guide: ' + title, content: html, document: true, source: name, ...context}));
      if (name.startsWith('examples/')) await write(name, content); // Preserve source bytes and hashes for the fictional pack.
    } else if (name.endsWith('.html')) {
      const prefix = path.posix.relative(path.posix.dirname(name), '.') || '.';
      const banner = `<aside class="public-demo-banner" style="padding:12px 24px;background:#102a43;color:white;font:14px/1.5 system-ui;text-align:center"><a style="color:white" href="${prefix}/demo/">← career.json demo</a> · Fictional data. Browser choices do not update a real career pack. <a style="color:#9cdeef" href="${prefix}/start/">Build your own →</a></aside>`;
      let html = content.toString().replace(/\b(href|src)="([^"]+)"/g, (_, key, href) => `${key}="${escape(rewriteLink(href.replaceAll('&amp;', '&'), name, published, tracked))}"`);
      html = html.replace(/<body([^>]*)>/i, '<body$1>' + banner);
      html = html.replace(/<\/head>/i, `<link rel="icon" type="image/png" href="${prefix}/graphics/png/favicon-32.png"></head>`);
      await write(name, html);
    } else await write(name, content);
  }
  const pages = [
    ['index.html', 'Your career, structured. The right facet, selected.', 'Preserve your achievements, review the evidence and reuse your career record for every opportunity.', home(context)],
    ['start/index.html', 'Start your career pack', 'Choose your first career.json workflow: build a career pack or make a resume.', start(context)],
    ['demo/index.html', 'Explore a career you can review', 'Explore Jules Elm’s fictional career record, supporting sources and human review process.', demo(context)],
    ['privacy/index.html', 'Privacy and your career information', 'Understand what this public website does and how your personal career workspace stays separate.', privacy(context)],
    ['404.html', 'Page not found', 'Find the career.json guides or return to the homepage.', notFound(context)]
  ];
  for (const [page, title, description, content] of pages) await write(page, layout({page,title,description,content,...context}));
  // Package only explicit public component files, never the developer workspace.
  execFileSync('python3', [path.join(root, 'scripts/build_starter.py'), '--output-dir', path.join(output, 'downloads')], {cwd: root});
  const urls = ['','start/','demo/','guides/','privacy/'];
  await write('sitemap.xml', `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls.map(u => `<url><loc>${escape(siteUrl + '/' + u)}</loc></url>`).join('')}</urlset>`);
  await write('robots.txt', `User-agent: *\nAllow: /\nSitemap: ${siteUrl}/sitemap.xml\n`);
  await write('.nojekyll', '');
  await write('public-build.json', JSON.stringify({source_files: names, component_versions: versions}, null, 2) + '\n');
  console.log(`Built public website from ${names.length} explicitly listed files: ${output}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) await build();
