# Cazuela

A personal life assistant accessible via WhatsApp.
Send natural language messages in Spanish — Cazuela logs expenses,
gives weekly summaries, and will eventually manage todos, reminders,
meals, and more.

No app to install. Just save the number and start messaging.

## Features (current)

- **Expenses:** `gasté 5000 en almuerzo` — logs with auto-detected category
- **Ambiguous expenses:** `pagué 3000` — AI proposes category, you confirm
- **Weekly summary:** `resumen`
- **Todos:** `pendiente: llamar al banco` / `mis pendientes` / `listo: banco`
- **Shopping list:** `comprar: leche` / `compras` / `compré leche`
- **Wishlist:** `quiero: zapatillas` / `mis deseos`
- **Notes:** `nota: flores en el jardín` / `mis notas` / `buscar nota: flores`
- **Help:** `ayuda` — shows all available commands
- CSV / JSON export via REST API
- Swagger UI at `/docs`

## Tech Stack

- **Backend:** Python + FastAPI
- **Database:** Supabase (managed Postgres)
- **WhatsApp:** Twilio
- **Deployment:** Railway

---

## Running Locally

### 1. Clone and set up the environment

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
```

### 3. Set up Supabase

Create the following tables in your Supabase project
(SQL editor → New query). Run each block separately:

```sql
-- Users
create table users (
  id uuid primary key default gen_random_uuid(),
  phone text unique not null,
  created_at timestamptz default now()
);

-- Expenses
create table expenses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  amount numeric not null,
  category text not null,
  note text,
  date date default current_date,
  created_at timestamptz default now()
);

-- Todos
create table todos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  task text not null,
  done boolean default false,
  due_date date,
  created_at timestamptz default now()
);

-- Shopping list
create table shopping_list (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  item text not null,
  quantity integer,
  unit text,
  checked boolean default false,
  created_at timestamptz default now()
);

-- Wishlist
create table wishlist (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  item text not null,
  price_estimate numeric,
  url text,
  created_at timestamptz default now()
);

-- Notes
create table notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  content text not null,
  created_at timestamptz default now()
);
```

Also run `backend/mcp_contexts_migration.sql` for the
ambiguous expense confirmation flow.

### 4. Run the server

```bash
cd backend
uvicorn main:app --reload
```

API available at `http://localhost:8000`.
Swagger UI at `http://localhost:8000/docs`.

---

## Connecting Twilio

Cazuela uses Twilio's WhatsApp sandbox for development.

1. Create a free account at [twilio.com](https://twilio.com)
2. Go to Messaging → Try it out → Send a WhatsApp message
3. Follow the instructions to join the sandbox
4. Set the webhook URL to your public URL + `/webhook`
   (use Railway or a similar service — local tunneling tools
   are unreliable on managed machines)

---

## Running Tests

```bash
cd backend
.venv/bin/pytest
```

Tests do not require a live Supabase connection —
DB calls are mocked in unit and integration tests.
`pytest.ini` sets `pythonpath = .` so no extra env setup is needed.

---

## Deployment (Railway)

The app includes a `Procfile` for Railway:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

1. Create a new project on [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Add environment variables:
   - `SUPABASE_URL` and `SUPABASE_KEY`
   - `TWILIO_AUTH_TOKEN` — live auth token from Twilio console
   - `EXPORT_TOKEN` — any secret string to protect the export endpoint
4. Railway auto-deploys on every push to `main`

---

## WhatsApp Commands

Send `ayuda` at any time to see the full command reference.

| Message | Action |
|---------|--------|
| `gasté 5000 en almuerzo` | Log an expense with category |
| `pagué 3000` | Log expense, bot proposes category |
| `confirmar` / `cancelar` | Confirm or cancel a pending expense |
| `resumen` | Weekly summary by category |
| `pendiente: llamar al banco` | Add a todo |
| `mis pendientes` | List open todos |
| `listo: llamar al banco` | Mark todo as done |
| `comprar: leche` | Add item to shopping list |
| `compras` | View shopping list |
| `compré leche` | Mark item as bought |
| `quiero: zapatillas` | Add to wishlist |
| `mis deseos` | View wishlist |
| `nota: texto libre` | Save a note |
| `mis notas` | List notes |
| `buscar nota: palabra` | Search notes by keyword |
| `ayuda` | Show all commands |

**Expense categories (auto-detected):**
comida, transporte, salud, hogar, entretenimiento,
ropa, tecnología, educación, viajes, otros

---

## Export

```
GET /export?phone=+56912345678&format=json
GET /export?phone=+56912345678&format=csv
```

---

## Project Structure

```
cazuela/
├── backend/
│   ├── app/
│   │   ├── handlers/       # One module per feature
│   │   │   ├── expenses.py
│   │   │   ├── summary.py
│   │   │   ├── todos.py
│   │   │   ├── shopping.py
│   │   │   ├── wishlist.py
│   │   │   └── notes.py
│   │   ├── mcp/            # Context store for confirm/cancel flow
│   │   │   ├── context.py  # Supabase-backed context state machine
│   │   │   ├── client.py   # Public API for handlers
│   │   │   └── agent.py    # Stub agent (category proposal)
│   │   ├── db/             # Supabase client + user queries
│   │   └── router.py       # Message routing (regex patterns)
│   ├── tests/
│   │   ├── fixtures/       # Shared test data
│   │   ├── test_handlers.py
│   │   ├── test_integration.py
│   │   ├── test_main.py
│   │   ├── test_mcp.py
│   │   └── test_router.py
│   ├── mcp_contexts_migration.sql
│   ├── main.py
│   ├── pytest.ini
│   └── requirements.txt
└── README.md
```

---

## Roadmap

| Phase | What | Status |
|-------|------|--------|
| 0 | Infrastructure | ✓ done |
| 1 | Core agent + Expenses | ✓ done |
| 2 | Todos + Reminders + Google Calendar | todos done; reminders + calendar pending |
| 3 | Budget + Savings goals + Email | pending |
| 4 | Shopping list + Wishlist + Notes | ✓ done |
| 5 | Despensa + Google Sheets + Meal planning | pending |
| 6 | Dashboard (Next.js) | pending |
| 7 | Onboarding + multi-user polish | pending |
