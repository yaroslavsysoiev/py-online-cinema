from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from database.models.movies import ActorModel
from schemas.movies import (
    ActorSchema,
)

router = APIRouter(prefix="/actors", tags=["actors"])


@router.post("/", response_model=ActorSchema, status_code=status.HTTP_201_CREATED)
async def create_actor(data: ActorSchema, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(ActorModel).where(ActorModel.name == data.name))
    if existing.scalars().first():
        raise HTTPException(
            status_code=409, detail="Actor with this name already exists."
        )
    actor = ActorModel(name=data.name)
    db.add(actor)
    await db.commit()
    await db.refresh(actor)
    return actor


@router.get("/", response_model=list[ActorSchema])
async def list_actors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ActorModel))
    return result.scalars().all()


@router.get("/{actor_id}", response_model=ActorSchema)
async def get_actor(actor_id: int, db: AsyncSession = Depends(get_db)):
    actor = await db.get(ActorModel, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found.")
    return actor


@router.patch("/{actor_id}", response_model=ActorSchema)
async def update_actor(
    actor_id: int, data: ActorSchema, db: AsyncSession = Depends(get_db)
):
    actor = await db.get(ActorModel, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found.")
    actor.name = data.name
    await db.commit()
    await db.refresh(actor)
    return actor


@router.delete("/{actor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_actor(actor_id: int, db: AsyncSession = Depends(get_db)):
    actor = await db.get(ActorModel, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found.")
    await db.delete(actor)
    await db.commit()
