from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from database.models.movies import DirectorModel
from schemas.movies import DirectorSchema, DirectorCreateSchema, DirectorUpdateSchema

router = APIRouter(prefix="/directors", tags=["directors"])


@router.post("/", response_model=DirectorSchema, status_code=status.HTTP_201_CREATED)
async def create_director(
    data: DirectorCreateSchema, db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(
        select(DirectorModel).where(DirectorModel.name == data.name)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=409, detail="Director with this name already exists."
        )
    director = DirectorModel(name=data.name)
    db.add(director)
    await db.commit()
    await db.refresh(director)
    return director


@router.get("/", response_model=list[DirectorSchema])
async def list_directors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DirectorModel))
    return result.scalars().all()


@router.get("/{director_id}", response_model=DirectorSchema)
async def get_director(director_id: int, db: AsyncSession = Depends(get_db)):
    director = await db.get(DirectorModel, director_id)
    if not director:
        raise HTTPException(status_code=404, detail="Director not found.")
    return director


@router.patch("/{director_id}", response_model=DirectorSchema)
async def update_director(
    director_id: int, data: DirectorUpdateSchema, db: AsyncSession = Depends(get_db)
):
    director = await db.get(DirectorModel, director_id)
    if not director:
        raise HTTPException(status_code=404, detail="Director not found.")
    director.name = data.name
    await db.commit()
    await db.refresh(director)
    return director


@router.delete("/{director_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_director(director_id: int, db: AsyncSession = Depends(get_db)):
    director = await db.get(DirectorModel, director_id)
    if not director:
        raise HTTPException(status_code=404, detail="Director not found.")
    await db.delete(director)
    await db.commit()
