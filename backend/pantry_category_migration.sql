alter table pantry
  add column category text not null default 'otros'
  check (category in ('cocina', 'baño', 'otros'));
