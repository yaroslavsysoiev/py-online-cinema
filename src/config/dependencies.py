import os

from fastapi import Depends, HTTPException, status, Request

from config.settings import TestingSettings, Settings, BaseAppSettings, get_settings

from security.interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager

from sqlalchemy.ext.asyncio import AsyncSession

# from database import get_db  # Moved to inside function
from database.models.accounts import UserModel, UserGroupEnum


def get_jwt_auth_manager(settings: BaseAppSettings = Depends(get_settings)) -> JWTAuthManagerInterface:
    """
    Create and return a JWT authentication manager instance.
    """
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


async def get_current_user(
        request: Request,
        db: AsyncSession = Depends(lambda: __import__('database').database.get_db()),
        jwt_manager=Depends(get_jwt_auth_manager)
) -> UserModel:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    token = auth_header.split(" ")[1]
    try:
        payload = jwt_manager.decode_access_token(token)
        user_id = payload.get("user_id")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


async def get_current_admin(
        current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    if not current_user.has_group(UserGroupEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_current_moderator(
        current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    if not (
            current_user.has_group(UserGroupEnum.ADMIN)
            or current_user.has_group(UserGroupEnum.MODERATOR)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator privileges required"
        )
    return current_user
