from datetime import timedelta, datetime
from typing import Optional
from fastapi import Request, HTTPException
from passlib.context import CryptContext
from starlette.responses import RedirectResponse

from ..db import session_scope
from ..models import User
from ..settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_KEY = "user_id"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def login_user(resp: RedirectResponse, request: Request, user_id: int):
    request.session[SESSION_KEY] = user_id
    # optional: set expiry by custom cookie (SessionMiddleware handles cookie)
    return resp

def logout_user(resp: RedirectResponse, request: Request):
    request.session.pop(SESSION_KEY, None)
    return resp

def current_user_id(request: Request) -> Optional[int]:
    return request.session.get(SESSION_KEY)

def require_login(request: Request):
    if not current_user_id(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

def bootstrap_admin():
    """Ensure one admin user exists using env credentials."""
    with session_scope() as db:
        admin = db.query(User).filter(User.email == settings.admin_email).first()
        if not admin:
            db.add(User(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password)
            ))

