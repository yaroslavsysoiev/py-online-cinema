from datetime import date, datetime, timezone
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from database.models.movies import MovieStatusEnum
from schemas.examples.movies import (
    country_schema_example,
    language_schema_example,
    genre_schema_example,
    actor_schema_example,
    movie_item_schema_example,
    movie_list_response_schema_example,
    movie_create_schema_example,
    movie_detail_schema_example,
    movie_update_schema_example
)


class LanguageSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                language_schema_example
            ]
        }
    }


class CountrySchema(BaseModel):
    id: int
    code: str
    name: Optional[str]

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                country_schema_example
            ]
        }
    }


class GenreSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                genre_schema_example
            ]
        }
    }


class ActorSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                actor_schema_example
            ]
        }
    }


class MovieBaseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    date: date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)

    model_config = {
        "from_attributes": True
    }

    @field_validator("date")
    @classmethod
    def validate_date(cls, value):
        current_year = datetime.now(timezone.utc).year
        if value.year > current_year + 1:
            raise ValueError(f"The year in 'date' cannot be greater than {current_year + 1}.")
        return value


class MovieDetailSchema(BaseModel):
    id: int
    country: CountrySchema
    genres: List[GenreSchema]
    actors: List[ActorSchema]
    languages: List[LanguageSchema]
    date: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                movie_detail_schema_example
            ]
        }
    }


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                movie_item_schema_example
            ]
        }
    }


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                movie_list_response_schema_example
            ]
        }
    }


class MovieCreateSchema(BaseModel):
    name: str
    date: date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                movie_create_schema_example
            ]
        }
    }

    @field_validator("country", mode="before")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        return value.upper()

    @field_validator("genres", "actors", "languages", mode="before")
    @classmethod
    def normalize_list_fields(cls, value: List[str]) -> List[str]:
        return [item.title() for item in value]


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                movie_update_schema_example
            ]
        }
    }


class MovieLikeRequestSchema(BaseModel):
    is_like: bool


class MovieLikeCountSchema(BaseModel):
    likes: int
    dislikes: int


class MovieCommentCreateSchema(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    parent_id: Optional[int] = None


class MovieCommentResponseSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    text: str
    created_at: datetime
    parent_id: Optional[int] = None
    replies: List['MovieCommentResponseSchema'] = []
    likes: int = 0
    dislikes: int = 0

    class Config:
        from_attributes = True


MovieCommentResponseSchema.update_forward_refs()


class MovieCommentLikeRequestSchema(BaseModel):
    is_like: bool


class MovieCommentLikeCountSchema(BaseModel):
    likes: int
    dislikes: int
