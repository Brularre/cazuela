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

alter table events
    add column if not exists remind_at timestamptz,
    add column if not exists remind_sent boolean not null default false,
    add column if not exists recur text check (
        recur is null or recur in (
            'daily', 'weekly',
            'mondays', 'tuesdays', 'wednesdays', 'thursdays',
            'fridays', 'saturdays', 'sundays'
        )
    );

create index if not exists events_user_start
    on events (user_id, starts_at);
create index if not exists events_due_reminders
    on events (remind_at) where remind_sent = false;

alter table users
    add column if not exists calendar_token text;
