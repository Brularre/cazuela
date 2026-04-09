from fastapi import FastAPI, Request, Response
from twilio.twiml.messaging_response import MessagingResponse
from app.db.users import get_or_create_user
from app.router import route

app = FastAPI(title="Cazuela")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    form = await request.form()
    body = form.get("Body", "").strip()
    sender = form.get("From", "")

    user = get_or_create_user(sender)
    text = route(body, user)

    reply = MessagingResponse()
    reply.message(text)

    return Response(content=str(reply), media_type="application/xml")
