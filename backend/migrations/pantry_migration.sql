create table pantry (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  item text not null,
  desired_quantity integer not null,
  current_quantity integer not null,
  created_at timestamptz default now()
);
