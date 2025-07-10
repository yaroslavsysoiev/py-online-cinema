from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, aliased

from database import get_db, MovieModel
from database import (
    CountryModel,
    GenreModel,
    ActorModel,
    LanguageModel
)
from database.models.movies import MovieLikeModel
from database.models.movies import FavoriteMovieModel
from schemas import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieDetailSchema
)
from schemas.movies import MovieCreateSchema, MovieUpdateSchema, MovieLikeRequestSchema, MovieLikeCountSchema
from config.dependencies import get_current_user

router = APIRouter()


@router.get(
    "/movies/",
    response_model=MovieListResponseSchema,
    summary="Get a paginated list of movies with filtering, sorting, and searching",
    description="Retrieve a paginated list of movies with optional filters, sorting, and search.",
    responses={
        404: {
            "description": "No movies found.",
            "content": {
                "application/json": {
                    "example": {"detail": "No movies found."}
                }
            },
        }
    }
)
async def get_movie_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    year: int = Query(None, description="Release year to filter by"),
    imdb_min: float = Query(None, description="Minimum IMDb rating"),
    imdb_max: float = Query(None, description="Maximum IMDb rating"),
    price_min: float = Query(None, description="Minimum price"),
    price_max: float = Query(None, description="Maximum price"),
    sort_by: str = Query(None, description="Sort by field: price, date, popularity, imdb, etc."),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    search: str = Query(None, description="Search in title, description, actor, or director"),
    genre: str = Query(None, description="Filter by genre name"),
    star: str = Query(None, description="Filter by star/actor name"),
    director: str = Query(None, description="Filter by director name"),
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    offset = (page - 1) * per_page

    stmt = select(MovieModel)

    # Filtering
    if year:
        stmt = stmt.where(MovieModel.date == year)  # If 'date' is a date, you may need to extract year
    if imdb_min is not None:
        stmt = stmt.where(MovieModel.score >= imdb_min)
    if imdb_max is not None:
        stmt = stmt.where(MovieModel.score <= imdb_max)
    if price_min is not None:
        stmt = stmt.where(MovieModel.budget >= price_min)  # Or use 'price' if you have it
    if price_max is not None:
        stmt = stmt.where(MovieModel.budget <= price_max)  # Or use 'price' if you have it
    if genre:
        stmt = stmt.join(MovieModel.genres).where(GenreModel.name.ilike(f"%{genre}%"))
    if star:
        stmt = stmt.join(MovieModel.actors).where(ActorModel.name.ilike(f"%{star}%"))
    # Remove director filter if DirectorModel is not defined

    # Searching
    if search:
        stmt = stmt.where(
            (MovieModel.name.ilike(f"%{search}%")) |
            (MovieModel.overview.ilike(f"%{search}%")) |
            (MovieModel.actors.any(ActorModel.name.ilike(f"%{search}%")))
            # Add director search if DirectorModel is defined
        )

    # Sorting
    sort_map = {
        "price": MovieModel.budget,  # Or use 'price' if you have it
        "date": MovieModel.date,
        "popularity": MovieModel.score,  # Or use 'votes' if you have it
        "imdb": MovieModel.score,
    }
    if sort_by in sort_map:
        sort_column = sort_map[sort_by]
        if sort_order == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(MovieModel.id.desc())

    # Count total items
    count_stmt = stmt.with_only_columns(func.count()).order_by(None)
    result_count = await db.execute(count_stmt)
    total_items = result_count.scalar() or 0
    if not total_items:
        raise HTTPException(status_code=404, detail="No movies found.")

    # Pagination
    stmt = stmt.offset(offset).limit(per_page)
    result_movies = await db.execute(stmt)
    movies = result_movies.scalars().all()
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]
    total_pages = (total_items + per_page - 1) // per_page
    response = MovieListResponseSchema(
        movies=movie_list,
        prev_page=f"/theater/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/theater/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )
    return response


@router.post(
    "/movies/",
    response_model=MovieDetailSchema,
    summary="Add a new movie",
    description=(
            "<h3>This endpoint allows clients to add a new movie to the database. "
            "It accepts details such as name, date, genres, actors, languages, and "
            "other attributes. The associated country, genres, actors, and languages "
            "will be created or linked automatically.</h3>"
    ),
    responses={
        201: {
            "description": "Movie created successfully.",
        },
        400: {
            "description": "Invalid input.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid input data."}
                }
            },
        }
    },
    status_code=201
)
async def create_movie(
        movie_data: MovieCreateSchema,
        db: AsyncSession = Depends(get_db)
) -> MovieDetailSchema:
    """
    Add a new movie to the database.

    This endpoint allows the creation of a new movie with details such as
    name, release date, genres, actors, and languages. It automatically
    handles linking or creating related entities.

    :param movie_data: The data required to create a new movie.
    :type movie_data: MovieCreateSchema
    :param db: The SQLAlchemy async database session (provided via dependency injection).
    :type db: AsyncSession

    :return: The created movie with all details.
    :rtype: MovieDetailSchema

    :raises HTTPException:
        - 409 if a movie with the same name and date already exists.
        - 400 if input data is invalid (e.g., violating a constraint).
    """
    existing_stmt = select(MovieModel).where(
        (MovieModel.name == movie_data.name),
        (MovieModel.date == movie_data.date)
    )
    existing_result = await db.execute(existing_stmt)
    existing_movie = existing_result.scalars().first()

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A movie with the name '{movie_data.name}' and release date "
                f"'{movie_data.date}' already exists."
            )
        )

    try:
        country_stmt = select(CountryModel).where(CountryModel.code == movie_data.country)
        country_result = await db.execute(country_stmt)
        country = country_result.scalars().first()
        if not country:
            country = CountryModel(code=movie_data.country)
            db.add(country)
            await db.flush()

        genres = []
        for genre_name in movie_data.genres:
            genre_stmt = select(GenreModel).where(GenreModel.name == genre_name)
            genre_result = await db.execute(genre_stmt)
            genre = genre_result.scalars().first()

            if not genre:
                genre = GenreModel(name=genre_name)
                db.add(genre)
                await db.flush()
            genres.append(genre)

        actors = []
        for actor_name in movie_data.actors:
            actor_stmt = select(ActorModel).where(ActorModel.name == actor_name)
            actor_result = await db.execute(actor_stmt)
            actor = actor_result.scalars().first()

            if not actor:
                actor = ActorModel(name=actor_name)
                db.add(actor)
                await db.flush()
            actors.append(actor)

        languages = []
        for language_name in movie_data.languages:
            lang_stmt = select(LanguageModel).where(LanguageModel.name == language_name)
            lang_result = await db.execute(lang_stmt)
            language = lang_result.scalars().first()

            if not language:
                language = LanguageModel(name=language_name)
                db.add(language)
                await db.flush()
            languages.append(language)

        movie = MovieModel(
            name=movie_data.name,
            date=movie_data.date,
            score=movie_data.score,
            overview=movie_data.overview,
            status=movie_data.status,
            budget=movie_data.budget,
            revenue=movie_data.revenue,
            country=country,
            genres=genres,
            actors=actors,
            languages=languages,
        )
        db.add(movie)
        await db.commit()
        await db.refresh(movie, ["genres", "actors", "languages"])

        return MovieDetailSchema.model_validate(movie)

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Get movie details by ID",
    description=(
            "<h3>Fetch detailed information about a specific movie by its unique ID. "
            "This endpoint retrieves all available details for the movie, such as "
            "its name, genre, crew, budget, and revenue. If the movie with the given "
            "ID is not found, a 404 error will be returned.</h3>"
    ),
    responses={
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        }
    }
)
async def get_movie_by_id(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    """
    Retrieve detailed information about a specific movie by its ID.

    This function fetches detailed information about a movie identified by its unique ID.
    If the movie does not exist, a 404 error is returned.

    :param movie_id: The unique identifier of the movie to retrieve.
    :type movie_id: int
    :param db: The SQLAlchemy database session (provided via dependency injection).
    :type db: AsyncSession

    :return: The details of the requested movie.
    :rtype: MovieDetailResponseSchema

    :raises HTTPException: Raises a 404 error if the movie with the given ID is not found.
    """
    stmt = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )

    result = await db.execute(stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    return MovieDetailSchema.model_validate(movie)


@router.delete(
    "/movies/{movie_id}/",
    summary="Delete a movie by ID",
    description=(
            "<h3>Delete a specific movie from the database by its unique ID.</h3>"
            "<p>If the movie exists, it will be deleted. If it does not exist, "
            "a 404 error will be returned.</p>"
    ),
    responses={
        204: {
            "description": "Movie deleted successfully."
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
    },
    status_code=204
)
async def delete_movie(
        movie_id: int,
        db: AsyncSession = Depends(get_db),
):
    """
    Delete a specific movie by its ID.

    This function deletes a movie identified by its unique ID.
    If the movie does not exist, a 404 error is raised.

    :param movie_id: The unique identifier of the movie to delete.
    :type movie_id: int
    :param db: The SQLAlchemy database session (provided via dependency injection).
    :type db: AsyncSession

    :raises HTTPException: Raises a 404 error if the movie with the given ID is not found.

    :return: A response indicating the successful deletion of the movie.
    :rtype: None
    """
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()

    return {"detail": "Movie deleted successfully."}


@router.patch(
    "/movies/{movie_id}/",
    summary="Update a movie by ID",
    description=(
            "<h3>Update details of a specific movie by its unique ID.</h3>"
            "<p>This endpoint updates the details of an existing movie. If the movie with "
            "the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        200: {
            "description": "Movie updated successfully.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie updated successfully."}
                }
            },
        },
        404: {
            "description": "Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie with the given ID was not found."}
                }
            },
        },
    }
)
async def update_movie(
        movie_id: int,
        movie_data: MovieUpdateSchema,
        db: AsyncSession = Depends(get_db),
):
    """
    Update a specific movie by its ID.

    This function updates a movie identified by its unique ID.
    If the movie does not exist, a 404 error is raised.

    :param movie_id: The unique identifier of the movie to update.
    :type movie_id: int
    :param movie_data: The updated data for the movie.
    :type movie_data: MovieUpdateSchema
    :param db: The SQLAlchemy database session (provided via dependency injection).
    :type db: AsyncSession

    :raises HTTPException: Raises a 404 error if the movie with the given ID is not found.

    :return: A response indicating the successful update of the movie.
    :rtype: None
    """
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie with the given ID was not found."
        )

    for field, value in movie_data.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)

    try:
        await db.commit()
        await db.refresh(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")

    return {"detail": "Movie updated successfully."}


@router.post(
    "/movies/{movie_id}/like",
    response_model=None,
    summary="Like or dislike a movie",
    description="Like or dislike a movie. User can only have one like/dislike per movie.",
    status_code=204
)
async def like_or_dislike_movie(
    movie_id: int,
    data: MovieLikeRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    stmt = select(MovieLikeModel).where(
        MovieLikeModel.user_id == current_user.id,
        MovieLikeModel.movie_id == movie_id
    )
    result = await db.execute(stmt)
    like_obj = result.scalars().first()

    if like_obj:
        like_obj.is_like = data.is_like
    else:
        like_obj = MovieLikeModel(user_id=current_user.id, movie_id=movie_id, is_like=data.is_like)
        db.add(like_obj)
    await db.commit()
    return


@router.get(
    "/movies/{movie_id}/likes",
    response_model=MovieLikeCountSchema,
    summary="Get like/dislike counts for a movie",
    description="Get the number of likes and dislikes for a movie."
)
async def get_movie_like_counts(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MovieLikeModel.is_like, func.count()).where(MovieLikeModel.movie_id == movie_id).group_by(MovieLikeModel.is_like)
    result = await db.execute(stmt)
    counts = dict(result.all())
    return MovieLikeCountSchema(
        likes=counts.get(True, 0),
        dislikes=counts.get(False, 0)
    )


@router.post(
    "/movies/{movie_id}/favorite",
    status_code=204,
    summary="Add a movie to favorites",
    description="Add a movie to the authenticated user's favorites list."
)
async def add_movie_to_favorites(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    exists_stmt = select(FavoriteMovieModel).where(
        FavoriteMovieModel.user_id == current_user.id,
        FavoriteMovieModel.movie_id == movie_id
    )
    result = await db.execute(exists_stmt)
    favorite = result.scalars().first()
    if favorite:
        return  # Already in favorites
    favorite = FavoriteMovieModel(user_id=current_user.id, movie_id=movie_id)
    db.add(favorite)
    await db.commit()
    return


@router.delete(
    "/movies/{movie_id}/favorite",
    status_code=204,
    summary="Remove a movie from favorites",
    description="Remove a movie from the authenticated user's favorites list."
)
async def remove_movie_from_favorites(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    stmt = select(FavoriteMovieModel).where(
        FavoriteMovieModel.user_id == current_user.id,
        FavoriteMovieModel.movie_id == movie_id
    )
    result = await db.execute(stmt)
    favorite = result.scalars().first()
    if not favorite:
        return  # Not in favorites
    await db.delete(favorite)
    await db.commit()
    return


@router.get(
    "/favorites/",
    response_model=MovieListResponseSchema,
    summary="List user's favorite movies with catalog functions",
    description="List the authenticated user's favorite movies with support for search, filter, sort, and pagination."
)
async def list_favorite_movies(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    year: int = Query(None, description="Release year to filter by"),
    imdb_min: float = Query(None, description="Minimum IMDb rating"),
    imdb_max: float = Query(None, description="Maximum IMDb rating"),
    price_min: float = Query(None, description="Minimum price"),
    price_max: float = Query(None, description="Maximum price"),
    sort_by: str = Query(None, description="Sort by field: price, date, popularity, imdb, etc."),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    search: str = Query(None, description="Search in title, description, actor, or director"),
    genre: str = Query(None, description="Filter by genre name"),
    star: str = Query(None, description="Filter by star/actor name"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
) -> MovieListResponseSchema:
    offset = (page - 1) * per_page
    # Get favorite movie IDs for the user
    stmt_fav = select(FavoriteMovieModel.movie_id).where(FavoriteMovieModel.user_id == current_user.id)
    result_fav = await db.execute(stmt_fav)
    favorite_ids = [row[0] for row in result_fav.all()]
    if not favorite_ids:
        return MovieListResponseSchema(movies=[], prev_page=None, next_page=None, total_pages=0, total_items=0)
    # Build the movie query with filters, search, sort
    stmt = select(MovieModel).where(MovieModel.id.in_(favorite_ids))
    if year:
        stmt = stmt.where(MovieModel.date == year)
    if imdb_min is not None:
        stmt = stmt.where(MovieModel.score >= imdb_min)
    if imdb_max is not None:
        stmt = stmt.where(MovieModel.score <= imdb_max)
    if price_min is not None:
        stmt = stmt.where(MovieModel.budget >= price_min)
    if price_max is not None:
        stmt = stmt.where(MovieModel.budget <= price_max)
    if genre:
        stmt = stmt.join(MovieModel.genres).where(GenreModel.name.ilike(f"%{genre}%"))
    if star:
        stmt = stmt.join(MovieModel.actors).where(ActorModel.name.ilike(f"%{star}%"))
    if search:
        stmt = stmt.where(
            (MovieModel.name.ilike(f"%{search}%")) |
            (MovieModel.overview.ilike(f"%{search}%")) |
            (MovieModel.actors.any(ActorModel.name.ilike(f"%{search}%")))
        )
    sort_map = {
        "price": MovieModel.budget,
        "date": MovieModel.date,
        "popularity": MovieModel.score,
        "imdb": MovieModel.score,
    }
    if sort_by in sort_map:
        sort_column = sort_map[sort_by]
        if sort_order == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(MovieModel.id.desc())
    count_stmt = stmt.with_only_columns(func.count()).order_by(None)
    result_count = await db.execute(count_stmt)
    total_items = result_count.scalar() or 0
    if not total_items:
        return MovieListResponseSchema(movies=[], prev_page=None, next_page=None, total_pages=0, total_items=0)
    stmt = stmt.offset(offset).limit(per_page)
    result_movies = await db.execute(stmt)
    movies = result_movies.scalars().all()
    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]
    total_pages = (total_items + per_page - 1) // per_page
    response = MovieListResponseSchema(
        movies=movie_list,
        prev_page=f"/favorites/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/favorites/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )
    return response
