import csv
import io
import json
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from app.config import settings
from app.db import client
from app.db.users import get_or_create_user
from app.router import route

app = FastAPI(title="Cazuela")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    form = await request.form()

    if settings.twilio_auth_token:
        validator = RequestValidator(settings.twilio_auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(str(request.url), dict(form), signature):
            return Response(content="Forbidden", status_code=403)

    body = form.get("Body", "").strip()
    sender = form.get("From", "")

    user = get_or_create_user(sender)
    text = route(body, user)

    reply = MessagingResponse()
    reply.message(text)

    return Response(content=str(reply), media_type="application/xml")


@app.get("/export")
def export(phone: str, format: str = "json", token: str = ""):
    if not settings.export_token or token != settings.export_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = get_or_create_user(phone)

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
