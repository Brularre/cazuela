create unique index otp_codes_phone_unused_unique on otp_codes(phone) where used = false;
