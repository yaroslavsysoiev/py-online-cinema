import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Float, Text, DECIMAL, UniqueConstraint, Date, ForeignKey, Table, Column
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import Enum as SQLAlchemyEnum

from database import Base


class MovieStatusEnum(str, Enum):
    RELEASED = "Released"
    POST_PRODUCTION = "Post Production"
    IN_PRODUCTION = "In Production"


MoviesGenresModel = Table(
    "movies_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, nullable=False),
)

ActorsMoviesModel = Table(
    "actors_movies",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column(
        "actor_id",
        ForeignKey("actors.id", ondelete="CASCADE"), primary_key=True, nullable=False),
)

MoviesLanguagesModel = Table(
    "movies_languages",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("language_id", ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True),
)


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MoviesGenresModel,
        back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre(name='{self.name}')>"


class ActorModel(Base):
    __tablename__ = "actors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=ActorsMoviesModel,
        back_populates="actors"
    )

    def __repr__(self):
        return f"<Actor(name='{self.name}')>"


class CountryModel(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    movies: Mapped[list["MovieModel"]] = relationship("MovieModel", back_populates="country")

    def __repr__(self):
        return f"<Country(code='{self.code}', name='{self.name}')>"


class LanguageModel(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MoviesLanguagesModel,
        back_populates="languages"
    )

    def __repr__(self):
        return f"<Language(name='{self.name}')>"


class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MovieStatusEnum] = mapped_column(
        SQLAlchemyEnum(MovieStatusEnum), nullable=False
    )
    budget: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=False)
    revenue: Mapped[float] = mapped_column(Float, nullable=False)

    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False)
    country: Mapped["CountryModel"] = relationship("CountryModel", back_populates="movies")

    genres: Mapped[list["GenreModel"]] = relationship(
        "GenreModel",
        secondary=MoviesGenresModel,
        back_populates="movies"
    )

    actors: Mapped[list["ActorModel"]] = relationship(
        "ActorModel",
        secondary=ActorsMoviesModel,
        back_populates="movies"
    )

    languages: Mapped[list["LanguageModel"]] = relationship(
        "LanguageModel",
        secondary=MoviesLanguagesModel,
        back_populates="movies"
    )

    __table_args__ = (
        UniqueConstraint("name", "date", name="unique_movie_constraint"),
    )

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]

    def __repr__(self):
        return f"<Movie(name='{self.name}', release_date='{self.date}', score={self.score})>"
