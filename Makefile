.PHONY: benchmark replay-check

benchmark:
	cd backend && .venv/bin/python scripts/run_comparison.py

replay-check:
	cd backend && \
	for f in fixtures/mcp_snapshots/expense_batch_*.json; do \
		.venv/bin/python replay.py "$$f" --mode stub --runs 2 \
			--expect-final-status confirmed \
			--request-actions 3 --expect-iteration-count 3; \
	done && \
	.venv/bin/python replay.py \
		fixtures/mcp_snapshots/reconciliation_batch.json \
		--mode stub --runs 2 \
		--expect-final-status confirmed \
		--request-actions 1 --expect-iteration-count 1 && \
	for f in \
		fixtures/mcp_snapshots/expense_comida.json \
		fixtures/mcp_snapshots/expense_empty_history.json \
		fixtures/mcp_snapshots/expense_with_category_map.json \
		fixtures/mcp_snapshots/expense_with_user_profile.json; do \
		.venv/bin/python replay.py "$$f" --mode stub --runs 2 \
			--expect-final-status confirmed \
			--request-actions 1 --expect-iteration-count 1; \
	done
