import os

from src.database.models.base import Base
from src.database.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    NotificationModel,
    UserProfileModel,
)
from src.database.models.movies import (
    MovieModel,
    LanguageModel,
    ActorModel,
    GenreModel,
    CountryModel,
    MoviesGenresModel,
    ActorsMoviesModel,
    MoviesLanguagesModel,
    CartModel,
    CartItemModel,
    PurchasedMovieModel,
    OrderModel,
    OrderItemModel,
    OrderStatusEnum,
    PaymentModel,
    PaymentItemModel,
    PaymentStatusEnum,
)

from src.database.session_sqlite import reset_sqlite_database as reset_database
from src.database.validators import accounts as accounts_validators

environment = os.getenv("ENVIRONMENT", "developing")

if environment == "testing":
    from src.database.session_sqlite import (
        get_sqlite_db_contextmanager as get_db_contextmanager,
        get_sqlite_db as get_db,
    )
else:
    from src.database.session_postgresql import (
        get_postgresql_db_contextmanager as get_db_contextmanager,
        get_postgresql_db as get_db,
    )
