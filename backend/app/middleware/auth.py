import jwt
from fastapi import Cookie, HTTPException
from app.config import settings


def require_auth(session: str = Cookie(None)) -> str:
    if not session or not settings.session_secret:
        raise HTTPException(status_code=401)
    try:
        payload = jwt.decode(session, settings.session_secret, algorithms=["HS256"])
        if "user_id" not in payload:
            raise HTTPException(status_code=401, detail="session_expired")
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="session_expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401)
