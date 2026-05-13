from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.models.user import User


def validate_bearer(current_user: User = Depends(get_current_user)) -> bool:
    return current_user is not None
