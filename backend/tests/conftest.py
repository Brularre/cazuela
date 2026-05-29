import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("SESSION_SECRET", "test-secret-that-is-long-enough-for-jwt-hs256")
os.environ.setdefault("META_SKIP_VALIDATION", "true")
os.environ.setdefault("CLASSIFIER_PROVIDER", "stub")
os.environ.setdefault("RESPONDER_PROVIDER", "stub")


FAKE_USER = {"id": "abc-123", "phone": "+15555550100", "onboarding_complete": True}


def meta_payload(body, sender="15555550100"):
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
