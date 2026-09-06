# Dependency-free: everything here is stdlib Python or shell.
.PHONY: help check validate records test render artifacts quantities entailment evals corroboration questions index pack-html excerpts links hooks clean

help:
	@echo "make check     - validate packs and run the test suite"
	@echo "make validate  - structural check on every live pack"
	@echo "make test      - regression suite"
	@echo "make render    - regenerate HTML from every Markdown draft in outputs/"
	@echo "make artifacts - validate every generated artefact against its pack"
	@echo "make records   - validate evaluation and screen records"
	@echo "make excerpts  - check every recorded excerpt against the source it cites"
	@echo "make quantities - magnitudes a draft claims that its evidence does not carry"
	@echo "make entailment - a cold model judges whether each bullet says more than its evidence (spends tokens)"
	@echo "make evals     - behavioural scenarios: run a skill for real and assert on what it did (spends tokens)"
	@echo "make corroboration - ranked list of evidence worth corroborating"
	@echo "make index     - regenerate outputs/INDEX.md"
	@echo "make fit       - score the pack against every role profile"
	@echo "make links     - confirmed and proposed requirement-to-evidence links per role"
	@echo "make notes     - capture notes awaiting promotion into the pack"
	@echo "make dupes     - near-duplicate atoms already in the pack"
	@echo "make coverage  - timeline, gaps, undated atoms, stale skills"
	@echo "make questions - outstanding questions, ranked by what answering unlocks"
	@echo "make pack-html - browsable private view of the whole pack"
	@echo "make resume-json - export a JSON Resume projection to outputs/resume.json"
	@echo "make verdicts  - record screen verdicts and show the trend"
	@echo "make hooks     - install the pre-commit hook"

check: validate records excerpts test

validate:
	@python3 scripts/validate_pack.py

records:
	@python3 scripts/validate_records.py

# The source-to-atom hop: re-extracts each cited file and fails on an excerpt
# the source does not contain. Exit 0 with no pack, so a clean checkout passes.
excerpts:
	@python3 scripts/verify_excerpts.py --quiet

test:
	@python3 tests/run_tests.py

corroboration:
	@python3 scripts/corroboration_plan.py --markdown

# review-evidence works this queue one question at a time; --delta afterwards
# shows how much of the movement rests on evidence citing nothing.
questions:
	@python3 scripts/open_questions.py --markdown

index:
	@python3 scripts/artifact_index.py

fit:
	@python3 scripts/role_fit.py --markdown

links:
	@python3 scripts/link_evidence.py --status

notes:
	@python3 scripts/capture.py --list

dupes:
	@python3 scripts/dedupe.py

coverage:
	@python3 scripts/coverage.py

# Private working view: includes withheld atoms. outputs/ is gitignored.
pack-html:
	@python3 scripts/pack_html.py

resume-json:
	@python3 scripts/export_resume_json.py -o outputs/resume.json

verdicts:
	@python3 scripts/verdict_log.py && python3 scripts/verdict_log.py --trend

hooks:
	@git config core.hooksPath .githooks && echo "pre-commit hook installed (.githooks)"

# INDEX.md, screens, and private briefs are not artefacts.
ARTEFACTS = $(filter-out outputs/INDEX.md,$(wildcard outputs/*-draft.md outputs/*-cover-letter.md))

render:
	@for f in $(ARTEFACTS); do \
		python3 scripts/render.py "$$f" >/dev/null && echo "rendered $$f"; \
	done

# Reporting only, and deliberately not part of `make check`. The risk in this
# check is noise teaching generation to delete the number rather than go back to
# the atom, so its rate gets measured before it is allowed to block anything.
quantities:
	@for f in $(ARTEFACTS); do \
		python3 scripts/quantities.py "$$f" || true; \
	done

# Both spend tokens through the Claude Code CLI and are never part of `make check`.
entailment:
	@for f in $(ARTEFACTS); do \
		python3 scripts/entailment.py "$$f" || true; \
	done

evals:
	@python3 tests/run_scenarios.py

artifacts:
	@for f in $(ARTEFACTS); do \
		python3 scripts/validate_artifact.py "$$f" || true; \
	done
	@for f in $(wildcard outputs/*-interview-brief.md); do \
		python3 scripts/validate_artifact.py --private "$$f" || true; \
	done
