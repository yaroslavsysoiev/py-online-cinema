import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from config import get_settings
from config.dependencies import get_s3_storage_client, get_accounts_email_notificator
from database import (
    reset_database,
    get_db_contextmanager,
    UserGroupEnum,
    UserGroupModel
)
from database.populate import CSVDatabaseSeeder
from main import app
from security.interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager
from storages import S3StorageClient
from tests.doubles.fakes.storage import FakeS3Storage
from tests.doubles.stubs.emails import StubEmailSender
from src.database.models.base import Base
from src.database.session_sqlite import sqlite_engine


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "order: Specify the order of test execution"
    )
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    # Глобально підміняємо email sender на StubEmailSender для всіх тестів
    from config.dependencies import get_accounts_email_notificator
    from tests.doubles.stubs.emails import StubEmailSender
    from main import app
    app.dependency_overrides[get_accounts_email_notificator] = lambda: StubEmailSender()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def reset_db(request, db_session):
    """
    Reset the SQLite database before each test function, except for tests marked with 'e2e'.

    By default, this fixture ensures that the database is cleared and recreated before every
    test function to maintain test isolation. However, if the test is marked with 'e2e',
    the database reset is skipped to allow preserving state between end-to-end tests.
    """
    if "e2e" in request.keywords:
        yield
    else:
        await reset_database()
        yield


@pytest_asyncio.fixture(scope="session")
async def reset_db_once_for_e2e(request):
    """
    Reset the database once for end-to-end tests.

    This fixture is intended to be used for end-to-end tests at the session scope,
    ensuring the database is reset before running E2E tests.
    """
    await reset_database()


@pytest_asyncio.fixture(scope="session")
async def settings():
    """
    Provide application settings.

    This fixture returns the application settings by calling get_settings().
    """
    return get_settings()


@pytest_asyncio.fixture(scope="function")
async def email_sender_stub():
    """
    Provide a stub implementation of the email sender.

    This fixture returns an instance of StubEmailSender for testing purposes.
    """
    return StubEmailSender()


@pytest_asyncio.fixture(scope="function")
async def s3_storage_fake():
    """
    Provide a fake S3 storage client.

    This fixture returns an instance of FakeS3Storage for testing purposes.
    """
    return FakeS3Storage()


@pytest_asyncio.fixture(scope="session")
async def s3_client(settings):
    """
    Provide an S3 storage client.

    This fixture returns an instance of S3StorageClient configured with the application settings.
    """
    return S3StorageClient(
        endpoint_url=settings.S3_STORAGE_ENDPOINT,
        access_key=settings.S3_STORAGE_ACCESS_KEY,
        secret_key=settings.S3_STORAGE_SECRET_KEY,
        bucket_name=settings.S3_BUCKET_NAME
    )


@pytest_asyncio.fixture(scope="function", autouse=True)
async def client(email_sender_stub, s3_storage_fake):
    """
    Provide an asynchronous HTTP client for testing.

    Overrides the dependencies for email sender and S3 storage with test doubles.
    """
    app.dependency_overrides[get_accounts_email_notificator] = lambda: email_sender_stub
    app.dependency_overrides[get_s3_storage_client] = lambda: s3_storage_fake

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session")
async def e2e_client():
    """
    Provide an asynchronous HTTP client for end-to-end tests.

    This client is available at the session scope.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client


@pytest_asyncio.fixture(scope="function")
async def db_session(create_all_tables):
    """
    Provide an async database session for database interactions.

    This fixture yields an async session using `get_db_contextmanager`, ensuring that the session
    is properly closed after each test.
    """
    async with get_db_contextmanager() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def e2e_db_session(create_all_tables):
    """
    Provide an async database session for end-to-end tests.

    This fixture yields an async session using `get_db_contextmanager` at the session scope,
    ensuring that the same session is used throughout the E2E test suite.
    Note: Using a session-scoped DB session in async tests may lead to shared state between tests,
    so use this fixture with caution if tests run concurrently.
    """
    async with get_db_contextmanager() as session:
        yield session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def e2e_client_with_tables(create_all_tables, e2e_client):
    yield e2e_client


@pytest_asyncio.fixture(scope="function")
async def jwt_manager() -> JWTAuthManagerInterface:
    """
    Asynchronous fixture to create a JWT authentication manager instance.

    This fixture retrieves the application settings via `get_settings()` and uses them to
    instantiate a `JWTAuthManager`. The manager is configured with the secret keys for
    access and refresh tokens, as well as the JWT signing algorithm specified in the settings.

    Returns:
        JWTAuthManagerInterface: An instance of JWTAuthManager configured with the appropriate
        secret keys and algorithm.
    """
    settings = get_settings()
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


@pytest_asyncio.fixture(scope="function")
async def seed_user_groups(db_session: AsyncSession):
    """
    Asynchronously seed the UserGroupModel table with default user groups.

    This fixture inserts all user groups defined in UserGroupEnum into the database and commits the transaction.
    It then yields the asynchronous database session for further testing.
    """
    existing_groups = (await db_session.execute(select(UserGroupModel.name))).scalars().all()
    groups = [
        {"name": "USER"},
        {"name": "MODERATOR"},
        {"name": "ADMIN"},
    ]
    groups_to_add = [g for g in groups if g["name"] not in existing_groups]
    if groups_to_add:
        try:
            await db_session.execute(insert(UserGroupModel).values(groups_to_add))
            await db_session.commit()
        except IntegrityError:
            await db_session.rollback()
    yield db_session


@pytest_asyncio.fixture(scope="function", autouse=True)
async def seed_database(db_session):
    """
    Seed the database with test data if it is empty.

    This fixture initializes a `CSVDatabaseSeeder` and ensures the test database is populated before
    running tests that require existing data.

    :param db_session: The async database session fixture.
    :type db_session: AsyncSession
    """
    settings = get_settings()
    seeder = CSVDatabaseSeeder(csv_file_path=settings.PATH_TO_MOVIES_CSV, db_session=db_session)

    if not await seeder.is_db_populated():
        await seeder.seed()

    yield db_session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_all_tables():
    """
    Створює всі таблиці у тестовій базі перед запуском тестів (один раз за сесію).
    """
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_all_tables_e2e():
    """
    Створює всі таблиці у тестовій БД для e2e-тестів (один раз за сесію).
    """
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_all_tables_for_e2e():
    """
    Створює всі таблиці у тестовій БД для e2e-тестів (один раз за сесію).
    """
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
