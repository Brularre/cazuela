create table budgets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  period text not null check (period in ('semana', 'mes')),
  amount numeric not null,
  created_at timestamptz default now(),
  unique (user_id, period)
);
