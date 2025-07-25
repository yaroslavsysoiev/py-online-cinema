from datetime import datetime, timezone
from typing import cast

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from pydantic import BaseModel

from config.dependencies import get_current_user, get_current_admin, get_accounts_email_notificator
from security.passwords import validate_password_strength, verify_password, hash_password


from config import get_jwt_auth_manager, BaseAppSettings
from config.settings import get_settings

from database import (
    get_db,
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    NotificationModel,
    CartModel,
    PurchasedMovieModel
)
from exceptions import BaseSecurityError
from schemas import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    MessageResponseSchema,
    UserActivationRequestSchema,
    PasswordResetRequestSchema,
    PasswordResetCompleteRequestSchema,
    UserLoginResponseSchema,
    UserLoginRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    ResendActivationRequestSchema,
    NotificationSchema,
    NotificationUpdateSchema,
)

from utils.email import send_email

from security.interfaces import JWTAuthManagerInterface
from security.passwords import hash_password
from notifications.interfaces import EmailSenderInterface

router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    description="Register a new user with an email and password.",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Conflict - User with this email already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A user with this email test@example.com already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred during user creation.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred during user creation."
                    }
                }
            },
        },
    }
)
async def register_user(
        user_data: UserRegistrationRequestSchema,
        db: AsyncSession = Depends(get_db),
        email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> UserRegistrationResponseSchema:
    stmt = select(UserModel).where(UserModel.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists."
        )

    stmt = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
    result = await db.execute(stmt)
    user_group = result.scalars().first()
    if not user_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found."
        )

    try:
        new_user = UserModel.create(
            email=str(user_data.email),
            raw_password=user_data.password,
            group_id=user_group.id,
        )
        db.add(new_user)
        await db.flush()

        activation_token = ActivationTokenModel(user_id=new_user.id)
        db.add(activation_token)

        activation_link = f"https://your-domain.com/activate?email={new_user.email}&token={activation_token.token}"
        await email_sender.send_activation_email(
            email=new_user.email,
            activation_link=activation_link
        )

        await db.commit()
        await db.refresh(new_user)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation."
        ) from e

    return UserRegistrationResponseSchema.model_validate(new_user)


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
    summary="Request Password Reset Token",
    description=(
            "Allows a user to request a password reset token. If the user exists and is active, "
            "a new token will be generated and any existing tokens will be invalidated."
    ),
    status_code=status.HTTP_200_OK,
)
async def request_password_reset_token(
        data: PasswordResetRequestSchema,
        db: AsyncSession = Depends(get_db),
        email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> MessageResponseSchema:
    stmt = select(UserModel).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.is_active:
        return MessageResponseSchema(
            message="If you are registered, you will receive an email with instructions."
        )

    await db.execute(delete(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id))

    reset_token = PasswordResetTokenModel(user_id=cast(int, user.id))
    db.add(reset_token)
    await db.commit()

    reset_link = f"https://your-domain.com/reset-password?email={user.email}&token={reset_token.token}"
    await email_sender.send_password_reset_email(
        email=user.email,
        reset_link=reset_link
    )

    return MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    summary="Activate User Account",
    description="Activate a user's account using their email and activation token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The activation token is invalid or expired, "
                           "or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid or expired activation token."
                            }
                        },
                        "already_active": {
                            "summary": "Account Already Active",
                            "value": {
                                "detail": "User account is already active."
                            }
                        },
                    }
                }
            },
        },
    },
)
async def activate_account(
        activation_data: UserActivationRequestSchema,
        db: AsyncSession = Depends(get_db),
        email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> MessageResponseSchema:
    """
    Endpoint to activate a user's account.

    This endpoint verifies the activation token for a user by checking that the token record exists
    and that it has not expired. If the token is valid and the user's account is not already active,
    the user's account is activated and the activation token is deleted. If the token is invalid, expired,
    or if the account is already active, an HTTP 400 error is raised.

    Args:
        activation_data (UserActivationRequestSchema): Contains the user's email and activation token.
        db (AsyncSession): The asynchronous database session.

    Returns:
        MessageResponseSchema: A response message confirming successful activation.

    Raises:
        HTTPException:
            - 400 Bad Request if the activation token is invalid or expired.
            - 400 Bad Request if the user account is already active.
    """
    stmt = (
        select(ActivationTokenModel)
        .options(joinedload(ActivationTokenModel.user))
        .join(UserModel)
        .where(
            UserModel.email == activation_data.email,
            ActivationTokenModel.token == activation_data.token
        )
    )
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    now_utc = datetime.now(timezone.utc)
    if not token_record or cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc) < now_utc:
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token."
        )

    user = token_record.user
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active."
        )

    user.is_active = True
    await db.delete(token_record)
    await db.commit()

    try:
        login_link = f"https://your-domain.com/login"
        await email_sender.send_activation_complete_email(
            email=user.email,
            login_link=login_link
        )
    except Exception as e:
        print(f"Error sending activation complete email: {e}")

    return MessageResponseSchema(message="User account activated successfully.")


@router.post(
    "/activate/resend/",
    response_model=MessageResponseSchema,
    summary="Resend Activation Token",
    description="Resend a new activation token if the previous one has expired.",
    status_code=status.HTTP_200_OK,
)
async def resend_activation_token(
        data: ResendActivationRequestSchema,
        db: AsyncSession = Depends(get_db),
        email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> MessageResponseSchema:
    stmt = select(UserModel).where(UserModel.email == data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        return MessageResponseSchema(message="If you are registered, you will receive an email with instructions.")

    if user.is_active:
        return MessageResponseSchema(message="Account is already activated.")

    await db.execute(delete(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id))

    activation_token = ActivationTokenModel(user_id=user.id)
    db.add(activation_token)
    await db.commit()

    activation_link = f"https://your-domain.com/activate?email={user.email}&token={activation_token.token}"
    await email_sender.send_activation_email(
        email=user.email,
        activation_link=activation_link
    )

    return MessageResponseSchema(message="If you are registered, you will receive an email with instructions.")


@router.post(
    "/reset-password/complete/",
    response_model=MessageResponseSchema,
    summary="Reset User Password",
    description="Reset a user's password if a valid token is provided.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": (
                    "Bad Request - The provided email or token is invalid, "
                    "the token has expired, or the user account is not active."
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_email_or_token": {
                            "summary": "Invalid Email or Token",
                            "value": {
                                "detail": "Invalid email or token."
                            }
                        },
                        "expired_token": {
                            "summary": "Expired Token",
                            "value": {
                                "detail": "Invalid email or token."
                            }
                        }
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while resetting the password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while resetting the password."
                    }
                }
            },
        },
    },
)
async def reset_password(
        data: PasswordResetCompleteRequestSchema,
        db: AsyncSession = Depends(get_db),
        email_sender: EmailSenderInterface = Depends(get_accounts_email_notificator),
) -> MessageResponseSchema:
    """
    Endpoint for resetting a user's password.

    Validates the token and updates the user's password if the token is valid and not expired.
    Deletes the token after a successful password reset.

    Args:
        data (PasswordResetCompleteRequestSchema): The request data containing the user's email,
         token, and new password.
        db (AsyncSession): The asynchronous database session.

    Returns:
        MessageResponseSchema: A response message indicating successful password reset.

    Raises:
        HTTPException:
            - 400 Bad Request if the email or token is invalid, or the token has expired.
            - 500 Internal Server Error if an error occurs during the password reset process.
    """
    stmt = select(UserModel).filter_by(email=data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    stmt = select(PasswordResetTokenModel).filter_by(user_id=user.id)
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    if not token_record or token_record.token != data.token:
        if token_record:
            await db.run_sync(lambda s: s.delete(token_record))
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    expires_at = cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    try:
        user.password = data.password
        await db.run_sync(lambda s: s.delete(token_record))
        await db.commit()
        
        try:
            login_link = f"https://your-domain.com/login"
            await email_sender.send_password_reset_complete_email(
                email=user.email,
                login_link=login_link
            )
        except Exception as e:
            print(f"Error sending password reset complete email: {e}")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password."
        )

    return MessageResponseSchema(message="Password reset successfully.")


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    summary="User Login",
    description="Authenticate a user and return access and refresh tokens.",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid email or password."
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - User account is not activated.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User account is not activated."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while processing the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing the request."
                    }
                }
            },
        },
    },
)
async def login_user(
        login_data: UserLoginRequestSchema,
        db: AsyncSession = Depends(get_db),
        settings: BaseAppSettings = Depends(get_settings),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> UserLoginResponseSchema:
    """
    Endpoint for user login.

    Authenticates a user using their email and password.
    If authentication is successful, creates a new refresh token and returns both access and refresh tokens.

    Args:
        login_data (UserLoginRequestSchema): The login credentials.
        db (AsyncSession): The asynchronous database session.
        settings (BaseAppSettings): The application settings.
        jwt_manager (JWTAuthManagerInterface): The JWT authentication manager.

    Returns:
        UserLoginResponseSchema: A response containing the access and refresh tokens.

    Raises:
        HTTPException:
            - 401 Unauthorized if the email or password is invalid.
            - 403 Forbidden if the user account is not activated.
            - 500 Internal Server Error if an error occurs during token creation.
    """
    stmt = select(UserModel).filter_by(email=login_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated.",
        )

    jwt_refresh_token = jwt_manager.create_refresh_token({"user_id": user.id})

    try:
        refresh_token = RefreshTokenModel.create(
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=jwt_refresh_token
        )
        db.add(refresh_token)
        await db.flush()
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )

    jwt_access_token = jwt_manager.create_access_token({"user_id": user.id})
    return UserLoginResponseSchema(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token,
    )


@router.post(
    "/refresh/",
    response_model=TokenRefreshResponseSchema,
    summary="Refresh Access Token",
    description="Refresh the access token using a valid refresh token.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The provided refresh token is invalid or expired.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Token has expired."
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Refresh token not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Refresh token not found."
                    }
                }
            },
        },
        404: {
            "description": "Not Found - The user associated with the token does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found."
                    }
                }
            },
        },
    },
)
async def refresh_access_token(
        token_data: TokenRefreshRequestSchema,
        db: AsyncSession = Depends(get_db),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> TokenRefreshResponseSchema:
    """
    Endpoint to refresh an access token.

    Validates the provided refresh token, extracts the user ID from it, and issues
    a new access token. If the token is invalid or expired, an error is returned.

    Args:
        token_data (TokenRefreshRequestSchema): Contains the refresh token.
        db (AsyncSession): The asynchronous database session.
        jwt_manager (JWTAuthManagerInterface): JWT authentication manager.

    Returns:
        TokenRefreshResponseSchema: A new access token.

    Raises:
        HTTPException:
            - 400 Bad Request if the token is invalid or expired.
            - 401 Unauthorized if the refresh token is not found.
            - 404 Not Found if the user associated with the token does not exist.
    """
    try:
        decoded_token = jwt_manager.decode_refresh_token(token_data.refresh_token)
        user_id = decoded_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    stmt = select(RefreshTokenModel).filter_by(token=token_data.refresh_token)
    result = await db.execute(stmt)
    refresh_token_record = result.scalars().first()
    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found.",
        )

    stmt = select(UserModel).filter_by(id=user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    new_access_token = jwt_manager.create_access_token({"user_id": user_id})

    return TokenRefreshResponseSchema(access_token=new_access_token)


@router.post(
    "/logout/",
    response_model=MessageResponseSchema,
    summary="User Logout",
    description="Invalidate the user's refresh token to log them out securely.",
    status_code=status.HTTP_200_OK,
)
async def logout_user(
        refresh_data: TokenRefreshRequestSchema,
        db: AsyncSession = Depends(get_db),
        jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> MessageResponseSchema:
    """
    Logout the user by deleting the provided refresh token from the database.

    Args:
        refresh_data (TokenRefreshRequestSchema): The refresh token to invalidate.
        db (AsyncSession): Database session.
        jwt_manager (JWTAuthManagerInterface): JWT manager to validate tokens.

    Returns:
        MessageResponseSchema: Confirmation message.
    """
    try:
        payload = jwt_manager.decode_refresh_token(refresh_data.refresh_token)
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload.")

        stmt = delete(RefreshTokenModel).where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.token == refresh_data.refresh_token,
        )
        await db.execute(stmt)
        await db.commit()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to logout. Invalid or expired token."
        )

    return MessageResponseSchema(message="Successfully logged out.")


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect."
        )
    validate_password_strength(data.new_password)
    current_user.hashed_password = hash_password(data.new_password)
    db.add(current_user)
    await db.commit()
    return {"detail": "Password changed successfully."}


class ChangeUserGroupRequest(BaseModel):
    group: UserGroupEnum


@router.post(
    "/admin/users/{user_id}/activate",
    response_model=MessageResponseSchema,
    summary="Admin: Activate user account",
    description="Activate a user account manually (admin only)",
    responses={
        200: {
            "description": "User activated successfully.",
            "content": {
                "application/json": {
                    "example": {"message": "User activated successfully."}
                }
            },
        },
        404: {
            "description": "User not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found"}
                }
            },
        },
    },
)
async def admin_activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin),
):
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active:
        return MessageResponseSchema(message="User is already active.")
    user.is_active = True
    await db.commit()
    return MessageResponseSchema(message="User activated successfully.")


@router.post(
    "/admin/users/{user_id}/change-group",
    response_model=MessageResponseSchema,
    summary="Admin: Change user group",
    description="Change a user's group (admin only)",
    responses={
        200: {
            "description": "User group changed successfully.",
            "content": {
                "application/json": {
                    "example": {"message": "User group changed to moderator."}
                }
            },
        },
        404: {
            "description": "User or group not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found"}
                }
            },
        },
    },
)
async def admin_change_user_group(
    user_id: int,
    data: ChangeUserGroupRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin),
):
    """
    Change a user's group. Example request body:
    {
        "group": "moderator"
    }
    """
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    group = await db.scalar(select(UserGroupModel).where(UserGroupModel.name == data.group))
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    user.group_id = group.id
    await db.commit()
    return MessageResponseSchema(message=f"User group changed to {data.group.value}.")

# --- Endpoint-и для сповіщень ---
@router.get(
    "/notifications/",
    response_model=list[NotificationSchema],
    summary="Get user notifications",
    description="Get all notifications for the current user."
)
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    stmt = select(NotificationModel).where(
        NotificationModel.user_id == current_user.id
    ).order_by(NotificationModel.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.patch(
    "/notifications/{notification_id}",
    response_model=NotificationSchema,
    summary="Mark notification as read",
    description="Mark a notification as read or unread."
)
async def update_notification(
    notification_id: int,
    data: NotificationUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    notification = await db.get(NotificationModel, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your own notifications.")
    notification.is_read = data.is_read
    await db.commit()
    await db.refresh(notification)
    return notification

@router.delete(
    "/notifications/{notification_id}",
    status_code=204,
    summary="Delete notification",
    description="Delete a notification."
)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    notification = await db.get(NotificationModel, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own notifications.")
    await db.delete(notification)
    await db.commit()

# --- Admin endpoints for cart management ---
@router.get(
    "/admin/users/{user_id}/cart",
    response_model=dict,
    summary="Admin: Get user's cart",
    description="Get the contents of a specific user's shopping cart (admin only)",
    responses={
        200: {
            "description": "User's cart contents.",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": 1,
                        "cart_items": [
                            {"movie_id": 1, "movie_title": "Inception", "price": 9.99}
                        ],
                        "total_price": 9.99
                    }
                }
            },
        },
        404: {
            "description": "User or cart not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found"}
                }
            },
        },
    },
)
async def admin_get_user_cart(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin),
):
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    cart_stmt = select(CartModel).where(CartModel.user_id == user_id)
    cart_result = await db.execute(cart_stmt)
    cart = cart_result.scalars().first()
    
    if not cart:
        return {
            "user_id": user_id,
            "cart_items": [],
            "total_price": 0.0
        }
    
    cart_items = []
    total_price = 0.0
    
    for item in cart.items:
        cart_items.append({
            "movie_id": item.movie_id,
            "movie_title": item.movie.name,
            "price": float(item.movie.price)
        })
        total_price += float(item.movie.price)
    
    return {
        "user_id": user_id,
        "cart_items": cart_items,
        "total_price": total_price
    }

@router.get(
    "/admin/users/{user_id}/purchased",
    response_model=list[dict],
    summary="Admin: Get user's purchased movies",
    description="Get all movies purchased by a specific user (admin only)",
    responses={
        200: {
            "description": "User's purchased movies.",
            "content": {
                "application/json": {
                    "example": [
                        {"movie_id": 1, "movie_title": "Inception", "purchased_at": "2024-01-01T12:00:00Z", "price_paid": 9.99}
                    ]
                }
            },
        },
        404: {
            "description": "User not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found"}
                }
            },
        },
    },
)
async def admin_get_user_purchased_movies(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserModel = Depends(get_current_admin),
):
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    stmt = select(PurchasedMovieModel).where(PurchasedMovieModel.user_id == user_id)
    result = await db.execute(stmt)
    purchased_movies = result.scalars().all()
    
    return [
        {
            "movie_id": pm.movie_id,
            "movie_title": pm.movie.name,
            "purchased_at": pm.purchased_at,
            "price_paid": float(pm.price_paid)
        }
        for pm in purchased_movies
    ]
