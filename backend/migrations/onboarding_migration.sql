ALTER TABLE users
    ADD COLUMN IF NOT EXISTS onboarding_complete boolean NOT NULL DEFAULT false;

UPDATE users SET onboarding_complete = true;
