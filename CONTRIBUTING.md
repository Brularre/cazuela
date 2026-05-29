# Contributing to Cazuela

## Getting started

```bash
git clone https://github.com/your-username/cazuela.git
cd cazuela/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your credentials
```

Run the test suite:

```bash
cd backend && .venv/bin/pytest
```

## Code style

- **No inline comments** — code should speak for itself
- **Module docstrings required** on every handler in `backend/app/handlers/`
- **Plain CSS Modules** on the frontend — no Tailwind
- UI strings and WhatsApp messages are in **Spanish**; code and docs in **English**

## Submitting changes

1. Fork the repo and create a branch (`git checkout -b feat/my-feature`)
2. Keep PRs focused — one feature or fix per PR
3. Run tests before opening a PR (`cd backend && .venv/bin/pytest`)
4. Reference any related issue in the PR description

## Adding a new WhatsApp feature

Use the `handler-scaffold` skill if you have Claude Code set up — it reads
existing handlers and generates a matching module, router patterns, and tests.
Otherwise follow the structure in `backend/app/handlers/` and add patterns to
`backend/app/patterns.py`.

## Questions

Open a GitHub Discussion or issue — happy to help.
