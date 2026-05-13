from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.category_service import CategoryService


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, payload: RegisterRequest) -> User:
        existing = (
            self.db.query(User)
            .filter((User.email == payload.email) | (User.username == payload.username))
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already exists")

        user = User(
            email=payload.email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        CategoryService(self.db).ensure_default_categories(user.id)
        return user

    def login(self, username: str, password: str) -> tuple[str, User]:
        login_identifier = username.strip().lower()
        user = (
            self.db.query(User)
            .filter(or_(User.email == login_identifier, User.username == username.strip()))
            .first()
        )
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        token = create_access_token(subject=str(user.id))
        return token, user
