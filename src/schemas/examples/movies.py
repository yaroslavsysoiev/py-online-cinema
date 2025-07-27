movie_item_schema_example = {
    "id": 9933,
    "name": "The Swan Princess: A Royal Wedding",
    "date": "2020-07-20",
    "score": 70,
    "overview": "Princess Odette and Prince Derek are going to a wedding at Princess Mei Li and her beloved Chen. "
                "But evil forces are at stake and the wedding plans are tarnished and "
                "true love has difficult conditions."
}

movie_list_response_schema_example = {
    "movies": [
        movie_item_schema_example
    ],
    "prev_page": "/theater/movies/?page=1&per_page=1",
    "next_page": "/theater/movies/?page=3&per_page=1",
    "total_pages": 9933,
    "total_items": 9933
}

movie_create_schema_example = {
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
    "languages": ["English", "French"]
}


language_schema_example = {
    "id": 1,
    "name": "English"
}

country_schema_example = {
    "id": 1,
    "code": "US",
    "name": "United States"
}

genre_schema_example = {
    "id": 1,
    "genre": "Comedy"
}

actor_schema_example = {
    "id": 1,
    "name": "JimmyFallon"
}

movie_detail_schema_example = {
    **movie_item_schema_example,
    "status": "Released",
    "budget": 1000000.00,
    "revenue": 5000000.00,
    "actors": [actor_schema_example],
    "country": country_schema_example,
    "genres": [genre_schema_example],
    "languages": [language_schema_example]
}

movie_update_schema_example = {
    "name": "Update Movie",
    "date": "2025-01-01",
    "score": 85.5,
    "overview": "An amazing movie.",
    "status": "Released",
    "budget": 1000000.00,
    "revenue": 5000000.00,
}
