"""Outbound WhatsApp sender. Single place that talks to Meta.

Public API:
- send_text(phone, body) -> bool
    Plain-text message. Delivers inside the 24-hour customer-service window.

- send_interactive(phone, body, buttons) -> bool
    Free-form interactive button message (max 3 buttons, each title ≤ 20
    chars). Used by the daily digest to carry a Continuar quick-reply
    button that resets the 24-hour window when tapped. Only delivers
    inside an already-open window.

Known limitation: both functions fail silently (warn + return False) when
the 24-hour window is closed. The daily digest accepts this — the user
resumes the chain by messaging Cazuela.
"""
import warnings

import requests

from app.config import settings

_META_URL = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"


def _meta_headers() -> dict:
    return {"Authorization": f"Bearer {settings.meta_access_token}"}


def send_text(phone: str, body: str) -> bool:
    if not (settings.meta_access_token and settings.meta_phone_number_id):
        warnings.warn("Meta credentials not set — message not sent")
        return False
    res = requests.post(
        _META_URL.format(phone_number_id=settings.meta_phone_number_id),
        headers=_meta_headers(),
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


def send_interactive(phone: str, body: str, buttons: list[str]) -> bool:
    if not (settings.meta_access_token and settings.meta_phone_number_id):
        warnings.warn("Meta credentials not set — message not sent")
        return False
    res = requests.post(
        _META_URL.format(phone_number_id=settings.meta_phone_number_id),
        headers=_meta_headers(),
        json={
            "messaging_product": "whatsapp",
            "to": phone.lstrip("+"),
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": f"btn_{i}", "title": title},
                        }
                        for i, title in enumerate(buttons)
                    ]
                },
            },
        },
        timeout=10,
    )
    if not res.ok:
        warnings.warn(
            f"WhatsApp interactive send failed {res.status_code}: {res.text[:200]}"
        )
    return res.ok
