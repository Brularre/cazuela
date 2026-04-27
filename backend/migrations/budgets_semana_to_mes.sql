-- One-time: align legacy period='semana' rows with the monthly budget model.
-- If a user had both 'semana' and 'mes', keep 'mes' and drop the 'semana' row to avoid unique (user_id, period) conflicts.
delete from budgets b1
  using budgets b2
  where b1.user_id = b2.user_id
    and b1.period = 'semana'
    and b2.period = 'mes';

update budgets
  set period = 'mes'
  where period = 'semana';
