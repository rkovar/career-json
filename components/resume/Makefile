.PHONY: check test records
check: compatibility records test
compatibility:
	@python3 scripts/check_components.py --require resume
records:
	@python3 scripts/validate_records.py
test:
	@python3 tests/test_resume_startup.py
	@python3 tests/test_editorial.py
	@python3 tests/test_source_pack_evaluation.py
	@python3 tests/test_resume_workflow.py
	@python3 tests/test_resume_markdown.py
	@python3 tests/test_resume_process.py
	@python3 tests/test_pdf_links.py
	@python3 tests/test_employer_layout.py
	@python3 tests/test_resume_quality.py

.PHONY: export-resume
export-resume:
	@python3 scripts/export_resume.py "$(ARTEFACT)" --plan "$(PLAN)" --output "$(EXPORT_DIR)"
