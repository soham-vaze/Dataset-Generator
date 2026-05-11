import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.use_cases.auth import login_user, register_user
from domain.entities.user import UserEntity
from domain.interfaces.user_repository import UserRepositoryInterface
from interfaces.api.dependencies import auth_service, get_current_user, get_user_repo
from interfaces.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from interfaces.schemas.dataset import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserEntity = Depends(get_current_user)) -> dict:
    return {"id": str(current_user.id), "email": current_user.email}


@router.post("/register", response_model=MessageResponse)
def register(
    email: str = Form(...),
    password: str = Form(...),
    user_repo: UserRepositoryInterface = Depends(get_user_repo),
) -> dict:
    try:
        validated = RegisterRequest(email=email, password=password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        register_user(
            email=validated.email,
            password=validated.password,
            user_repo=user_repo,
            auth_service=auth_service,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "User registered successfully"}


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepositoryInterface = Depends(get_user_repo),
) -> dict:
    token = login_user(
        email=form_data.username,
        password=form_data.password,
        user_repo=user_repo,
        auth_service=auth_service,
    )

    if not token:
        logger.warning("Failed login attempt for: %s", form_data.username)
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return {"access_token": token, "token_type": "bearer"}
