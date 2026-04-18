import re
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from twilio.rest import Client as TwilioClient
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

    if settings.twilio_account_sid and settings.twilio_from_number and settings.twilio_auth_token:
        twilio = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        twilio.messages.create(
            from_=settings.twilio_from_number,
            to=f"whatsapp:{phone}",
            body=f"Tu código de acceso a Cazuela: {code}",
        )

    return {"ok": True}


@router.post("/verify-otp")
def verify_otp(body: OTPVerify):
    phone = body.phone
    code = body.code

    result = (
        client.table("otp_codes")
        .select("id")
        .eq("phone", phone)
        .eq("code", code)
        .eq("used", False)
        .gt("expires_at", datetime.now(timezone.utc).isoformat())
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=401)

    row_id = result.data[0]["id"]
    client.table("otp_codes").update({"used": True}).eq("id", row_id).execute()

    payload = {
        "phone": phone,
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
