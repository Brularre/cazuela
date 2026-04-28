import csv
import hashlib
import hmac
import io
import json
import warnings
import requests
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.config import settings
from app.db import client
from app.db.users import get_or_create_user
from app.router import route, WELCOME_TEXT
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.export_import import router as export_import_router

app = FastAPI(title="Cazuela")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

if not settings.session_secret:
    warnings.warn("SESSION_SECRET is not set — dashboard auth will return 401 for all requests")
if not settings.meta_app_secret and not settings.meta_skip_validation:
    warnings.warn("META_APP_SECRET is not set — /webhook will reject all requests")
if settings.meta_skip_validation:
    if settings.cookie_secure:
        raise RuntimeError("META_SKIP_VALIDATION cannot be true in production")
    warnings.warn("META_SKIP_VALIDATION is true — Meta signature checks are disabled")

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(export_import_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/webhook")
def webhook_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if (
        settings.meta_webhook_verify_token
        and mode == "subscribe"
        and token == settings.meta_webhook_verify_token
    ):
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Forbidden", status_code=403)


def _send_whatsapp(to: str, text: str):
    if not settings.meta_access_token or not settings.meta_phone_number_id:
        warnings.warn("Meta credentials not set — message not sent")
        return
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{settings.meta_phone_number_id}/messages",
        headers={"Authorization": f"Bearer {settings.meta_access_token}"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        },
        timeout=10,
    )
    if not res.ok:
        warnings.warn(f"Meta API error {res.status_code}: {res.text[:200]}")


@app.post("/webhook")
async def webhook(request: Request):
    raw_body = await request.body()

    if not settings.meta_skip_validation:
        if not settings.meta_app_secret:
            return Response(content="Forbidden", status_code=403)
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(
            settings.meta_app_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            return Response(content="Forbidden", status_code=403)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return Response(content="Bad Request", status_code=400)

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                sender = "+" + message["from"]
                body = message.get("text", {}).get("body", "").strip()
                try:
                    user, is_new = get_or_create_user(sender)
                    text = WELCOME_TEXT if is_new else route(body, user)
                except Exception as e:
                    warnings.warn(f"Webhook error for {sender}: {e}")
                    text = "Tuve un problema. Por favor intenta nuevamente."
                _send_whatsapp(message["from"], text)

    return Response(content="OK", status_code=200)


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
