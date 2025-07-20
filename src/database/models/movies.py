import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import String, Float, Text, DECIMAL, UniqueConstraint, Date, ForeignKey, Table, Column, Boolean, Integer, DateTime, func
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid as uuid_lib

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

# --- Додаємо асоціативну таблицю для режисерів ---
DirectorsMoviesModel = Table(
    "directors_movies",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True, nullable=False),
)

# --- Додаємо асоціативну таблицю для акторів (stars) ---
StarsMoviesModel = Table(
    "stars_movies",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column(
        "star_id",
        ForeignKey("actors.id", ondelete="CASCADE"), primary_key=True, nullable=False),
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
    uuid: Mapped[str] = mapped_column(UUID(as_uuid=False), default=lambda: str(uuid_lib.uuid4()), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)  # duration in minutes
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), nullable=False)
    certification: Mapped["CertificationModel"] = relationship("CertificationModel", back_populates="movies")
    date: Mapped["datetime.date"] = mapped_column(Date, nullable=False)
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
    stars: Mapped[list["ActorModel"]] = relationship(
        "ActorModel",
        secondary=StarsMoviesModel,
        back_populates="movies"
    )
    directors: Mapped[list["DirectorModel"]] = relationship(
        "DirectorModel",
        secondary=DirectorsMoviesModel,
        back_populates="movies"
    )
    languages: Mapped[list["LanguageModel"]] = relationship(
        "LanguageModel",
        secondary=MoviesLanguagesModel,
        back_populates="movies"
    )
    likes: Mapped[List["MovieLikeModel"]] = relationship(
        "MovieLikeModel", back_populates="movie", cascade="all, delete-orphan"
    )
    comments: Mapped[List["MovieCommentModel"]] = relationship(
        "MovieCommentModel", back_populates="movie", cascade="all, delete-orphan"
    )
    favorited_by: Mapped[List["FavoriteMovieModel"]] = relationship(
        "FavoriteMovieModel", back_populates="movie", cascade="all, delete-orphan"
    )
    ratings: Mapped[List["MovieRatingModel"]] = relationship(
        "MovieRatingModel", back_populates="movie", cascade="all, delete-orphan"
    )
    cart_items: Mapped[List["CartItemModel"]] = relationship(
        "CartItemModel", back_populates="movie", cascade="all, delete-orphan"
    )
    purchased_by: Mapped[List["PurchasedMovieModel"]] = relationship(
        "PurchasedMovieModel", back_populates="movie", cascade="all, delete-orphan"
    )
    order_items: Mapped[List["OrderItemModel"]] = relationship(
        "OrderItemModel", back_populates="movie", cascade="all, delete-orphan"
    )
    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="unique_movie_constraint"),
    )

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]

    def __repr__(self):
        return f"<Movie(name='{self.name}', release_date='{self.date}', score={self.score})>"


class MovieLikeModel(Base):
    __tablename__ = "movie_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uix_user_movie_like"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)

    user = relationship("UserModel", back_populates="movie_likes")
    movie = relationship("MovieModel", back_populates="likes")


class MovieCommentModel(Base):
    __tablename__ = "movie_comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("movie_comments.id", ondelete="CASCADE"), nullable=True)

    user = relationship("UserModel", back_populates="movie_comments")
    movie = relationship("MovieModel", back_populates="comments")
    replies = relationship("MovieCommentModel", back_populates="parent", remote_side=[id], cascade="all, delete-orphan")
    parent = relationship("MovieCommentModel", back_populates="replies", remote_side=[id])
    likes: Mapped[List["MovieCommentLikeModel"]] = relationship(
        "MovieCommentLikeModel", back_populates="comment", cascade="all, delete-orphan"
    )

class MovieCommentLikeModel(Base):
    __tablename__ = "movie_comment_likes"
    __table_args__ = (
        UniqueConstraint("user_id", "comment_id", name="uix_user_comment_like"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment_id: Mapped[int] = mapped_column(ForeignKey("movie_comments.id", ondelete="CASCADE"), nullable=False)
    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)

    user = relationship("UserModel", back_populates="movie_comment_likes")
    comment = relationship("MovieCommentModel", back_populates="likes")


class FavoriteMovieModel(Base):
    __tablename__ = "favorite_movies"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uix_user_movie_favorite"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)

    user = relationship("UserModel", back_populates="favorite_movies")
    movie = relationship("MovieModel", back_populates="favorited_by")

# --- Додаємо CertificationModel ---
class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship("MovieModel", back_populates="certification")

    def __repr__(self):
        return f"<Certification(name='{self.name}')>"

# --- Додаємо DirectorModel ---
class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=DirectorsMoviesModel,
        back_populates="directors"
    )

    def __repr__(self):
        return f"<Director(name='{self.name}')>"


class MovieRatingModel(Base):
    __tablename__ = "movie_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uix_user_movie_rating"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10

    user = relationship("UserModel", back_populates="movie_ratings")
    movie = relationship("MovieModel", back_populates="ratings")


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True
    )

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="cart")
    items: Mapped[List["CartItemModel"]] = relationship(
        "CartItemModel", back_populates="cart", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<CartModel(id={self.id}, user_id={self.user_id})>"


class CartItemModel(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "movie_id", name="uix_cart_movie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    added_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cart: Mapped["CartModel"] = relationship("CartModel", back_populates="items")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="cart_items")

    def __repr__(self):
        return f"<CartItemModel(id={self.id}, cart_id={self.cart_id}, movie_id={self.movie_id})>"


class PurchasedMovieModel(Base):
    __tablename__ = "purchased_movies"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uix_user_purchased_movie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    purchased_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    price_paid: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="purchased_movies")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="purchased_by")

    def __repr__(self):
        return f"<PurchasedMovieModel(id={self.id}, user_id={self.user_id}, movie_id={self.movie_id})>"

class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"

class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[OrderStatusEnum] = mapped_column(SQLAlchemyEnum(OrderStatusEnum), default=OrderStatusEnum.PENDING, nullable=False)
    total_amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="orders")
    items: Mapped[List["OrderItemModel"]] = relationship("OrderItemModel", back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[List["PaymentModel"]] = relationship("PaymentModel", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OrderModel(id={self.id}, user_id={self.user_id}, status={self.status})>"

class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    price_at_order: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="items")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="order_items")
    payment_items: Mapped[List["PaymentItemModel"]] = relationship("PaymentItemModel", back_populates="order_item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OrderItemModel(id={self.id}, order_id={self.order_id}, movie_id={self.movie_id})>"

class PaymentStatusEnum(str, Enum):
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[PaymentStatusEnum] = mapped_column(SQLAlchemyEnum(PaymentStatusEnum), default=PaymentStatusEnum.SUCCESSFUL, nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    external_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="payments")
    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="payments")
    items: Mapped[List["PaymentItemModel"]] = relationship("PaymentItemModel", back_populates="payment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Payment(id={self.id}, user_id={self.user_id}, order_id={self.order_id}, status={self.status}, amount={self.amount})>"


class PaymentItemModel(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    price_at_payment: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    payment: Mapped["PaymentModel"] = relationship("PaymentModel", back_populates="items")
    order_item: Mapped["OrderItemModel"] = relationship("OrderItemModel", back_populates="payment_items")

    def __repr__(self):
        return f"<PaymentItem(id={self.id}, payment_id={self.payment_id}, order_item_id={self.order_item_id}, price_at_payment={self.price_at_payment})>"
