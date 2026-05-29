"""Outbound WhatsApp sender. Single place that talks to Meta.

Public API:
- send_text(phone, body) -> bool

Known limitation: free-form text only delivers inside Meta's
24-hour customer-service window. Proactive sends outside that
window need an approved template.
"""
import warnings

import requests

from app.config import settings


def send_text(phone: str, body: str) -> bool:
    if not (settings.meta_access_token and settings.meta_phone_number_id):
        warnings.warn("Meta credentials not set — message not sent")
        return False
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{settings.meta_phone_number_id}/messages",
        headers={"Authorization": f"Bearer {settings.meta_access_token}"},
        json={
            "messaging_product": "whatsapp",
            "to": phone.lstrip("+"),
            "type": "text",
            "text": {"body": body},
        },
        timeout=10,
    )
    if not res.ok:
        warnings.warn(f"WhatsApp send failed {res.status_code}: {res.text[:200]}")
    return res.ok
