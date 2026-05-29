# Track C — Router tightening + LLM adapter

Internal implementation runbook. Delete after merge.

## Goals

1. Don't waste tokens — regex runs before AI, not after
2. Pluggable LLM (Anthropic, Groq, BYO) configurable per user
3. Two-tier model design — classifier and responder are independent
4. Personalization — inject user profile into prompts
5. Testable without API keys — stub adapter for the suite

Each stage below is self-contained. Execute in order. Run the
verification at the end of each stage before moving on. Do not
batch stages.

---

## Stage 0 — Verify assumptions

**Goal:** Confirm the schema and config state matches what this
plan assumes. Stop and ask if anything is off.

**Steps:**

1. Open `backend/SCHEMA.md`. Confirm the `users` table has columns
   `ai_mode` (boolean) and `anthropic_key` (text, "encrypted" per
   schema doc). If either is missing, stop and ask before continuing.
   **Verified 2026-05-29:** both present.
2. Open `backend/app/config.py`. Confirm `use_ai_agent` and
   `anthropic_api_key` settings exist. List any other AI-related
   settings already present.
3. Run `grep -rn "from app.ai_router" backend/` to find every
   importer of the current AI router. Expect: `router.py` and
   maybe tests. Anything else, flag it.

**Expected result:** Schema and config confirmed. List of
importers known.

---

## Stage 1 — Reorder router

**Goal:** Move AI classify from before the regex chain to after.
Smallest possible change; no new modules.

**Files affected:** `backend/app/router.py`

**Steps:**

1. In `route()`, locate the block:
   ```python
   intent = classify(message)
   if intent:
       try:
           result = _dispatch(intent, message, user)
           if result is not None:
               return result
       except Exception as e:
           warnings.warn(f"AI dispatch failed, falling back to regex: {e}")
   ```
   It currently sits between the confirm/cancel shortcuts and
   the regex chain (around line 139).
2. Move that block to immediately before the final
   `return _hint_for_message(message)` line.
3. Update the module docstring's "Routing order" comment to
   reflect: regex chain → AI classify → hint.

**Verification:**

```
cd backend && .venv/bin/pytest -xvs tests/test_ai_router.py
cd backend && .venv/bin/pytest
```

Some tests in `test_ai_router.py` may fail because they assert AI
runs before regex. For each failing test, update the assertion
to reflect the new order (regex first, AI second). Do not change
test intent — just the order assumption.

**Expected result:** All 337 tests pass.

---

## Stage 2 — Create LLM adapter module

**Goal:** Extract Anthropic-specific logic into a provider-agnostic
adapter. Add Groq and stub providers. Keep it one file.

**Files affected:**
- Create `backend/app/llm.py`
- Leave `backend/app/ai_router.py` alone for now (Stage 5 deletes it)

**Steps:**

1. Create `backend/app/llm.py` with this structure:

   ```python
   """LLM adapter — classify() and respond(). Provider-agnostic.

   Public API:
   - classify(message, user) -> dict | None
   - respond(prompt, user) -> str | None  (defined but not wired in Track C)
   """
   import json
   import warnings
   from app.config import settings

   _MAX_MESSAGE_LEN = 1000


   class _AnthropicProvider:
       def __init__(self, api_key: str, model: str):
           self.api_key = api_key
           self.model = model

       def complete(self, system: str, user: str, max_tokens: int, temperature: float) -> str | None:
           import anthropic
           client = anthropic.Anthropic(api_key=self.api_key)
           response = client.messages.create(
               model=self.model,
               max_tokens=max_tokens,
               temperature=temperature,
               system=system,
               messages=[{"role": "user", "content": user}],
           )
           if not response.content:
               return None
           return response.content[0].text.strip() or None


   class _GroqProvider:
       def __init__(self, api_key: str, model: str):
           self.api_key = api_key
           self.model = model

       def complete(self, system, user, max_tokens, temperature):
           import requests
           response = requests.post(
               "https://api.groq.com/openai/v1/chat/completions",
               headers={"Authorization": f"Bearer {self.api_key}"},
               json={
                   "model": self.model,
                   "max_tokens": max_tokens,
                   "temperature": temperature,
                   "messages": [
                       {"role": "system", "content": system},
                       {"role": "user", "content": user},
                   ],
               },
               timeout=30,
           )
           response.raise_for_status()
           data = response.json()
           if not data.get("choices"):
               return None
           return data["choices"][0]["message"]["content"].strip() or None


   class _StubProvider:
       """Returns canned responses keyed by message. Used in tests."""
       _registry: dict[str, str] = {}

       @classmethod
       def register(cls, message: str, response: str):
           cls._registry[message] = response

       @classmethod
       def clear(cls):
           cls._registry.clear()

       def __init__(self, api_key=None, model=None):
           pass

       def complete(self, system, user, max_tokens, temperature):
           return self._registry.get(user)
   ```

2. Add the provider factory:

   ```python
   def _provider_for(role: str, user: dict):
       """role is 'classifier' or 'responder'."""
       if role == "classifier":
           provider_name = settings.classifier_provider
           api_key = settings.classifier_api_key
           model = settings.classifier_model
       else:
           provider_name = settings.responder_provider
           api_key = settings.responder_api_key
           model = settings.responder_model

       if provider_name == "stub":
           return _StubProvider()
       if provider_name == "none" or not api_key:
           return None
       if provider_name == "anthropic":
           return _AnthropicProvider(api_key, model)
       if provider_name == "groq":
           return _GroqProvider(api_key, model)
       return None
   ```

3. Move the intent system prompt from `ai_router.py` into `llm.py`
   as a constant `_INTENT_SYSTEM_PROMPT` and the `_INTENTS` list.
   Add a helper:

   ```python
   def _parse_intent_json(raw: str) -> dict | None:
       if not raw:
           return None
       if raw.startswith("```"):
           raw = raw.split("```")[1].removeprefix("json").strip()
       try:
           result = json.loads(raw)
       except json.JSONDecodeError:
           return None
       if result.get("intent") not in _INTENTS:
           return None
       if result.get("intent") == "unknown":
           return None
       return result
   ```

4. Implement the public `classify()` and `respond()` functions:

   ```python
   def classify(message: str, user: dict) -> dict | None:
       if not _ai_enabled_for(user):
           return None
       if len(message) > _MAX_MESSAGE_LEN:
           return None
       provider = _provider_for("classifier", user)
       if provider is None:
           return None
       try:
           raw = provider.complete(
               system=_INTENT_SYSTEM_PROMPT,
               user=message,
               max_tokens=512,
               temperature=0,
           )
       except Exception as e:
           warnings.warn(f"LLM classify failed ({type(e).__name__}): {e!r}")
           return None
       return _parse_intent_json(raw)


   def respond(prompt: str, user: dict) -> str | None:
       """Not wired in Track C — defined for future conversational use."""
       if not _ai_enabled_for(user):
           return None
       provider = _provider_for("responder", user)
       if provider is None:
           return None
       try:
           return provider.complete(
               system="You are Cazuela, a friendly Spanish WhatsApp assistant.",
               user=prompt,
               max_tokens=512,
               temperature=0.3,
           )
       except Exception as e:
           warnings.warn(f"LLM respond failed ({type(e).__name__}): {e!r}")
           return None


   def _ai_enabled_for(user: dict) -> bool:
       if user.get("ai_mode") is False:
           return False
       return settings.classifier_provider != "none"
   ```

**Verification:**

```
cd backend && .venv/bin/pytest -xvs tests/test_ai_router.py
cd backend && .venv/bin/pytest
```

Nothing in the suite uses `llm.py` yet — these should still pass.

**Expected result:** All 337 tests pass. `llm.py` exists but is
unused.

---

## Stage 3 — Add config slots

**Goal:** Add new config fields with deprecated-alias behavior.
Old `USE_AI_AGENT` + `ANTHROPIC_API_KEY` continue to work.

**Files affected:** `backend/app/config.py`, `backend/.env.example`

**Steps:**

1. In `config.py`, add fields to the settings class:

   ```python
   router_provider: str = "anthropic"
   router_api_key: str | None = None
   router_model: str = "claude-haiku-4-5-20251001"

   chat_provider: str = "anthropic"
   chat_api_key: str | None = None
   chat_model: str = "claude-haiku-4-5-20251001"
   ```

   `router_*` is the cheap grunt model (Groq today) used for intent
   classification. `chat_*` is the better model (Haiku today) used
   for conversational replies.

2. Add a `model_post_init` (Pydantic v2) or equivalent to populate
   the new slots from the old ones if the new ones are unset:

   ```python
   def model_post_init(self, __context):
       if self.use_ai_agent and self.anthropic_api_key:
           if not self.router_api_key:
               self.router_api_key = self.anthropic_api_key
           if not self.chat_api_key:
               self.chat_api_key = self.anthropic_api_key
       if not self.use_ai_agent:
           if self.router_provider == "anthropic" and not self.router_api_key:
               self.router_provider = "none"
           if self.chat_provider == "anthropic" and not self.chat_api_key:
               self.chat_provider = "none"
   ```

   (Adjust to match the existing pydantic-settings idiom in this
   project. If unsure, read existing usage in `config.py` first.)

3. Update `backend/.env.example` to document the new fields with
   comments. Keep the old ones with a "deprecated, use X instead"
   note.

**Verification:**

```
cd backend && .venv/bin/pytest
```

**Expected result:** All tests pass. Old `.env` config still works.

---

## Stage 4 — User profile injection

**Goal:** Personalize prompts with the user's name, language, and
currency.

**Files affected:** `backend/app/llm.py`

**Steps:**

1. Add a helper to `llm.py`:

   ```python
   def _user_profile_prefix(user: dict) -> str:
       bits = []
       if user.get("name"):
           bits.append(f"User's name: {user['name']}")
       currency = user.get("currency") or "CLP"
       bits.append(f"Currency: {currency} (integer amounts only)")
       return "\n".join(bits)
   ```

2. In `classify()` and `respond()`, prepend the profile to the
   system prompt before calling `provider.complete()`:

   ```python
   system = _user_profile_prefix(user) + "\n\n" + _INTENT_SYSTEM_PROMPT
   ```

   (Same pattern for `respond()` with its own base prompt.)

**Verification:**

```
cd backend && .venv/bin/pytest
```

**Expected result:** All tests pass. No visible behavior change in
tests yet (the stub provider ignores prompts).

---

## Stage 5 — Wire dispatch to new LLM module

**Goal:** Replace `ai_router.classify` with `llm.classify`. Delete
`ai_router.py`.

**Files affected:**
- `backend/app/router.py`
- `backend/app/dispatch.py`
- Delete `backend/app/ai_router.py`

**Steps:**

1. In `router.py`, change:
   ```python
   from app.ai_router import classify
   ```
   to:
   ```python
   from app.llm import classify
   ```
2. Update the call site:
   ```python
   intent = classify(message)  # OLD
   intent = classify(message, user)  # NEW
   ```
3. In `dispatch.py`, check if `ai_router` is imported. If so,
   update similarly. If `classify` is only used in `router.py`,
   leave `dispatch.py` alone.
4. Delete `backend/app/ai_router.py`.

**Verification:**

```
cd backend && grep -rn "ai_router" backend/app/
cd backend && .venv/bin/pytest
```

The grep should return no results in `app/` (test files may still
have references — that's fine, Stage 6 handles them).

**Expected result:** All non-`ai_router` tests pass.
`tests/test_ai_router.py` likely fails because it imports the
deleted module — Stage 6 fixes this.

---

## Stage 6 — Update tests for stub provider

**Goal:** Replace API-dependent test setup with the stub provider.
Make tests deterministic and key-free.

**Files affected:**
- `backend/tests/test_ai_router.py` (rename to `test_llm.py`)
- `backend/tests/conftest.py`

**Steps:**

1. In `conftest.py`, after the existing `os.environ.setdefault`
   block, add:
   ```python
   os.environ.setdefault("CLASSIFIER_PROVIDER", "stub")
   os.environ.setdefault("RESPONDER_PROVIDER", "stub")
   ```
2. Rename `tests/test_ai_router.py` to `tests/test_llm.py`. Update:
   - `from app.ai_router import classify` →
     `from app.llm import classify, _StubProvider`
   - For each test that mocks the Anthropic client, replace the
     mock with `_StubProvider.register(input, json_output)` in a
     `setUp` / fixture. Clear with `_StubProvider.clear()` in
     teardown.
   - Tests that asserted "AI runs before regex" — flip to assert
     "regex runs before AI" if they still make sense; otherwise
     delete them.
3. Add a few new tests to `test_llm.py`:
   - `test_classify_returns_none_when_disabled` — user with
     `ai_mode=False` short-circuits
   - `test_classify_returns_none_when_no_provider` — provider
     config is "none"
   - `test_parse_intent_json_strips_markdown` — handles fenced JSON
   - `test_parse_intent_json_rejects_unknown_intent`
   - `test_user_profile_prefix_includes_name_and_currency`

**Verification:**

```
cd backend && .venv/bin/pytest -xvs tests/test_llm.py
cd backend && .venv/bin/pytest
```

**Expected result:** All tests pass. The full suite runs without
needing `ANTHROPIC_API_KEY`.

---

## Stage 7 — Backwards-compatibility smoke

**Goal:** Confirm a deployment using only the old env vars still
works.

**Steps:**

1. Create a temporary `backend/.env.legacy` (do not commit) with
   only the old fields set:
   ```
   USE_AI_AGENT=true
   ANTHROPIC_API_KEY=sk-fake-for-smoke-test
   SUPABASE_URL=https://fake.supabase.co
   SUPABASE_KEY=fake
   SESSION_SECRET=test-secret-that-is-long-enough-for-jwt-hs256
   META_SKIP_VALIDATION=true
   ```
2. Run:
   ```
   cd backend && env $(grep -v '^#' .env.legacy | xargs) python -c "from app.config import settings; print(settings.classifier_api_key, settings.classifier_provider, settings.responder_api_key, settings.responder_provider)"
   ```
3. Expected output: the fake key appears in both `classifier_api_key`
   and `responder_api_key`. Both providers say `anthropic`.
4. Delete `backend/.env.legacy`.

**Expected result:** Legacy config maps to the new slots correctly.

---

## Stage 8 — Final validation

**Goal:** Confirm the full system is healthy.

**Steps:**

1. `cd backend && .venv/bin/pytest` — all tests pass
2. `cd backend && .venv/bin/ruff check .` — clean
3. `grep -rn "from app.ai_router" backend/` — no results
4. `grep -rn "settings.use_ai_agent\|settings.anthropic_api_key" backend/app/` —
   only references in `config.py` (the deprecated-alias logic). No
   handler or router code should still reference these directly.
5. Update `CHANGELOG.md`:
   - Added: pluggable LLM adapter with Anthropic, Groq, and stub
     providers
   - Added: two-tier model config (classifier and responder)
   - Added: user profile injection into AI prompts
   - Changed: AI classification now runs as a fallback after regex,
     reducing token usage
   - Deprecated: `USE_AI_AGENT` and `ANTHROPIC_API_KEY` env vars
     (still work, prefer `CLASSIFIER_*` and `RESPONDER_*`)
6. Open a PR. Title: `feat(router): pluggable LLM adapter; regex-first dispatch`

**Expected result:** Clean diff, green CI, ready to merge.

---

## What's out of scope for Track C

- **Clarify MCP domain** for low-confidence ambiguous classification
- **Wiring `respond()` into the router** for conversational replies
- **Per-user provider selection UI** in the dashboard
- **Dashboard toggle for AI mode**

These are planned for a later track once Track C is in main.
