import os
from itsdangerous import URLSafeSerializer
from fastapi import Request, HTTPException
from ..settings import settings

_CSRF_KEY = "_csrf_token"

def _get_serializer() -> URLSafeSerializer:
    return URLSafeSerializer(settings.secret_key, salt="csrf-v1")

def get_or_set_csrf(request: Request) -> str:
    token = request.session.get(_CSRF_KEY)
    if not token:
        s = _get_serializer()
        token = s.dumps(os.urandom(16).hex())
        request.session[_CSRF_KEY] = token
    return token

def validate_csrf(request: Request, token: str):
    if not token:
        raise HTTPException(status_code=400, detail="Missing CSRF token")
    s = _get_serializer()
    try:
        # token is signed but we only care it's valid and equals the session's token
        expected = request.session.get(_CSRF_KEY)
        s.loads(token)  # verify signature
        if token != expected:
            raise HTTPException(status_code=400, detail="Invalid CSRF token")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSRF token")

