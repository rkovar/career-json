# Resume Application release notes

## 0.1.0-beta.3 — local release candidate, 2026-09-11

- Requires career-core 0.1.0-alpha.3. Resume generation remains optional after first-pack onboarding.

## 0.1.0-beta.2 — local release candidate, 2026-09-09

- Requires career-core 0.1.0-alpha.2, including staged human review.
- Resume generation continues reading the accepted pack; pending proposals and
  review notes do not become resume facts.

## 0.1.0-beta.1 — local release candidate, 2026-09-09

- First separately packaged beta add-on; requires career-core 0.1.0-alpha.1.
- Owns role targeting, briefs, ranked selections, scoped editorial decisions,
  document generation, reviews, rendering and public JSON Resume projection.
- Uses shared career schema 1.3/1.4 and core primitives. Existing command paths
  and editorial core-command forwarding remain compatible.
- Installs without replacing core files or bringing private workspace data.
- Thirty-five editorial tests pass in a fresh core-plus-add-on installation.
- Writing quality still requires semantic review; professionally reviewed
  cross-career benchmarks and requested PDF checks remain promotion gates.

See `docs/releases.md` for compatibility, installation and release gates.
