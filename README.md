# Cazuela

A personal life assistant accessible via WhatsApp.
Send natural language messages in Spanish — Cazuela logs expenses,
tracks todos, manages your pantry, and more.

No app to install. Just save the number and start messaging.

## Features (current)

- **Expenses:** `gasté 5000 en almuerzo` — logs with auto-detected category
- **Ambiguous expenses:** `pagué 3000` — AI proposes category, you confirm
- **Weekly summary:** `resumen`
- **Todos:** `pendiente: llamar al banco` / `mis pendientes` / `listo: banco`
- **Shopping list:** `comprar: leche` / `compras` / `compré leche`
- **Waiting on:** `esperando: respuesta del seguro` / `mis esperas` / `llegó: seguro`
- **Pantry:** `despensa cocina: arroz 3` / `mi despensa` / `usé: jabón` / `compré todo`
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
TWILIO_AUTH_TOKEN=your-twilio-auth-token
SESSION_SECRET=any-long-random-string
```

### 3. Set up Supabase

Run the migration files in `backend/` against your Supabase project
(SQL editor → New query), in the order listed in `backend/SCHEMA.md`.

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

---

## Deployment (Railway)

The app includes a `Procfile` for Railway:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

1. Create a new project on [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Add environment variables (see `.env.example`)
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
| `esperando: respuesta del banco` | Track something waiting on someone else |
| `mis esperas` | List open waiting items |
| `llegó: banco` | Mark as resolved |
| `despensa cocina: arroz 3` | Add pantry item with category |
| `mi despensa` | View pantry stock |
| `usé: jabón` | Consume one unit |
| `compré: jabón` | Restock one item |
| `compré todo` | Restock everything that's low |
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
│   │   ├── mcp/            # Context store for confirm/cancel flow
│   │   ├── routes/         # Dashboard + auth REST API
│   │   ├── db/             # Supabase client + user queries
│   │   └── router.py       # Message routing (regex patterns)
│   ├── tests/
│   └── main.py
├── frontend/               # Next.js dashboard
└── README.md
```

---

## Roadmap

| Phase | What | Status |
|-------|------|--------|
| 0 | Infrastructure | ✓ done |
| 1 | Core agent + Expenses | ✓ done |
| 2 | Todos + waiting on | ✓ done |
| 3 | Weekly budget | planned |
| 4 | Shopping list | handler only |
| 5 | Despensa + meal planning | despensa live |
| 6 | Dashboard (Next.js) | in progress |
| 7 | Onboarding + multi-user polish | planned |
