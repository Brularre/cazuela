create table if not exists user_modules (
    user_id uuid references users(id) on delete cascade,
    module text not null,
    enabled boolean not null default true,
    primary key (user_id, module)
);

create table if not exists events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references users(id) on delete cascade,
    title text not null,
    starts_at timestamptz not null,
    ends_at timestamptz,
    category text default 'otro',
    created_at timestamptz default now()
);

create index if not exists events_user_start
    on events (user_id, starts_at);

alter table users
    add column if not exists calendar_token text;
