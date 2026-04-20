import re
from app.db import client

_PHONE_RE = re.compile(r'^\+\d{7,15}$')


def get_or_create_user(raw_phone: str) -> tuple[dict, bool]:
    phone = raw_phone.replace("whatsapp:", "")
    if not _PHONE_RE.match(phone):
        raise ValueError(f"Invalid phone number: {phone}")
    result = client.table("users").select("*").eq("phone", phone).execute()
    if result.data:
        return result.data[0], False
    result = client.table("users").insert({"phone": phone}).execute()
    if not result.data:
        raise RuntimeError("Failed to create user")
    return result.data[0], True
