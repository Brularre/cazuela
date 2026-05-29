alter table todos
  add column if not exists recur text check (
    recur is null or recur in (
      'daily', 'weekly',
      'mondays', 'tuesdays', 'wednesdays', 'thursdays',
      'fridays', 'saturdays', 'sundays'
    )
  );

alter table events
  add column if not exists recur text check (
    recur is null or recur in (
      'daily', 'weekly',
      'mondays', 'tuesdays', 'wednesdays', 'thursdays',
      'fridays', 'saturdays', 'sundays'
    )
  );
