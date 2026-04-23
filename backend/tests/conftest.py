import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("SESSION_SECRET", "test-secret-that-is-long-enough-for-jwt-hs256")
os.environ.setdefault("META_SKIP_VALIDATION", "true")


FAKE_USER = {"id": "abc-123", "phone": "+56912345678"}


def meta_payload(body, sender="56912345678"):
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": sender,
                        "type": "text",
                        "text": {"body": body},
                    }]
                }
            }]
        }]
    }

sys.modules.setdefault("app.db", MagicMock())
_mock_users = MagicMock()
_mock_users.get_or_create_user.return_value = (MagicMock(), False)
sys.modules.setdefault("app.db.users", _mock_users)
sys.modules.setdefault("app.db.recipes", MagicMock())
sys.modules.setdefault("app.db.meal_plans", MagicMock())
