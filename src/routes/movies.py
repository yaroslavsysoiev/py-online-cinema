from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, aliased
from datetime import datetime, date

from database import get_db, MovieModel
from database import (
    CountryModel,
    GenreModel,
    ActorModel,
    LanguageModel
)
from database.models.movies import MovieLikeModel, FavoriteMovieModel, MovieRatingModel, MovieCommentModel, MovieCommentLikeModel, DirectorModel, CartModel, CartItemModel, PurchasedMovieModel
from schemas import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieDetailSchema
)
from schemas.movies import MovieCreateSchema, MovieUpdateSchema, MovieLikeRequestSchema, MovieLikeCountSchema, MovieRatingCreateSchema, MovieRatingResponseSchema, MovieRatingAverageSchema, MovieCommentCreateSchema, MovieCommentResponseSchema, MovieCommentLikeRequestSchema, MovieCommentLikeCountSchema, CartItemCreateSchema, CartSchema, PurchasedMovieSchema
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
    if director:
        stmt = stmt.join(MovieModel.directors).where(DirectorModel.name.ilike(f"%{director}%"))

    # Searching
    if search:
        stmt = stmt.where(
            (MovieModel.name.ilike(f"%{search}%")) |
            (MovieModel.overview.ilike(f"%{search}%")) |
            (MovieModel.actors.any(ActorModel.name.ilike(f"%{search}%"))) |
            (MovieModel.directors.any(DirectorModel.name.ilike(f"%{search}%")))
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
    response = MovieDetailSchema.model_validate(movie, from_attributes=True).model_dump()
    if isinstance(movie.date, (datetime, date)):
        response['date'] = movie.date.isoformat()
    return response


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
    If the movie has been purchased by at least one user, deletion is prevented.
    If the movie is in users' carts, a warning is provided.

    :param movie_id: The unique identifier of the movie to delete.
    :type movie_id: int
    :param db: The SQLAlchemy database session (provided via dependency injection).
    :type db: AsyncSession

    :raises HTTPException: Raises a 404 error if the movie with the given ID is not found.
    :raises HTTPException: Raises a 400 error if the movie has been purchased by users.

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

    # Перевіряємо, чи купив хтось цей фільм
    purchased_stmt = select(PurchasedMovieModel).where(PurchasedMovieModel.movie_id == movie_id)
    purchased_result = await db.execute(purchased_stmt)
    if purchased_result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete movie that has been purchased by users."
        )

    # Перевіряємо, чи є фільм в кошиках користувачів
    cart_items_stmt = select(CartItemModel).where(CartItemModel.movie_id == movie_id)
    cart_items_result = await db.execute(cart_items_stmt)
    cart_items = cart_items_result.scalars().all()
    
    if cart_items:
        # Отримуємо список користувачів, у яких фільм в кошику
        user_ids = [item.cart.user_id for item in cart_items]
        user_ids_str = ", ".join(map(str, user_ids))
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete movie that is in users' carts. Users with movie in cart: {user_ids_str}"
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
    rows = result.all()
    counts = {row[0]: row[1] for row in rows}
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
    director: str = Query(None, description="Filter by director name"),
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
    if director:
        stmt = stmt.join(MovieModel.directors).where(DirectorModel.name.ilike(f"%{director}%"))
    if search:
        stmt = stmt.where(
            (MovieModel.name.ilike(f"%{search}%")) |
            (MovieModel.overview.ilike(f"%{search}%")) |
            (MovieModel.actors.any(ActorModel.name.ilike(f"%{search}%"))) |
            (MovieModel.directors.any(DirectorModel.name.ilike(f"%{search}%")))
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


@router.post(
    "/movies/{movie_id}/rate",
    response_model=MovieRatingResponseSchema,
    summary="Rate a movie (1-10)",
    description="Set or update your rating for a movie.",
    status_code=201
)
async def rate_movie(
    movie_id: int,
    data: MovieRatingCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    stmt = select(MovieRatingModel).where(
        MovieRatingModel.user_id == current_user.id,
        MovieRatingModel.movie_id == movie_id
    )
    result = await db.execute(stmt)
    rating_obj = result.scalars().first()
    if rating_obj:
        rating_obj.rating = data.rating
    else:
        rating_obj = MovieRatingModel(user_id=current_user.id, movie_id=movie_id, rating=data.rating)
        db.add(rating_obj)
    await db.commit()
    await db.refresh(rating_obj)
    return rating_obj

@router.get(
    "/movies/{movie_id}/rating",
    response_model=MovieRatingAverageSchema,
    summary="Get average rating for a movie",
    description="Get the average rating and number of ratings for a movie."
)
async def get_movie_average_rating(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func
    stmt = select(
        func.avg(MovieRatingModel.rating),
        func.count(MovieRatingModel.id)
    ).where(MovieRatingModel.movie_id == movie_id)
    result = await db.execute(stmt)
    avg, count = result.first()
    return MovieRatingAverageSchema(movie_id=movie_id, average_rating=avg or 0.0, ratings_count=count or 0)

@router.get(
    "/movies/{movie_id}/my-rating",
    response_model=MovieRatingResponseSchema,
    summary="Get your rating for a movie",
    description="Get the current user's rating for a movie, if exists."
)
async def get_my_movie_rating(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    stmt = select(MovieRatingModel).where(
        MovieRatingModel.user_id == current_user.id,
        MovieRatingModel.movie_id == movie_id
    )
    result = await db.execute(stmt)
    rating_obj = result.scalars().first()
    if not rating_obj:
        raise HTTPException(status_code=404, detail="You have not rated this movie yet.")
    return rating_obj

# --- CRUD для коментарів до фільмів ---
@router.post(
    "/movies/{movie_id}/comments",
    response_model=MovieCommentResponseSchema,
    summary="Create a comment on a movie",
    description="Add a comment to a movie. Can be a reply to another comment.",
    status_code=201
)
async def create_movie_comment(
    movie_id: int,
    data: MovieCommentCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    comment = MovieCommentModel(
        user_id=current_user.id,
        movie_id=movie_id,
        text=data.text,
        parent_id=data.parent_id
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment

@router.get(
    "/movies/{movie_id}/comments",
    response_model=list[MovieCommentResponseSchema],
    summary="Get comments for a movie",
    description="Get all comments for a movie with replies."
)
async def get_movie_comments(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MovieCommentModel).where(
        MovieCommentModel.movie_id == movie_id,
        MovieCommentModel.parent_id.is_(None)
    ).order_by(MovieCommentModel.created_at.desc())
    result = await db.execute(stmt)
    comments = result.scalars().all()
    return comments

@router.patch(
    "/comments/{comment_id}",
    response_model=MovieCommentResponseSchema,
    summary="Update a comment",
    description="Update your own comment."
)
async def update_movie_comment(
    comment_id: int,
    data: MovieCommentCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    comment = await db.get(MovieCommentModel, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found.")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments.")
    comment.text = data.text
    await db.commit()
    await db.refresh(comment)
    return comment

@router.delete(
    "/comments/{comment_id}",
    status_code=204,
    summary="Delete a comment",
    description="Delete your own comment."
)
async def delete_movie_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    comment = await db.get(MovieCommentModel, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found.")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments.")
    await db.delete(comment)
    await db.commit()

@router.post(
    "/comments/{comment_id}/like",
    status_code=204,
    summary="Like or dislike a comment",
    description="Like or dislike a comment. User can only have one like/dislike per comment."
)
async def like_or_dislike_comment(
    comment_id: int,
    data: MovieCommentLikeRequestSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    stmt = select(MovieCommentLikeModel).where(
        MovieCommentLikeModel.user_id == current_user.id,
        MovieCommentLikeModel.comment_id == comment_id
    )
    result = await db.execute(stmt)
    like_obj = result.scalars().first()
    if like_obj:
        like_obj.is_like = data.is_like
    else:
        like_obj = MovieCommentLikeModel(user_id=current_user.id, comment_id=comment_id, is_like=data.is_like)
        db.add(like_obj)
    await db.commit()

@router.get(
    "/comments/{comment_id}/likes",
    response_model=MovieCommentLikeCountSchema,
    summary="Get like/dislike counts for a comment",
    description="Get the number of likes and dislikes for a comment."
)
async def get_comment_like_counts(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MovieCommentLikeModel.is_like, func.count()).where(MovieCommentLikeModel.comment_id == comment_id).group_by(MovieCommentLikeModel.is_like)
    result = await db.execute(stmt)
    rows = result.all()
    counts = {row[0]: row[1] for row in rows}
    return MovieCommentLikeCountSchema(
        likes=counts.get(True, 0),
        dislikes=counts.get(False, 0)
    )

# --- Shopping Cart endpoints ---
@router.post(
    "/cart/add",
    response_model=CartSchema,
    summary="Add movie to cart",
    description="Add a movie to the user's shopping cart. Cannot add if already purchased or already in cart.",
    status_code=201
)
async def add_to_cart(
    data: CartItemCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Перевіряємо, чи купив користувач цей фільм
    purchased_stmt = select(PurchasedMovieModel).where(
        PurchasedMovieModel.user_id == current_user.id,
        PurchasedMovieModel.movie_id == data.movie_id
    )
    purchased_result = await db.execute(purchased_stmt)
    if purchased_result.scalars().first():
        raise HTTPException(status_code=400, detail="You have already purchased this movie.")
    
    # Отримуємо або створюємо кошик користувача
    cart_stmt = select(CartModel).where(CartModel.user_id == current_user.id)
    cart_result = await db.execute(cart_stmt)
    cart = cart_result.scalars().first()
    
    if not cart:
        cart = CartModel(user_id=current_user.id)
        db.add(cart)
        await db.flush()
    
    # Перевіряємо, чи фільм вже в кошику
    existing_item_stmt = select(CartItemModel).where(
        CartItemModel.cart_id == cart.id,
        CartItemModel.movie_id == data.movie_id
    )
    existing_result = await db.execute(existing_item_stmt)
    if existing_result.scalars().first():
        raise HTTPException(status_code=400, detail="Movie is already in your cart.")
    
    # Додаємо фільм до кошика
    cart_item = CartItemModel(cart_id=cart.id, movie_id=data.movie_id)
    db.add(cart_item)
    await db.commit()
    await db.refresh(cart)
    
    # Розраховуємо загальну ціну
    total_price = sum(item.movie.price for item in cart.items)
    return CartSchema(
        id=cart.id,
        user_id=cart.user_id,
        items=cart.items,
        total_price=total_price
    )

@router.delete(
    "/cart/remove/{movie_id}",
    status_code=204,
    summary="Remove movie from cart",
    description="Remove a movie from the user's shopping cart."
)
async def remove_from_cart(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    cart_stmt = select(CartModel).where(CartModel.user_id == current_user.id)
    cart_result = await db.execute(cart_stmt)
    cart = cart_result.scalars().first()
    
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found.")
    
    item_stmt = select(CartItemModel).where(
        CartItemModel.cart_id == cart.id,
        CartItemModel.movie_id == movie_id
    )
    item_result = await db.execute(item_stmt)
    item = item_result.scalars().first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Movie not found in cart.")
    
    await db.delete(item)
    await db.commit()

@router.get(
    "/cart/",
    response_model=CartSchema,
    summary="Get user's cart",
    description="Get the current user's shopping cart with all items and total price."
)
async def get_cart(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    cart_stmt = select(CartModel).where(CartModel.user_id == current_user.id)
    cart_result = await db.execute(cart_stmt)
    cart = cart_result.scalars().first()
    
    if not cart:
        # Створюємо порожній кошик
        cart = CartModel(user_id=current_user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    
    total_price = sum(item.movie.price for item in cart.items)
    return CartSchema(
        id=cart.id,
        user_id=cart.user_id,
        items=cart.items,
        total_price=total_price
    )

@router.post(
    "/cart/purchase",
    response_model=list[PurchasedMovieSchema],
    summary="Purchase all movies in cart",
    description="Purchase all movies in the user's cart. Movies are moved to purchased list and cart is cleared.",
    status_code=201
)
async def purchase_cart(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    cart_stmt = select(CartModel).where(CartModel.user_id == current_user.id)
    cart_result = await db.execute(cart_stmt)
    cart = cart_result.scalars().first()
    
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")
    
    purchased_movies = []
    
    for item in cart.items:
        # Перевіряємо, чи не купив користувач цей фільм
        purchased_stmt = select(PurchasedMovieModel).where(
            PurchasedMovieModel.user_id == current_user.id,
            PurchasedMovieModel.movie_id == item.movie_id
        )
        purchased_result = await db.execute(purchased_stmt)
        if purchased_result.scalars().first():
            continue  # Пропускаємо вже куплені фільми
        
        # Додаємо до куплених
        purchased_movie = PurchasedMovieModel(
            user_id=current_user.id,
            movie_id=item.movie_id,
            price_paid=item.movie.price
        )
        db.add(purchased_movie)
        purchased_movies.append(purchased_movie)
    
    # Очищаємо кошик
    await db.delete(cart)
    await db.commit()
    
    return purchased_movies

@router.delete(
    "/cart/clear",
    status_code=204,
    summary="Clear cart",
    description="Remove all items from the user's shopping cart."
)
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    cart_stmt = select(CartModel).where(CartModel.user_id == current_user.id)
    cart_result = await db.execute(cart_stmt)
    cart = cart_result.scalars().first()
    
    if cart:
        await db.delete(cart)
        await db.commit()

@router.get(
    "/purchased/",
    response_model=list[PurchasedMovieSchema],
    summary="Get user's purchased movies",
    description="Get all movies purchased by the current user."
)
async def get_purchased_movies(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    stmt = select(PurchasedMovieModel).where(
        PurchasedMovieModel.user_id == current_user.id
    ).order_by(PurchasedMovieModel.purchased_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
