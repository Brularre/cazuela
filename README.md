# Cazuela

A personal life assistant accessible via WhatsApp.
Send natural language messages in Spanish — Cazuela logs
expenses, tracks todos, manages your pantry, plans meals,
and more.

No app to install. Just save the number and start messaging.

Includes MCP benchmark results and full agent iteration log.

## Features

- **Expenses:** `gasté 5000 en almuerzo` — logs with
  auto-detected category
- **Ambiguous expenses:** `pagué 3000` — AI proposes
  category, you confirm via MCP staging flow
- **Batch expenses:** `gasté 18000 en supermercado: pan,
  leche, queso` — splits and categorizes each item
- **Weekly summary:** `resumen`
- **Todos:** `pendiente: llamar al banco` /
  `mis pendientes` / `listo: banco`
- **Waiting on:** `esperando: respuesta del seguro` /
  `mis esperas` / `llegó: seguro`
- **Shopping list:** `comprar: leche` / `compras` /
  `compré leche`
- **Pantry:** `despensa cocina: arroz 3` / `mi despensa` /
  `usé: jabón` / `compré todo`
- **Recipes:** `nueva receta: cazuela` (AI suggests
  ingredients if enabled) / `mis recetas` /
  `receta: cazuela`
- **Help:** `ayuda` — shows all available commands

## Dashboard

A Next.js dashboard at `localhost:3000` shows expenses,
budget bar, todos, pantry, shopping list, recipes, and
weekly meal planner. Auth via WhatsApp OTP + session
cookie.

## Tech Stack

- **Backend:** Python + FastAPI, deployed on Railway
- **Frontend:** Next.js, deployed on Railway
- **AI:** Claude Haiku (optional; requires
  `USE_AI_AGENT=true` + `ANTHROPIC_API_KEY`)
- **MCP:** Internal propose→confirm/rollback context
  staging module (`backend/app/mcp/`)
- **Database:** Supabase (managed Postgres)
- **WhatsApp:** Meta WhatsApp Cloud API (graph.facebook.com v19.0)

---

## Running Locally

### 1. Clone and set up the backend

Requires **Python 3.10+** (the code uses `X | None` syntax).

```bash
git clone https://github.com/Brularre/cazuela.git
cd cazuela/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your-service-role-key
META_APP_SECRET=your-meta-app-secret
META_PHONE_NUMBER_ID=your-phone-number-id
META_ACCESS_TOKEN=your-access-token
META_WEBHOOK_VERIFY_TOKEN=any-random-string
SESSION_SECRET=         # generate with: openssl rand -hex 32

# Optional — enables AI categorization and recipe suggestions
USE_AI_AGENT=true
ANTHROPIC_API_KEY=your-anthropic-key
```

### 3. Set up Supabase

Create a new Supabase project, open the SQL editor, and run
`backend/migrations/00_bootstrap.sql`. That single file creates
every table the app needs.

(The other `.sql` files in that folder are the historical
per-feature migrations from this project's deploy — you do not
need to run them on a fresh project.)

### 4. Create your first user

The app only sends OTPs to phone numbers that already exist in
the `users` table. To log yourself in for the first time, insert
a row in Supabase (SQL editor):

```sql
insert into users (phone, name) values ('+56912345678', 'Tu nombre');
```

Use the same phone number when requesting an OTP from the
dashboard. (To onboard family later, repeat this step — and
remember to also add their number as a tester in your Meta app.)

### 5. Run the backend

```bash
cd backend
uvicorn main:app --reload
```

API at `http://localhost:8000`.
Swagger UI at `http://localhost:8000/docs`.

### 6. Run the frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Dashboard at `http://localhost:3000`. The default `BACKEND_URL`
in `.env.example` points to `http://localhost:8000`; change it
if your backend runs elsewhere.

---

## Running with Docker

The fastest way to run both services locally:

```bash
cp backend/.env.example backend/.env   # fill in your values
cp frontend/.env.example frontend/.env.local
docker-compose up --build
```

Backend at `http://localhost:8000`, dashboard at `http://localhost:3000`.

**Note on `BACKEND_URL`:** Next.js bakes rewrite URLs into the build.
The compose file passes `http://backend:8000` as a build arg so
the dashboard talks to the backend container by service name. If
your backend lives elsewhere (e.g. Railway), rebuild with:

```bash
docker-compose build --build-arg BACKEND_URL=https://your-backend.up.railway.app
```

---

## Connecting Meta WhatsApp

Cazuela uses the Meta WhatsApp Cloud API.

1. Create a Meta for Developers app at [developers.facebook.com](https://developers.facebook.com)
2. Add the WhatsApp product and get a test phone number
3. Set the webhook URL to your public URL + `/webhook`
4. Set the webhook verify token to match `META_WEBHOOK_VERIFY_TOKEN` in your `.env`
5. Subscribe to the `messages` webhook field
6. **Add each recipient phone as a tester** (App Dashboard → WhatsApp → API Setup → "To"). On the free tier, Meta will only deliver messages to numbers in this list — including OTPs. Skipping this step is the #1 reason "login works but no message arrives".

Use a **System User access token** (Business Settings → System Users → Generate Token, no expiration) for `META_ACCESS_TOKEN`. The temporary tokens shown in the API Setup tab expire in 24 hours.

---

## Running Tests

```bash
cd backend
.venv/bin/pytest
```

Tests do not require a live Supabase connection —
DB calls are mocked. To run the MCP replay benchmark:

```bash
cd backend
python replay.py fixtures/mcp_snapshots/expense_comida.json \
  --mode stub --runs 3 --expect-final-status confirmed
```

## Reminder Deploy Checklist

- Run migration: `backend/migrations/reminders_migration.sql`
- Create Railway cron service: `python -m app.jobs.send_digest` on `0 13 * * *`
- Create Railway cron service: `python -m app.jobs.send_reminders` on `*/15 * * * *`
- Ensure both cron services have: `SUPABASE_URL`, `SUPABASE_KEY`, `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`
- Open the 24h WhatsApp window by sending any user message
- Verify: one digest with `Continuar`, then one due reminder arrives and flips `remind_sent=true`

---

## MCP Integration

Cazuela implements a propose→confirm/rollback staging
pattern for agent interactions:

```
send_context → request_action → [user confirms] → confirm
                                [user cancels]  → rollback
```

Key files:

| File | Purpose |
|------|---------|
| `backend/app/mcp/client.py` | Five-verb client API |
| `backend/app/mcp/agent.py` | Stub + optional Haiku agent |
| `backend/app/mcp/context.py` | Context store + redaction |
| `backend/mcp_context_schema.md` | Schema + field docs |
| `backend/fixtures/mcp_snapshots/` | Example context snapshots |
| `backend/replay.py` | Reproducibility replay script |
| `COMPARISON_REPORT.md` | Benchmark results vs baseline |
| `agent_iteration_log.md` | Full agent decision log |

---

## WhatsApp Commands

Send `ayuda` at any time to see the full command reference.

| Message | Action |
|---------|--------|
| `gasté 5000 en almuerzo` | Log expense with category |
| `pagué 3000` | Log expense, bot proposes category |
| `gasté 18000 en super: pan, leche` | Log batch expense |
| `confirmar` / `cancelar` | Confirm or cancel pending action |
| `resumen` | Weekly summary by category |
| `pendiente: llamar al banco` | Add a todo |
| `mis pendientes` | List open todos |
| `listo: llamar al banco` | Mark todo as done |
| `comprar: leche` | Add item to shopping list |
| `compras` | View shopping list |
| `compré leche` | Mark item as bought |
| `esperando: respuesta del banco` | Track waiting item |
| `mis esperas` | List open waiting items |
| `llegó: banco` | Mark as resolved |
| `despensa cocina: arroz 3` | Add pantry item |
| `mi despensa` | View pantry stock |
| `usé: jabón` | Consume one unit |
| `compré todo` | Restock everything low |
| `nueva receta: cazuela` | Create recipe (AI suggests ingredients) |
| `mis recetas` | List all recipes |
| `receta: cazuela` | Show recipe ingredients |
| `ayuda` | Show all commands |

**Expense categories:**
comida, transporte, salud, hogar, entretenimiento,
ropa, tecnología, educación, viajes, otros

---

## Project Structure

```
cazuela/
├── backend/
│   ├── app/
│   │   ├── handlers/         # One module per feature (see handlers/__init__.py for full API)
│   │   ├── mcp/              # MCP staging: client, agent, context
│   │   ├── routes/           # Dashboard + auth REST API
│   │   ├── db/               # Supabase client + queries
│   │   ├── ai_router.py      # Haiku intent classifier (AI mode)
│   │   ├── patterns.py       # All compiled regex patterns
│   │   ├── copy.py           # Static Spanish copy strings
│   │   ├── dispatch.py       # AI intent dispatch + routing helpers
│   │   └── router.py         # Message routing entry point (route())
│   ├── fixtures/
│   │   └── mcp_snapshots/    # Example context JSON snapshots
│   ├── migrations/           # Supabase SQL migrations
│   ├── scripts/              # Benchmark + comparison scripts
│   ├── tests/
│   ├── replay.py             # MCP reproducibility replay
│   └── main.py
├── frontend/                 # Next.js dashboard
├── COMPARISON_REPORT.md      # MCP vs baseline benchmark
├── agent_iteration_log.md    # Agent decision log
└── README.md
```

---

## Roadmap

| Phase | What | Status |
|-------|------|--------|
| 0 | Infrastructure | done |
| 1 | Expenses + WhatsApp parsing | done |
| 2 | Todos + waiting on | done |
| 3 | Weekly budget + monthly estimate | done |
| 4 | Shopping list | done |
| 5 | Despensa + "necesito comprar" MCP flow | done |
| 5b | Recipes + meal planning | done |
| 6 | Dashboard (Next.js) | done |
| 7 | Onboarding + multi-user polish | planned |
