from fastapi import FastAPI, Request, Response
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI(title="Cazuela")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    form = await request.form()
    body = form.get("Body", "")
    sender = form.get("From", "")

    print(f"Mensaje de {sender}: {body}")

    reply = MessagingResponse()
    reply.message("Hola! Soy Cazuela. Todavía estoy en construcción 🍲")

    return Response(content=str(reply), media_type="application/xml")
