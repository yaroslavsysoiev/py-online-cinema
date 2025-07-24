from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db, UserProfileModel, UserModel
from schemas.profiles import ProfileCreateSchema, ProfileResponseSchema
from config.dependencies import get_current_user, get_s3_storage_client
from storages import S3StorageInterface

router = APIRouter(prefix="/profiles", tags=["profiles"])

@router.get("/me", response_model=ProfileResponseSchema)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = select(UserProfileModel).where(UserProfileModel.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return ProfileResponseSchema.model_validate(profile, from_attributes=True)

@router.post("/", response_model=ProfileResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreateSchema = Depends(ProfileCreateSchema.from_form),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    s3: S3StorageInterface = Depends(get_s3_storage_client),
):
    stmt = select(UserProfileModel).where(UserProfileModel.user_id == current_user.id)
    result = await db.execute(stmt)
    existing_profile = result.scalars().first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Profile already exists.")
    # Зберігаємо аватар у S3
    avatar_file = profile_data.avatar
    avatar_bytes = await avatar_file.read()
    await s3.upload_file(avatar_file.filename, avatar_bytes)
    avatar_url = await s3.get_file_url(avatar_file.filename)
    profile = UserProfileModel(
        user_id=current_user.id,
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        gender=profile_data.gender,
        date_of_birth=profile_data.date_of_birth,
        info=profile_data.info,
        avatar=avatar_url,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return ProfileResponseSchema.model_validate(profile)

@router.post("/users/{user_id}/profile/", response_model=ProfileResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_user_profile(
    user_id: int,
    profile_data: ProfileCreateSchema = Depends(ProfileCreateSchema.from_form),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    s3: S3StorageInterface = Depends(get_s3_storage_client),
):
    # Only the owner can create a profile for themselves
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to create a profile for another user.")
    # Only active users can create a profile
    if not current_user.is_active:
        raise HTTPException(status_code=401, detail="User not found or not active.")
    stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    result = await db.execute(stmt)
    existing_profile = result.scalars().first()
    if existing_profile:
        raise HTTPException(status_code=400, detail="Profile already exists.")
    # Save avatar to S3
    avatar_file = profile_data.avatar
    avatar_bytes = await avatar_file.read()
    await s3.upload_file(avatar_file.filename, avatar_bytes)
    avatar_url = await s3.get_file_url(avatar_file.filename)
    profile = UserProfileModel(
        user_id=user_id,
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        gender=profile_data.gender,
        date_of_birth=profile_data.date_of_birth,
        info=profile_data.info,
        avatar=avatar_url,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return ProfileResponseSchema.model_validate(profile, from_attributes=True)

@router.get("/users/{user_id}/profile/", response_model=ProfileResponseSchema)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return ProfileResponseSchema.model_validate(profile, from_attributes=True) 