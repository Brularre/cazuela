import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("SESSION_SECRET", "test-secret-that-is-long-enough-for-jwt-hs256")
os.environ.setdefault("TWILIO_SKIP_VALIDATION", "true")

sys.modules.setdefault("app.db", MagicMock())
sys.modules.setdefault("app.db.users", MagicMock())
