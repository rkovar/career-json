# Publish the project website

The public website is a static companion to the local career tools. It includes
the product pages, Markdown guides, Jules's fictional example, and a downloadable
career starter.
Personal career creation runs in a local folder through Claude Code, either the
CLI or the Desktop Code tab. The website does not accept personal uploads.

## Build and preview

Website development needs Node.js 22+ and Python 3.9+. These are website build
tools; using Career Core does not require Node.js. The one direct npm dependency,
`markdown-it`, renders the existing Markdown guides during the build. It is not
loaded in visitors' browsers.

```sh
npm ci --prefix site --ignore-scripts
npm run check --prefix site
npm run preview --prefix site
```

Open `http://127.0.0.1:8000`. The build writes only `dist/site/`. It replaces that
generated directory on each build. The source remains in `site/`, `docs/`,
`graphics/` and `examples/first-pack/`. The starter is assembled from the public
component manifests and `components/starter/START-HERE.html`.

`site/public-files.json` explicitly lists every repository document, graphic and
fictional example included in the site. Add new public guides to that manifest.
The build rejects paths outside those public roots, path traversal and symlinks.
It preserves the fictional source files and JSON byte-for-byte, alongside rendered
HTML reading pages. Tests check links, source boundaries and Markdown rendering.

The build also writes `downloads/career-json-starter.zip`. `scripts/build_starter.py`
combines the Core and Resume release archives under a single `My Career/` folder,
retaining their file inventories and adding a combined checksum inventory. It
never walks a personal workspace. The archive includes local instructions;
`Help me start my career notebook` routes Claude to the Desktop setup workflow.
The website checker audits the download's paths, file inventory and checksums.

`tests/test_starter.py` extracts that actual archive into an empty folder and
exercises preparation, explicit review, a private save, source verification,
retrieval in a new process and a repeat setup. It removes developer tools from
PATH for these calls. It also checks damaged downloads and prevents setup from
following a personal-directory symlink outside the workspace. These checks run
with `npm run check --prefix site` and make no model calls.

With Chrome/Chromium installed, run `node site/browser.test.mjs` after building
for desktop/mobile navigation, the starter download and copy message, offline
instructions, keyboard tabs and browser error checks. Set
`CAREER_BROWSER` for a nonstandard browser path. `CAREER_SITE_SCREENSHOTS` optionally
names a directory for preview screenshots. These checks use a temporary local
server and browser profile and make no model calls.

No personal `data/`, `reviews/`, `outputs/` or backups are published. The workflow
uploads only `dist/site/`, not the checkout. The existing career release manifests
do not package the website or its npm dependency.

## GitHub Pages

The `.github/workflows/pages.yml` workflow builds and checks the website on relevant
pull requests and pushes. Only a push to `main` or a manual run from `main` can
deploy. Enable **Settings → Pages → Build and deployment → GitHub Actions**.
The default address is `https://rkovar.github.io/career-json/`.

The workflow uses GitHub's Pages deployment identity; no Namecheap password or
deployment token is stored in this repository. Its deployment job has only the
Pages and identity permissions it needs. It uses pinned official action revisions.

`SITE_URL` sets canonical links and the sitemap. The deployment workflow takes it
from GitHub Pages configuration, so both the project address and a custom domain
work. Local builds default to `https://career-json.com`. Navigation uses relative
links so local previews and project subpaths work too. During the build, links
from public Markdown to the project website are also made relative, including
the starter download route. The Markdown source keeps its full website URLs
so the same guide remains usable when read on GitHub.

## Connect career-json.com

Confirm the registration is active and which provider serves the domain's DNS.
If Namecheap uses BasicDNS, PremiumDNS or FreeDNS, edit **Domain List → Manage →
Advanced DNS → Host Records**. If it uses hosting nameservers, edit records in
the hosting DNS zone instead.

First verify ownership in the GitHub account's **Settings → Pages**, following
the TXT-record instructions GitHub provides. Then set `career-json.com` as the
repository's custom domain in **Settings → Pages**, before pointing DNS at Pages.

Set these records for the website:

| Type | Host | Value |
| --- | --- | --- |
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `rkovar.github.io` |

Replace conflicting website A/AAAA/CNAME/redirect records for those hosts. Keep
unrelated records, including email MX and verification TXT records. Do not include
the repository name in the `www` CNAME target. DNS changes can take up to 24 hours.

After GitHub's DNS and certificate checks succeed, enable **Enforce HTTPS**.
Run the website workflow again so canonical URLs reflect the custom domain.
Check both `https://career-json.com` and `https://www.career-json.com`, including
the demo, a guide and a source link. Changing Pages to a custom domain redirects
the project address, so coordinate that change with the DNS setup.

GitHub Actions deployments use the domain setting in Pages; adding a `CNAME` file
alone does not configure it. The site remains usable at its GitHub project address
until the custom domain is configured.

See the official [GitHub custom-domain guide](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
and [Namecheap connection instructions](https://www.namecheap.com/support/knowledgebase/article.aspx/9645/2208/how-do-i-link-my-domain-to-github-pages/).
