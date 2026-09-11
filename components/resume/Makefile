.PHONY: check test records
check: compatibility records test
compatibility:
	@python3 scripts/check_components.py --require resume
records:
	@python3 scripts/validate_records.py
test:
	@python3 tests/test_editorial.py
