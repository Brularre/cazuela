import csv
import io
import json
import warnings
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.config import settings
from app.db import client
from app.db.users import get_or_create_user
from app.router import route, WELCOME_TEXT
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router

app = FastAPI(title="Cazuela")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

if not settings.session_secret:
    warnings.warn("SESSION_SECRET is not set — dashboard auth will return 401 for all requests")
if not settings.twilio_auth_token and not settings.twilio_skip_validation:
    warnings.warn("TWILIO_AUTH_TOKEN is not set — /webhook will reject all requests")
if settings.twilio_skip_validation:
    if settings.cookie_secure:
        raise RuntimeError("TWILIO_SKIP_VALIDATION cannot be true in production")
    warnings.warn("TWILIO_SKIP_VALIDATION is true — Twilio signature checks are disabled")
app.include_router(auth_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    form = await request.form()

    if not settings.twilio_skip_validation:
        if not settings.twilio_auth_token:
            return Response(content="Forbidden", status_code=403)
        validator = RequestValidator(settings.twilio_auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(str(request.url), dict(form), signature):
            return Response(content="Forbidden", status_code=403)

    body = form.get("Body", "").strip()
    sender = form.get("From", "")

    try:
        user, is_new = get_or_create_user(sender)
        text = WELCOME_TEXT if is_new else route(body, user)
    except Exception as e:
        warnings.warn(f"Webhook error for {sender}: {e}")
        text = "Tuve un problema. Por favor intenta nuevamente."

    reply = MessagingResponse()
    reply.message(text)

    return Response(content=str(reply), media_type="application/xml")


@app.get("/export")
def export(phone: str, format: str = "json", token: str = ""):
    if not settings.export_token or token != settings.export_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    user, _ = get_or_create_user(phone)

    result = (
        client.table("expenses")
        .select("amount, category, note, date")
        .eq("user_id", user["id"])
        .order("date", desc=True)
        .execute()
    )

    expenses = result.data or []

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["date", "amount", "category", "note"]
        )
        writer.writeheader()
        writer.writerows(expenses)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gastos.csv"},
        )

    return expenses
