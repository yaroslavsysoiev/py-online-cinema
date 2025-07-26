from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.database import get_db
from src.database.models.movies import GenreModel, MoviesGenresModel, MovieModel
from src.schemas.movies import (
    GenreSchema,
)

router = APIRouter(prefix="/genres", tags=["genres"])


@router.post("/", response_model=GenreSchema, status_code=status.HTTP_201_CREATED)
async def create_genre(data: GenreSchema, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(GenreModel).where(GenreModel.name == data.name))
    if existing.scalars().first():
        raise HTTPException(
            status_code=409, detail="Genre with this name already exists."
        )
    genre = GenreModel(name=data.name)
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return genre


@router.get("/", response_model=list[GenreSchema])
async def list_genres(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GenreModel))
    return result.scalars().all()


@router.get("/{genre_id}", response_model=GenreSchema)
async def get_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    genre = await db.get(GenreModel, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found.")
    return genre


@router.patch("/{genre_id}", response_model=GenreSchema)
async def update_genre(
    genre_id: int, data: GenreSchema, db: AsyncSession = Depends(get_db)
):
    genre = await db.get(GenreModel, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found.")
    genre.name = data.name
    await db.commit()
    await db.refresh(genre)
    return genre


@router.delete("/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    genre = await db.get(GenreModel, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found.")
    await db.delete(genre)
    await db.commit()


# Endpoint to get genres with movie count
@router.get("/with-count/", response_model=list[dict])
async def genres_with_movie_count(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            GenreModel.id,
            GenreModel.name,
            func.count(MoviesGenresModel.c.movie_id).label("movie_count"),
        )
        .join(MoviesGenresModel, GenreModel.id == MoviesGenresModel.c.genre_id)
        .group_by(GenreModel.id)
    )
    result = await db.execute(stmt)
    return [
        {"id": row[0], "name": row[1], "movie_count": row[2]} for row in result.all()
    ]
