alter table pantry
  add constraint pantry_user_id_item_key unique (user_id, item);
