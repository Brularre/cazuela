alter table todos
    add column if not exists remind_at timestamptz,
    add column if not exists remind_sent boolean not null default false;

alter table events
    add column if not exists remind_at timestamptz,
    add column if not exists remind_sent boolean not null default false;

create index if not exists todos_due_reminders
    on todos (remind_at) where remind_sent = false;
create index if not exists events_due_reminders
    on events (remind_at) where remind_sent = false;
