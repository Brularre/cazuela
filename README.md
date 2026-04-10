# Cazuela

A personal life assistant accessible via WhatsApp.
Send natural language messages in Spanish — Cazuela logs expenses,
gives weekly summaries, and will eventually manage todos, reminders,
meals, and more.

No app to install. Just save the number and start messaging.

## Features (current)

- Log expenses: `gasté 5000 en almuerzo`
- Automatic category detection from description
- Weekly summary: `resumen`
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
(SQL editor → New query):

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  phone text unique not null,
  created_at timestamptz default now()
);

create table expenses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  amount numeric not null,
  category text not null,
  note text,
  date date default current_date,
  created_at timestamptz default now()
);
```

### 4. Run the server

```bash
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
source .venv/bin/activate
pytest
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
3. Add `SUPABASE_URL` and `SUPABASE_KEY` as environment variables
4. Railway auto-deploys on every push to `main`

---

## WhatsApp Commands

| Message | Action |
|---------|--------|
| `gasté [amount] en [description]` | Log an expense |
| `gaste [amount] [description]` | Log an expense (no accent) |
| `resumen` | Weekly summary by category |

**Expense categories (auto-detected):**
comida, transporte, salud, hogar, entretenimiento,
ropa, tecnologia, educacion, viajes, otros

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
│   │   ├── handlers/       # Business logic (expenses, summary)
│   │   ├── db/             # Supabase client + user queries
│   │   └── router.py       # Message routing (regex patterns)
│   ├── tests/
│   │   ├── fixtures/       # Shared test data
│   │   ├── test_aggregation.py
│   │   ├── test_expenses.py
│   │   ├── test_integration.py
│   │   ├── test_main.py
│   │   └── test_router.py
│   ├── main.py
│   ├── requirements.txt
│   └── requirements-dev.txt
└── README.md
```

---

## Roadmap

| Phase | What |
|-------|------|
| 0 | Infrastructure — done |
| 1 | Core agent + Expenses — done |
| 2 | Todos + Reminders + Google Calendar |
| 3 | Budget + Savings goals + Email |
| 4 | Shopping list + Wishlist |
| 5 | Despensa + Google Sheets + Meal planning |
| 6 | Dashboard (Next.js) |
| 7 | Onboarding + multi-user polish |
