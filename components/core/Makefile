.PHONY: help check validate excerpts test coverage questions strengths notes pack-html
help:
	@echo "Career Evidence Core (early access): check, validate, excerpts, test, coverage, questions, strengths, notes, pack-html"
check: compatibility validate excerpts test
compatibility:
	@python3 scripts/check_components.py
validate:
	@python3 scripts/validate_pack.py
excerpts:
	@python3 scripts/verify_excerpts.py --quiet
test:
	@python3 tests/test_core.py
	@python3 tests/test_pack_review.py
coverage:
	@python3 scripts/coverage.py
questions:
	@python3 scripts/open_questions.py --markdown
strengths:
	@python3 scripts/career_core.py status
notes:
	@python3 scripts/capture.py --list
pack-html:
	@python3 scripts/pack_html.py
