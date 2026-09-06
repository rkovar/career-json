# Dependency-free: everything here is stdlib Python or shell.
.PHONY: help check validate records test render artifacts corroboration index hooks clean

help:
	@echo "make check     - validate packs and run the test suite"
	@echo "make validate  - structural check on every live pack"
	@echo "make test      - regression suite"
	@echo "make render    - regenerate HTML from every Markdown draft in outputs/"
	@echo "make artifacts - validate every generated artefact against its pack"
	@echo "make records   - validate evaluation and screen records"
	@echo "make corroboration - ranked list of evidence worth corroborating"
	@echo "make index     - regenerate outputs/INDEX.md"
	@echo "make fit       - score the pack against every role profile"
	@echo "make notes     - capture notes awaiting promotion into the pack"
	@echo "make dupes     - near-duplicate atoms already in the pack"
	@echo "make coverage  - timeline, gaps, undated atoms, stale skills"
	@echo "make resume-json - export a JSON Resume projection to outputs/resume.json"
	@echo "make verdicts  - record screen verdicts and show the trend"
	@echo "make hooks     - install the pre-commit hook"

check: validate records test

validate:
	@python3 scripts/validate_pack.py

records:
	@python3 scripts/validate_records.py

test:
	@python3 tests/run_tests.py

corroboration:
	@python3 scripts/corroboration_plan.py --markdown

index:
	@python3 scripts/artifact_index.py

fit:
	@python3 scripts/role_fit.py --markdown

notes:
	@python3 scripts/capture.py --list

dupes:
	@python3 scripts/dedupe.py

coverage:
	@python3 scripts/coverage.py

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

artifacts:
	@for f in $(ARTEFACTS); do \
		python3 scripts/validate_artifact.py "$$f" || true; \
	done
	@for f in $(wildcard outputs/*-interview-brief.md); do \
		python3 scripts/validate_artifact.py --private "$$f" || true; \
	done
