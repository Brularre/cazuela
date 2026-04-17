import jwt
from fastapi import Cookie, HTTPException
from app.config import settings


def require_auth(session: str = Cookie(None)) -> str:
    if not session or not settings.session_secret:
        raise HTTPException(status_code=401)
    try:
        payload = jwt.decode(session, settings.session_secret, algorithms=["HS256"])
        return payload["phone"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401)
