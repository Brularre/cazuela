insert into user_modules (user_id, module, enabled)
select user_id, 'despensa', false
from user_modules
where module = 'comida' and enabled = false
on conflict (user_id, module) do nothing;
