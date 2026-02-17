# app/api/routes_auth.py

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.auth import STATIC_USERS, create_access_token


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    user = STATIC_USERS.get(data.username)

    if not user or user["password"] != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(
        username=data.username,
        role=user["role"],
    )

    return TokenResponse(access_token=token)
