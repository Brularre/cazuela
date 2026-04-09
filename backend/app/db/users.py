from app.db import client


def get_or_create_user(raw_phone: str) -> dict:
    phone = raw_phone.replace("whatsapp:", "")

    result = client.table("users").select("*").eq("phone", phone).execute()
    if result.data:
        return result.data[0]

    result = client.table("users").insert({"phone": phone}).execute()
    return result.data[0]
