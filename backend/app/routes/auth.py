import re
import secrets
import warnings
import requests
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.config import settings
from app.db import client

_PHONE_RE = re.compile(r'^\+\d{7,15}$')


router = APIRouter(prefix="/auth")


class OTPRequest(BaseModel):
    phone: str


class OTPVerify(BaseModel):
    phone: str
    code: str


@router.post("/request-otp")
def request_otp(body: OTPRequest):
    phone = body.phone

    if not _PHONE_RE.match(phone):
        return {"ok": True}

    result = client.table("users").select("id").eq("phone", phone).execute()
    if not result.data:
        return {"ok": True}

    sixty_ago = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    recent = (
        client.table("otp_codes")
        .select("id")
        .eq("phone", phone)
        .eq("used", False)
        .gt("created_at", sixty_ago)
        .execute()
    )
    if recent.data:
        return {"ok": True}

    code = str(secrets.randbelow(900000) + 100000)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    client.table("otp_codes").insert({
        "phone": phone,
        "code": code,
        "expires_at": expires_at,
    }).execute()

    if settings.meta_access_token and settings.meta_phone_number_id:
        res = requests.post(
            f"https://graph.facebook.com/v19.0/{settings.meta_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {settings.meta_access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone.lstrip("+"),
                "type": "text",
                "text": {"body": f"Tu código de acceso a Cazuela: {code}"},
            },
            timeout=10,
        )
        if not res.ok:
            warnings.warn(f"OTP send failed {res.status_code}: {res.text[:200]}")
    else:
        warnings.warn("Meta credentials not set — OTP not sent")

    return {"ok": True}


@router.post("/verify-otp")
def verify_otp(body: OTPVerify):
    phone = body.phone
    code = body.code

    if not _PHONE_RE.match(phone):
        raise HTTPException(status_code=401)

    result = (
        client.table("otp_codes")
        .select("id, code, attempts")
        .eq("phone", phone)
        .eq("used", False)
        .gt("expires_at", datetime.now(timezone.utc).isoformat())
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=401)

    row = result.data[0]

    if row["attempts"] >= 5:
        raise HTTPException(status_code=429, detail="Demasiados intentos fallidos. Solicita un nuevo código.")

    if row["code"] != code:
        client.table("otp_codes").update({"attempts": row["attempts"] + 1}).eq("id", row["id"]).execute()
        raise HTTPException(status_code=401)

    client.table("otp_codes").update({"used": True}).eq("id", row["id"]).execute()

    user_result = client.table("users").select("id").eq("phone", phone).execute()
    if not user_result.data:
        raise HTTPException(status_code=401)
    user_id = user_result.data[0]["id"]

    payload = {
        "phone": phone,
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    token = jwt.encode(payload, settings.session_secret, algorithm="HS256")

    response = JSONResponse({"ok": True})
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=60 * 60 * 24 * 30,
    )
    return response
