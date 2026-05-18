-- Cazuela — bootstrap schema for a fresh Supabase project.
-- Run this single file in the Supabase SQL editor on a new project to
-- create every table the app needs. Reflects SCHEMA.md as of 2026-04-20.
--
-- Existing deploys do NOT need this file — the per-table migrations in
-- this folder are the historical record. New self-hosters only need
-- this one.

create extension if not exists "pgcrypto";

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  phone text not null unique,
  name text,
  currency text not null default 'CLP',
  anthropic_key text,
  ai_mode boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists expenses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  amount numeric not null,
  currency text not null default 'CLP',
  category text not null,
  note text,
  date date not null default current_date,
  receipt_url text,
  created_at timestamptz not null default now()
);

create table if not exists todos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  task text not null,
  done boolean not null default false,
  due_date date,
  priority text not null default 'semana'
    check (priority in ('hoy', 'semana', 'mes')),
  created_at timestamptz not null default now()
);

create table if not exists waiting_on (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  description text not null,
  resolved boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists shopping_list (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  item text not null,
  quantity integer,
  unit text,
  checked boolean not null default false,
  source text not null default 'manual',
  created_at timestamptz not null default now()
);

create table if not exists budgets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  period text not null default 'mes' check (period = 'mes'),
  amount numeric not null,
  created_at timestamptz not null default now(),
  unique (user_id, period)
);

create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

create table if not exists otp_codes (
  id uuid primary key default gen_random_uuid(),
  phone text not null,
  code text not null,
  expires_at timestamptz not null,
  used boolean not null default false,
  attempts integer not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists pantry (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  item text not null,
  desired_quantity integer not null,
  current_quantity integer not null,
  category text not null default 'otros'
    check (category in ('cocina', 'baño', 'otros')),
  created_at timestamptz not null default now(),
  unique (user_id, item)
);

create table if not exists mcp_contexts (
  context_id uuid primary key,
  version text not null default '1.0',
  domain text not null,
  user_id uuid not null references users(id) on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  status text not null default 'pending'
    check (status in ('pending', 'staged', 'confirmed', 'rolled_back')),
  payload jsonb not null default '{}',
  proposed jsonb,
  agent_model text not null default 'stub-v1',
  iteration_count integer not null default 0
);

create index if not exists idx_mcp_contexts_user_status
  on mcp_contexts (user_id, status);
create index if not exists idx_mcp_contexts_expires_at
  on mcp_contexts (expires_at);

alter table mcp_contexts enable row level security;
create policy mcp_contexts_user_isolation on mcp_contexts
  for all using (user_id = auth.uid());

create table if not exists recipes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  name text not null,
  servings integer not null default 2,
  created_at timestamptz not null default now()
);

create table if not exists recipe_ingredients (
  id uuid primary key default gen_random_uuid(),
  recipe_id uuid references recipes(id) on delete cascade,
  item text not null,
  quantity numeric,
  unit text,
  created_at timestamptz not null default now()
);

create table if not exists meal_plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  week_start date not null,
  slots jsonb not null default '["almuerzo","cena"]',
  created_at timestamptz not null default now(),
  unique (user_id, week_start)
);

create table if not exists meal_plan_entries (
  id uuid primary key default gen_random_uuid(),
  meal_plan_id uuid references meal_plans(id) on delete cascade,
  day_of_week text not null,
  slot_name text not null,
  recipe_id uuid references recipes(id) on delete set null,
  created_at timestamptz not null default now()
);
