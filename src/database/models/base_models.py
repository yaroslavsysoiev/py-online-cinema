import enum
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional

from sqlalchemy import (
    ForeignKey,
    String,
    Boolean,
    DateTime,
    Enum,
    Integer,
    func,
    Text,
    Date,
    UniqueConstraint,
    Float,
    DECIMAL,
    Table,
    Column
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    validates
)
from src.database.models.base import Base

from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid as uuid_lib
import datetime

class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"

class UserGroupModel(Base):
    __tablename__ = "user_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(Enum(UserGroupEnum), nullable=False, unique=True)
    users: Mapped[List["UserModel"]] = relationship("UserModel", back_populates="group")
    def __repr__(self):
        return f"<UserGroupModel(id={self.id}, name={self.name})>"

class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    _hashed_password: Mapped[str] = mapped_column("hashed_password", String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False)
    group: Mapped["UserGroupModel"] = relationship("UserGroupModel", back_populates="users")
    # relationships to tokens, profile, etc. залишаються у accounts.py
    def __repr__(self):
        return f"<UserModel(id={self.id}, email={self.email})>"

class NotificationModel(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    related_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    def __repr__(self):
        return f"<NotificationModel(id={self.id}, user_id={self.user_id})>"

class MovieStatusEnum(str, enum.Enum):
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
    def __repr__(self):
        return f"<Genre(name='{self.name}')>"

class ActorModel(Base):
    __tablename__ = "actors"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    def __repr__(self):
        return f"<Actor(name='{self.name}')>"

class CountryModel(Base):
    __tablename__ = "countries"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    def __repr__(self):
        return f"<Country(code='{self.code}', name='{self.name}')>"

class LanguageModel(Base):
    __tablename__ = "languages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    def __repr__(self):
        return f"<Language(name='{self.name}')>"

class MovieModel(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(UUID(as_uuid=False), default=lambda: str(uuid_lib.uuid4()), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), nullable=False)
    date: Mapped["datetime.date"] = mapped_column(Date, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MovieStatusEnum] = mapped_column(
        SQLAlchemyEnum(MovieStatusEnum), default=MovieStatusEnum.RELEASED, nullable=False
    )
    budget: Mapped[float] = mapped_column(DECIMAL(15, 2), nullable=False)
    revenue: Mapped[float] = mapped_column(Float, nullable=False)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="unique_movie_constraint"),
    )
    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]
    def __repr__(self):
        return f"<Movie(name='{self.name}', release_date='{self.date}', score={self.score})>"

class CertificationModel(Base):
    __tablename__ = "certifications"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    def __repr__(self):
        return f"<Certification(name='{self.name}')>"

class DirectorModel(Base):
    __tablename__ = "directors"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    def __repr__(self):
        return f"<Director(name='{self.name}')>"

class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"

class PaymentStatusEnum(str, enum.Enum):
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"

# --- Додаю моделі з movies.py для уникнення циклічних імпортів ---
import datetime
from sqlalchemy import Text, DECIMAL, UniqueConstraint, Date, ForeignKey, Boolean, Integer, DateTime, func, String
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import Enum as SQLAlchemyEnum
from typing import Optional, List

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
    parent = relationship("MovieCommentModel", back_populates="replies", remote_side=[id])
    replies = relationship("MovieCommentModel", back_populates="parent")
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

class UserProfileModel(Base):
    __tablename__ = "user_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional["GenderEnum"]] = mapped_column(SQLAlchemyEnum("GenderEnum"))
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(DateTime)
    info: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    user = relationship("UserModel", back_populates="profile")
    __table_args__ = (UniqueConstraint("user_id"),)
    def __repr__(self):
        return f"<UserProfileModel(id={self.id}, first_name={self.first_name}, last_name={self.last_name}, user_id={self.user_id})>"

class TokenBaseModel(Base):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc) + timedelta(days=1))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

class ActivationTokenModel(TokenBaseModel):
    __tablename__ = "activation_tokens"
    user = relationship("UserModel", back_populates="activation_token")
    __table_args__ = (UniqueConstraint("user_id"),)
    def __repr__(self):
        return f"<ActivationTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"

class PasswordResetTokenModel(TokenBaseModel):
    __tablename__ = "password_reset_tokens"
    user = relationship("UserModel", back_populates="password_reset_token")
    __table_args__ = (UniqueConstraint("user_id"),)
    def __repr__(self):
        return f"<PasswordResetTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"

class RefreshTokenModel(TokenBaseModel):
    __tablename__ = "refresh_tokens"
    user = relationship("UserModel", back_populates="refresh_tokens")
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    @classmethod
    def create(cls, user_id: int | Mapped[int], days_valid: int, token: str) -> "RefreshTokenModel":
        expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        return cls(user_id=user_id, token=token, expires_at=expires_at)
    def __repr__(self):
        return f"<RefreshTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>" 