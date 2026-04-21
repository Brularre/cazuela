# Comparison benchmark

| Mode | Run | Scenario | Category | Iter | ms | rows |
|---|---:|:---:|---|---:|---:|---:|
| baseline-regex | 1 | single | otros | 0 | 0.0 | 1 |
| baseline-regex | 2 | single | otros | 0 | 0.0 | 1 |
| baseline-regex | 3 | single | otros | 0 | 0.0 | 1 |
| mcp-stub | 1 | single | comida | 1 | 0.3 | 1 |
| mcp-stub | 2 | single | comida | 1 | 0.0 | 1 |
| mcp-stub | 3 | single | comida | 1 | 0.0 | 1 |
| mcp-claude-t0 | 1 | single | comida | 1 | 0.5 | 1 |
| mcp-claude-t0 | 2 | single | comida | 1 | 0.3 | 1 |
| mcp-claude-t0 | 3 | single | comida | 1 | 0.2 | 1 |
| mcp-claude-t07 | 1 | single | comida | 1 | 0.2 | 1 |
| mcp-claude-t07 | 2 | single | comida | 1 | 0.2 | 1 |
| mcp-claude-t07 | 3 | single | hogar | 1 | 0.2 | 1 |
| baseline-regex | 1 | batch | otros | 0 | 0.0 | 1 |
| baseline-regex | 2 | batch | otros | 0 | 0.0 | 1 |
| baseline-regex | 3 | batch | otros | 0 | 0.0 | 1 |
| mcp-stub | 1 | batch | ['comida', 'otros', 'otros', 'otros'] | 3 | 0.1 | 4 |
| mcp-stub | 2 | batch | ['comida', 'otros', 'otros', 'otros'] | 3 | 0.1 | 4 |
| mcp-stub | 3 | batch | ['comida', 'otros', 'otros', 'otros'] | 3 | 0.1 | 4 |
| baseline-regex | 1 | recipe | 0 ingredientes | 0 | 0.0 | 1 |
| baseline-regex | 2 | recipe | 0 ingredientes | 0 | 0.0 | 1 |
| baseline-regex | 3 | recipe | 0 ingredientes | 0 | 0.0 | 1 |
| mcp-stub | 1 | recipe | 0 ingredientes | 1 | 0.0 | 1 |
| mcp-stub | 2 | recipe | 0 ingredientes | 1 | 0.0 | 1 |
| mcp-stub | 3 | recipe | 0 ingredientes | 1 | 0.0 | 1 |
| mcp-claude-t0 | 1 | recipe | 6 ingredientes | 1 | 0.2 | 7 |
| mcp-claude-t0 | 2 | recipe | 6 ingredientes | 1 | 0.2 | 7 |
| mcp-claude-t0 | 3 | recipe | 6 ingredientes | 1 | 0.2 | 7 |
