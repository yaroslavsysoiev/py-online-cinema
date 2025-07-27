import aioboto3
import pytest
import os
from io import BytesIO
from PIL import Image
from sqlalchemy import select, insert

from database import UserModel, UserProfileModel, UserGroupEnum, UserGroupModel


@pytest.mark.e2e
@pytest.mark.order(7)
@pytest.mark.asyncio
async def test_create_user_profile(e2e_client, e2e_db_session, settings, s3_client, seed_user_groups):
    """
    End-to-end test for creating a user profile with avatar upload (async + aioboto3.Session version).

    Steps:
    1. Authenticate a test user.
    2. Upload an avatar via `POST /users/{user_id}/profile/`.
    3. Verify that the profile was created successfully.
    4. Verify that the avatar URL is valid.
    5. Connect directly to MinIO (via aioboto3) and verify that the file exists.
    """

    user_email = "test@mate.com"
    user_password = "NewSecurePassword123!"

    stmt_user = select(UserModel).where(UserModel.email == user_email)
    result_user = await e2e_db_session.execute(stmt_user)
    user = result_user.scalars().first()
    
    if not user:
        stmt_group = select(UserGroupModel).where(UserGroupModel.name == UserGroupEnum.USER)
        result_group = await e2e_db_session.execute(stmt_group)
        user_group = result_group.scalars().first()
        
        user = UserModel.create(email=user_email, raw_password=user_password, group_id=user_group.id)
        user.is_active = True
        e2e_db_session.add(user)
        await e2e_db_session.commit()
        
        stmt_user = select(UserModel).where(UserModel.email == user_email)
        result_user = await e2e_db_session.execute(stmt_user)
        user = result_user.scalars().first()

    assert user, f"User {user_email} should exist!"

    login_url = "/api/v1/accounts/login/"
    login_response = await e2e_client.post(login_url, json={"email": user_email, "password": user_password})
    assert login_response.status_code == 201, f"Expected 201, got {login_response.status_code}"

    tokens = login_response.json()
    access_token = tokens["access_token"]

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    profile_url = f"/api/v1/profiles/users/{user.id}/profile/"
    headers = {"Authorization": f"Bearer {access_token}"}

    files = {
        "first_name": (None, "John"),
        "last_name": (None, "Doe"),
        "gender": (None, "man"),
        "date_of_birth": (None, "1990-01-01"),
        "info": (None, "This is a test profile."),
        "avatar": ("avatar.jpg", img_bytes, "image/jpeg"),
    }

    profile_response = await e2e_client.post(profile_url, headers=headers, files=files)
    assert profile_response.status_code == 201, f"Expected 201, got {profile_response.status_code}"

    profile_data = profile_response.json()
    assert profile_data["first_name"] == "john"
    assert profile_data["last_name"] == "doe"
    assert profile_data["gender"] == "man"
    assert profile_data["date_of_birth"] == "1990-01-01"
    assert "avatar" in profile_data, "Avatar URL is missing!"

    avatar_key = f"avatars/{user.id}_avatar.jpg"
    expected_url = await s3_client.get_file_url(avatar_key)
    assert profile_data["avatar"] == expected_url, f"Invalid avatar URL: {profile_data['avatar']}"

    stmt_profile = select(UserProfileModel).where(UserProfileModel.user_id == user.id)
    result_profile = await e2e_db_session.execute(stmt_profile)
    profile_in_db = result_profile.scalars().first()
    assert profile_in_db, f"Profile for user {user.id} should exist!"
    assert profile_in_db.avatar, "Avatar path should not be empty!"

    await e2e_db_session.commit()

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        aws_access_key_id=settings.S3_STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.S3_STORAGE_SECRET_KEY
    ) as s3:
        response = await s3.list_objects_v2(
            Bucket=settings.S3_BUCKET_NAME,
            Prefix=avatar_key
        )

    assert "Contents" in response, f"Avatar {avatar_key} was not found in MinIO!"
