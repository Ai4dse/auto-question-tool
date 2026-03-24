import os

from fastapi import APIRouter, Header, HTTPException
from mongoengine.errors import NotUniqueError
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.models.user_model import User

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
MIN_PASSWORD_LENGTH = int(os.getenv("AUTH_MIN_PASSWORD_LENGTH", "8"))
ALLOW_PUBLIC_USER_CREATION = os.getenv("ALLOW_PUBLIC_USER_CREATION", "false").lower() == "true"
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "")


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)
    display_name: str | None = Field(default=None, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


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
def login(payload: LoginRequest):
    username = payload.username.strip()
    user = User.objects(username=username).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "username": user.username,
        "display_name": user.display_name,
        "must_change": user.must_change_password,
    }

@router.post("/change_password")
def change_password(payload: ChangePasswordRequest):
    username = payload.username.strip()
    user = User.objects(username=username).first()
    if not user or not verify_password(payload.old_password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.password = hash_password(payload.new_password)
    user.must_change_password = False
    user.save()

    return {"message": "Password updated successfully"}
