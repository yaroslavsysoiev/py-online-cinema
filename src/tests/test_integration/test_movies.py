import random

import pytest
from sqlalchemy import select, func, delete
from sqlalchemy.orm import joinedload

from database import MovieModel
from database import (
    GenreModel,
    ActorModel,
    LanguageModel,
    CountryModel
)


@pytest.mark.asyncio
async def test_get_movies_empty_database(client, db_session):
    await db_session.execute(delete(MovieModel))
    await db_session.commit()
    """
    Test that the `/movies/` endpoint returns a 404 error when the database is empty.
    """
    response = await client.get("/api/v1/theater/movies/")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    expected_detail = {"detail": "No movies found."}
    assert response.json() == expected_detail, f"Expected {expected_detail}, got {response.json()}"


@pytest.mark.asyncio
async def test_get_movies_default_parameters(client, seed_database):
    """
    Test the `/movies/` endpoint with default pagination parameters.
    """
    response = await client.get("/api/v1/theater/movies/")
    assert response.status_code == 200, "Expected status code 200, but got a different value"

    response_data = response.json()

    assert len(response_data["movies"]) == 10, "Expected 10 movies in the response, but got a different count"

    assert response_data["total_pages"] > 0, "Expected total_pages > 0, but got a non-positive value"
    assert response_data["total_items"] > 0, "Expected total_items > 0, but got a non-positive value"

    assert response_data["prev_page"] is None, "Expected prev_page to be None on the first page, but got a value"

    if response_data["total_pages"] > 1:
        assert response_data["next_page"] is not None, (
            "Expected next_page to be present when total_pages > 1, but got None"
        )


@pytest.mark.asyncio
async def test_get_movies_with_custom_parameters(client, seed_database):
    """
    Test the `/movies/` endpoint with custom pagination parameters.
    """
    page = 2
    per_page = 5

    response = await client.get(f"/api/v1/theater/movies/?page={page}&per_page={per_page}")

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert len(response_data["movies"]) == per_page, (
        f"Expected {per_page} movies in the response, but got {len(response_data['movies'])}"
    )

    assert response_data["total_pages"] > 0, "Expected total_pages > 0, but got a non-positive value"
    assert response_data["total_items"] > 0, "Expected total_items > 0, but got a non-positive value"

    if page > 1:
        assert response_data["prev_page"] == f"/theater/movies/?page={page - 1}&per_page={per_page}", (
            f"Expected prev_page to be '/theater/movies/?page={page - 1}&per_page={per_page}', "
            f"but got {response_data['prev_page']}"
        )

    if page < response_data["total_pages"]:
        assert response_data["next_page"] == f"/theater/movies/?page={page + 1}&per_page={per_page}", (
            f"Expected next_page to be '/theater/movies/?page={page + 1}&per_page={per_page}', "
            f"but got {response_data['next_page']}"
        )
    else:
        assert response_data["next_page"] is None, "Expected next_page to be None on the last page, but got a value"


@pytest.mark.asyncio
@pytest.mark.parametrize("page, per_page, expected_detail", [
    (0, 10, "Input should be greater than or equal to 1"),
    (1, 0, "Input should be greater than or equal to 1"),
    (0, 0, "Input should be greater than or equal to 1"),
])
async def test_invalid_page_and_per_page(client, page, per_page, expected_detail):
    """
    Test the `/movies/` endpoint with invalid `page` and `per_page` parameters.
    """
    response = await client.get(f"/api/v1/theater/movies/?page={page}&per_page={per_page}")

    assert response.status_code == 422, (
        f"Expected status code 422 for invalid parameters, but got {response.status_code}"
    )

    response_data = response.json()

    assert "detail" in response_data, "Expected 'detail' in the response, but it was missing"

    assert any(expected_detail in error["msg"] for error in response_data["detail"]), (
        f"Expected error message '{expected_detail}' in the response details, but got {response_data['detail']}"
    )


@pytest.mark.asyncio
async def test_per_page_maximum_allowed_value(client, seed_database):
    """
    Test the `/movies/` endpoint with the maximum allowed `per_page` value.
    """
    response = await client.get("/api/v1/theater/movies/?page=1&per_page=20")

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert "movies" in response_data, "Response missing 'movies' field."
    assert len(response_data["movies"]) <= 20, (
        f"Expected at most 20 movies, but got {len(response_data['movies'])}"
    )


@pytest.mark.asyncio
async def test_page_exceeds_maximum(client, db_session, seed_database):
    """
    Test the `/movies/` endpoint with a page number that exceeds the maximum.
    """
    per_page = 10

    count_stmt = select(func.count(MovieModel.id))
    result = await db_session.execute(count_stmt)
    total_movies = result.scalar_one()

    max_page = (total_movies + per_page - 1) // per_page

    response = await client.get(f"/api/v1/theater/movies/?page={max_page + 1}&per_page={per_page}")

    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"
    response_data = response.json()

    assert "detail" in response_data, "Response missing 'detail' field."


@pytest.mark.asyncio
async def test_movies_sorted_by_id_desc(client, db_session, seed_database):
    """
    Test that movies are returned sorted by `id` in descending order
    and match the expected data from the database.
    """
    response = await client.get("/api/v1/theater/movies/?page=1&per_page=10")

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    stmt = select(MovieModel).order_by(MovieModel.id.desc()).limit(10)
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert returned_movie_ids == expected_movie_ids, (
        f"Movies are not sorted by `id` in descending order. "
        f"Expected: {expected_movie_ids}, but got: {returned_movie_ids}"
    )


@pytest.mark.asyncio
async def test_movie_list_with_pagination(client, db_session, seed_database):
    """
    Test the `/movies/` endpoint with pagination parameters.

    Verifies the following:
    - The response status code is 200.
    - Total items and total pages match the expected values from the database.
    - The movies returned match the expected movies for the given page and per_page.
    - The `prev_page` and `next_page` links are correct.
    """
    page = 2
    per_page = 5
    offset = (page - 1) * per_page

    response = await client.get(f"/api/v1/theater/movies/?page={page}&per_page={per_page}")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    # Підрахунок total_items як у endpoint (тільки Released)
    count_stmt = select(func.count(MovieModel.id)).where(MovieModel.status == "Released")
    count_result = await db_session.execute(count_stmt)
    total_items = count_result.scalar_one()
    assert response_data["total_items"] == total_items, f"Total items mismatch. API: {response_data['total_items']}, DB: {total_items}"

    total_pages = (total_items + per_page - 1) // per_page

    assert response_data["total_items"] == total_items, "Total items mismatch."
    assert response_data["total_pages"] == total_pages, "Total pages mismatch."

    stmt = (
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db_session.execute(stmt)
    expected_movies = result.scalars().all()

    expected_movie_ids = [movie.id for movie in expected_movies]
    returned_movie_ids = [movie["id"] for movie in response_data["movies"]]

    assert expected_movie_ids == returned_movie_ids, "Movies on the page mismatch."

    expected_prev_page = f"/theater/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None
    expected_next_page = f"/theater/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None

    assert response_data["prev_page"] == expected_prev_page, "Previous page link mismatch."
    assert response_data["next_page"] == expected_next_page, "Next page link mismatch."


@pytest.mark.asyncio
async def test_movies_fields_match_schema(client, db_session, seed_database):
    """
    Test that each movie in the response matches the fields defined in `MovieListItemSchema`.
    """
    response = await client.get("/api/v1/theater/movies/?page=1&per_page=10")

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert "movies" in response_data, "Response missing 'movies' field."

    expected_fields = {"id", "name", "date", "score", "overview"}

    for movie in response_data["movies"]:
        assert set(movie.keys()) == expected_fields, (
            f"Movie fields do not match schema. "
            f"Expected: {expected_fields}, but got: {set(movie.keys())}"
        )


@pytest.mark.asyncio
async def test_get_movie_by_id_not_found(client, db_session, seed_database):
    """
    Test that the `/movies/{movie_id}` endpoint returns a 404 error
    when a movie with the given ID does not exist.
    """
    # Вибираємо movie_id, якого точно немає
    stmt_max = select(MovieModel.id).order_by(MovieModel.id.desc()).limit(1)
    result_max = await db_session.execute(stmt_max)
    max_id = result_max.scalars().first() or 0
    movie_id = max_id + 1000
    response = await client.get(f"/api/v1/theater/movies/{movie_id}/")
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    response_data = response.json()
    assert response_data == {"detail": "Movie with the given ID was not found."}, (
        f"Expected error message not found. Got: {response_data}"
    )


@pytest.mark.asyncio
async def test_get_movie_by_id_valid(client, db_session, seed_database):
    """
    Test that the `/movies/{movie_id}` endpoint returns the correct movie details
    when a valid movie ID is provided.

    Verifies the following:
    - The movie exists in the database.
    - The response status code is 200.
    - The movie's `id` and `name` in the response match the expected values from the database.
    """
    stmt_min = select(MovieModel.id).order_by(MovieModel.id.asc()).limit(1)
    result_min = await db_session.execute(stmt_min)
    min_id = result_min.scalars().first()

    stmt_max = select(MovieModel.id).order_by(MovieModel.id.desc()).limit(1)
    result_max = await db_session.execute(stmt_max)
    max_id = result_max.scalars().first()

    random_id = random.randint(min_id, max_id)

    stmt_movie = select(MovieModel).where(MovieModel.id == random_id)
    result_movie = await db_session.execute(stmt_movie)
    expected_movie = result_movie.scalars().first()
    assert expected_movie is not None, "Movie not found in database."

    response = await client.get(f"/api/v1/theater/movies/{random_id}/")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert response_data["id"] == expected_movie.id, "Returned ID does not match the requested ID."
    assert response_data["name"] == expected_movie.name, "Returned name does not match the expected name."


@pytest.mark.asyncio
async def test_get_movie_by_id_fields_match_database(client, db_session, seed_database):
    """
    Test that the `/movies/{movie_id}` endpoint returns all fields matching the database data.
    """
    stmt = (
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
        .limit(1)
    )
    result = await db_session.execute(stmt)
    random_movie = result.scalars().first()
    assert random_movie is not None, "No movies found in the database."

    response = await client.get(f"/api/v1/theater/movies/{random_movie.id}/")
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()

    assert response_data["id"] == random_movie.id, "ID does not match."
    assert response_data["name"] == random_movie.name, "Name does not match."
    assert response_data["date"] == random_movie.date.isoformat(), "Date does not match."
    assert response_data["score"] == random_movie.score, "Score does not match."
    assert response_data["overview"] == random_movie.overview, "Overview does not match."
    assert response_data["status"] == random_movie.status.value, "Status does not match."
    assert response_data["budget"] == float(random_movie.budget), "Budget does not match."
    assert response_data["revenue"] == random_movie.revenue, "Revenue does not match."

    assert response_data["country"]["id"] == random_movie.country.id, "Country ID does not match."
    assert response_data["country"]["code"] == random_movie.country.code, "Country code does not match."
    assert response_data["country"]["name"] == random_movie.country.name, "Country name does not match."

    actual_genres = sorted(response_data["genres"], key=lambda x: x["id"])
    expected_genres = sorted(
        [{"id": genre.id, "name": genre.name} for genre in random_movie.genres],
        key=lambda x: x["id"]
    )
    assert actual_genres == expected_genres, "Genres do not match."

    actual_actors = sorted(response_data["actors"], key=lambda x: x["id"])
    expected_actors = sorted(
        [{"id": actor.id, "name": actor.name} for actor in random_movie.actors],
        key=lambda x: x["id"]
    )
    assert actual_actors == expected_actors, "Actors do not match."

    actual_languages = sorted(response_data["languages"], key=lambda x: x["id"])
    expected_languages = sorted(
        [{"id": lang.id, "name": lang.name} for lang in random_movie.languages],
        key=lambda x: x["id"]
    )
    assert actual_languages == expected_languages, "Languages do not match."


@pytest.mark.asyncio
async def test_create_movie_and_related_models(client, db_session, seed_database):
    """
    Test that a new movie is created successfully and related models
    (genres, actors, languages) are created if they do not exist.
    """
    movie_data = {
        "name": "New Movie",
        "date": "2025-01-01",
        "score": 85.5,
        "overview": "An amazing movie.",
        "status": "Released",
        "budget": 1000000.00,
        "revenue": 5000000.00,
        "country": "US",
        "genres": ["Action", "Adventure"],
        "actors": ["John Doe", "Jane Doe"],
        "languages": ["English", "French"],
        "year": 2025,
        "time": 120,
        "imdb": 8.5,
        "votes": 1000,
        "description": "A new movie for testing.",
        "price": 9.99,
        "certification_id": 1
    }

    response = await client.post("/api/v1/theater/movies/", json=movie_data)
    if response.status_code != 201:
        print("Response JSON:", response.json())
    assert response.status_code == 201, f"Expected status code 201, but got {response.status_code}"

    response_data = response.json()
    assert response_data["name"] == movie_data["name"], "Movie name does not match."
    assert response_data["date"] == movie_data["date"], "Movie date does not match."
    assert response_data["score"] == movie_data["score"], "Movie score does not match."
    assert response_data["overview"] == movie_data["overview"], "Movie overview does not match."

    for genre_name in movie_data["genres"]:
        stmt = select(GenreModel).where(GenreModel.name == genre_name)
        result = await db_session.execute(stmt)
        genre = result.scalars().first()
        assert genre is not None, f"Genre '{genre_name}' was not created."

    for actor_name in movie_data["actors"]:
        stmt = select(ActorModel).where(ActorModel.name == actor_name)
        result = await db_session.execute(stmt)
        actor = result.scalars().first()
        assert actor is not None, f"Actor '{actor_name}' was not created."

    for language_name in movie_data["languages"]:
        stmt = select(LanguageModel).where(LanguageModel.name == language_name)
        result = await db_session.execute(stmt)
        language = result.scalars().first()
        assert language is not None, f"Language '{language_name}' was not created."

    stmt = select(CountryModel).where(CountryModel.code == movie_data["country"])
    result = await db_session.execute(stmt)
    country = result.scalars().first()
    assert country is not None, f"Country '{movie_data['country']}' was not created."


@pytest.mark.asyncio
async def test_create_movie_duplicate_error(client, db_session, seed_database):
    """
    Test that trying to create a movie with the same name and date as an existing movie
    results in a 409 conflict error.
    """
    stmt = select(MovieModel).limit(1)
    result = await db_session.execute(stmt)
    existing_movie = result.scalars().first()
    assert existing_movie is not None, "No existing movies found in the database."

    movie_data = {
        "name": existing_movie.name,
        "date": existing_movie.date.isoformat(),
        "score": 90.0,
        "overview": "Duplicate movie test.",
        "status": "Released",
        "budget": 2000000.00,
        "revenue": 8000000.00,
        "country": "US",
        "genres": ["Drama"],
        "actors": ["New Actor"],
        "languages": ["Spanish"]
    }

    response = await client.post("/api/v1/theater/movies/", json=movie_data)
    assert response.status_code == 409, f"Expected status code 409, but got {response.status_code}"

    response_data = response.json()
    expected_detail = (
        f"A movie with the name '{movie_data['name']}' and release date '{movie_data['date']}' already exists."
    )
    assert response_data["detail"] == expected_detail, (
        f"Expected detail message: {expected_detail}, but got: {response_data['detail']}"
    )


@pytest.mark.asyncio
async def test_delete_movie_success(client, db_session, seed_database):
    """
    Test the `/movies/{movie_id}/` endpoint for successful movie deletion.
    """
    stmt = select(MovieModel).limit(1)
    result = await db_session.execute(stmt)
    movie = result.scalars().first()
    assert movie is not None, "No movies found in the database to delete."

    movie_id = movie.id

    response = await client.delete(f"/api/v1/theater/movies/{movie_id}/")
    assert response.status_code == 204, f"Expected status code 204, but got {response.status_code}"

    stmt_check = select(MovieModel).where(MovieModel.id == movie_id)
    result_check = await db_session.execute(stmt_check)
    deleted_movie = result_check.scalars().first()
    assert deleted_movie is None, f"Movie with ID {movie_id} was not deleted."


@pytest.mark.asyncio
async def test_delete_movie_not_found(client):
    """
    Test the `/movies/{movie_id}/` endpoint with a non-existent movie ID.
    """
    non_existent_id = 99999

    response = await client.delete(f"/api/v1/theater/movies/{non_existent_id}/")
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    response_data = response.json()
    expected_detail = "Movie with the given ID was not found."
    assert response_data["detail"] == expected_detail, (
        f"Expected detail message: {expected_detail}, but got: {response_data['detail']}"
    )


@pytest.mark.asyncio
async def test_update_movie_success(client, db_session, seed_database):
    """
    Test the `/movies/{movie_id}/` endpoint for successfully updating a movie's details.
    """
    stmt = select(MovieModel).limit(1)
    result = await db_session.execute(stmt)
    movie = result.scalars().first()
    assert movie is not None, "No movies found in the database to update."

    movie_id = movie.id
    update_data = {
        "name": "Updated Movie Name",
        "score": 95.0,
    }

    response = await client.patch(f"/api/v1/theater/movies/{movie_id}/", json=update_data)
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"

    response_data = response.json()
    assert response_data["detail"] == "Movie updated successfully.", (
        f"Expected detail message: 'Movie updated successfully.', but got: {response_data['detail']}"
    )

    await db_session.rollback()

    stmt_check = select(MovieModel).where(MovieModel.id == movie_id)
    result_check = await db_session.execute(stmt_check)
    updated_movie = result_check.scalars().first()

    assert updated_movie.name == update_data["name"], "Movie name was not updated."
    assert updated_movie.score == update_data["score"], "Movie score was not updated."


@pytest.mark.asyncio
async def test_update_movie_not_found(client):
    """
    Test the `/movies/{movie_id}/` endpoint with a non-existent movie ID.
    """
    non_existent_id = 99999
    update_data = {
        "name": "Non-existent Movie",
        "score": 90.0
    }

    response = await client.patch(f"/api/v1/theater/movies/{non_existent_id}/", json=update_data)
    assert response.status_code == 404, f"Expected status code 404, but got {response.status_code}"

    response_data = response.json()
    expected_detail = "Movie with the given ID was not found."
    assert response_data["detail"] == expected_detail, (
        f"Expected detail message: {expected_detail}, but got: {response_data['detail']}"
    )
