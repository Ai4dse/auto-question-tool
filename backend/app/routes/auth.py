from fastapi import APIRouter, HTTPException, Query
from passlib.context import CryptContext
from app.models.user_model import User

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

@router.post("/create_user")
def create_user(
    username: str = Query(...),
    password: str = Query(...),
    display_name: str = Query(None)
):
    if User.objects(username=username).first():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        username=username,
        password=hash_password(password),
        display_name=display_name,
        must_change_password=True
    )
    user.save()
    return {"message": "User created", "username": username}


@router.post("/login")
def login(username: str = Query(...), password: str = Query(...)):
    user = User.objects(username=username).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "username": user.username,
        "display_name": user.display_name,
        "must_change": user.must_change_password,
    }

@router.post("/change_password")
def change_password(
    username: str = Query(...),
    old_password: str = Query(...),
    new_password: str = Query(...)
):
    user = User.objects(username=username).first()
    if not user or not verify_password(old_password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.password = hash_password(new_password)
    user.must_change_password = False
    user.save()

    return {"message": "Password updated successfully"}
