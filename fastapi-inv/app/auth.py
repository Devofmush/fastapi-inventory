# app/auth.py
from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.models import get_user
import bcrypt

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return user
    return None

def login_required(request: Request):
    if not request.session.get("user"):
        raise HTTPException(status_code=403, detail="Not authenticated")
