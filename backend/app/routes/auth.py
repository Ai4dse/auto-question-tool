import os
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from mongoengine.errors import NotUniqueError
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.models.user_model import User

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
MIN_PASSWORD_LENGTH = int(os.getenv("AUTH_MIN_PASSWORD_LENGTH", "8"))
ALLOW_PUBLIC_USER_CREATION = os.getenv("ALLOW_PUBLIC_USER_CREATION", "false").lower() == "true"
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "")
AUTH_SESSION_COOKIE_NAME = os.getenv("AUTH_SESSION_COOKIE_NAME", "auth_session")
AUTH_SESSION_HOURS = int(os.getenv("AUTH_SESSION_HOURS", "12"))
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax")


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)
    display_name: str | None = Field(default=None, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)


class SessionInfoResponse(BaseModel):
    username: str
    display_name: str | None
    must_change: bool

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _hash_session_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _session_expiry_utc() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=AUTH_SESSION_HOURS)


def _set_session_cookie(response: Response, session_token: str) -> None:
    response.set_cookie(
        key=AUTH_SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        max_age=AUTH_SESSION_HOURS * 60 * 60,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_SESSION_COOKIE_NAME,
        path="/",
    )


def _create_session_for_user(user: User) -> str:
    token = secrets.token_urlsafe(48)
    user.session_token_hash = _hash_session_token(token)
    user.session_expires_at = _session_expiry_utc()
    user.save()
    return token


def _get_user_from_session_token(session_token: str | None) -> User | None:
    if not session_token:
        return None

    token_hash = _hash_session_token(session_token)
    user = User.objects(session_token_hash=token_hash).first()
    if not user or not user.session_expires_at:
        return None

    now = datetime.now(timezone.utc)
    expires_at = user.session_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        user.session_token_hash = None
        user.session_expires_at = None
        user.save()
        return None

    return user


def require_authenticated_user(request: Request) -> User:
    session_token = request.cookies.get(AUTH_SESSION_COOKIE_NAME)
    user = _get_user_from_session_token(session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_password_changed(user: User = Depends(require_authenticated_user)) -> User:
    if user.must_change_password:
        raise HTTPException(status_code=403, detail="Password change required")
    return user


def _require_admin_token(x_admin_token: str | None) -> None:
    if ALLOW_PUBLIC_USER_CREATION:
        return

    if not ADMIN_API_TOKEN:
        raise HTTPException(status_code=503, detail="User creation is disabled")

    if x_admin_token != ADMIN_API_TOKEN:
        raise HTTPException(status_code=403, detail="Missing or invalid admin token")


@router.post("/create_user")
def create_user(payload: CreateUserRequest, x_admin_token: str | None = Header(default=None)):
    _require_admin_token(x_admin_token)
    username = payload.username.strip()
    password = payload.password

    if User.objects(username=username).first():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        username=username,
        password=hash_password(password),
        display_name=payload.display_name,
        must_change_password=True
    )
    try:
        user.save()
    except NotUniqueError:
        raise HTTPException(status_code=409, detail="User already exists")
    return {"message": "User created", "username": username}


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    username = payload.username.strip()
    user = User.objects(username=username).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_token = _create_session_for_user(user)
    _set_session_cookie(response, session_token)

    return {
        "username": user.username,
        "display_name": user.display_name,
        "must_change": user.must_change_password,
    }


@router.get("/me", response_model=SessionInfoResponse)
def get_current_session(user: User = Depends(require_authenticated_user)):
    return {
        "username": user.username,
        "display_name": user.display_name,
        "must_change": user.must_change_password,
    }


@router.post("/logout")
def logout(response: Response, user: User = Depends(require_authenticated_user)):
    user.session_token_hash = None
    user.session_expires_at = None
    user.save()
    _clear_session_cookie(response)
    return {"message": "Logged out"}


@router.post("/change_password")
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    user: User = Depends(require_authenticated_user),
):
    if not verify_password(payload.old_password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.password = hash_password(payload.new_password)
    user.must_change_password = False
    session_token = _create_session_for_user(user)
    _set_session_cookie(response, session_token)

    return {"message": "Password updated successfully"}
