.PHONY: benchmark

benchmark:
	cd backend && .venv/bin/python scripts/run_comparison.py
