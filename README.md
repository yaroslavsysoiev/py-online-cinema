# py-online-cinema
Web platform which gives users opportunity to choose, watch and buy movies or videos in the Internet.

## Authorization & Authentication Features

### User Registration & Activation
- Users can register with their email and password.
- After registration, an activation email is sent with a unique link (valid for 24 hours).
- If the user does not activate their account in time, they can request a new activation link.
- Email uniqueness is enforced before registration.

### Login & JWT Token Management
- Users log in with email and password.
- On successful login, a pair of JWT tokens (access and refresh) is issued.
- Access token is used for authentication; refresh token can be used to obtain a new access token.
- Logout endpoint deletes the user's refresh token, making it unusable for further logins.

### Password Management
- Users can change their password by providing the old and new password.
- If a user forgets their password, they can request a password reset link via email (valid for 24 hours).
- Password complexity is enforced on registration and change.

### User Groups & Permissions
- There are three user groups: **User**, **Moderator**, **Admin**.
  - **User**: Basic access.
  - **Moderator**: Can manage movies and view sales (admin panel, not implemented in this repo).
  - **Admin**: Can manage users, change user groups, and manually activate accounts.
- Role-based access is enforced using FastAPI dependencies (`get_current_admin`, `get_current_moderator`).

### Admin Endpoints
- **POST /admin/users/{user_id}/activate**: Manually activate a user account (admin only).
- **POST /admin/users/{user_id}/change-group**: Change a user's group (admin only).

### Celery & Token Cleanup
- Celery-beat is used to periodically delete expired activation and password reset tokens.

### Database Models
- **UserModel**: Stores user info, hashed password, is_active, group, etc.
- **UserGroupModel**: Stores user groups (User, Moderator, Admin).
- **UserProfileModel**: Stores additional user info (optional fields).
- **ActivationTokenModel, PasswordResetTokenModel, RefreshTokenModel**: Store tokens with expiration.


## Docker & Docker Compose Setup

### Main Services
- **backend_theater**: FastAPI application (API, business logic)
- **postgres_theater**: PostgreSQL database
- **pgadmin_theater**: Web UI for PostgreSQL
- **mailhog_theater**: SMTP server for email testing (MailHog)
- **minio-theater**: S3-compatible object storage (MinIO)
- **minio_mc_theater**: MinIO client for bucket setup
- **alembic_migrator_theater**: Alembic migrations
- **redis_theater**: Redis for Celery task queue
- **celery_worker_theater**: Celery worker for background tasks

### How to Run All Services
1. **Build and start all containers:**
   ```bash
   docker-compose up --build
   ```
2. **View logs:**
   ```bash
   docker-compose logs -f
   ```
3. **Stop all containers:**
   ```bash
   docker-compose down
   ```

### Accessing Services
| Service         | URL/Port                  | Default Credentials         |
|----------------|---------------------------|----------------------------|
| FastAPI API    | http://localhost:8000     | -                          |
| OpenAPI Docs   | http://localhost:8000/docs| -                          |
| pgAdmin        | http://localhost:3333     | from .env                  |
| MailHog UI     | http://localhost:8025     | from .env (admin/admin)    |
| MinIO Console  | http://localhost:9001     | from .env (minioadmin/...) |
| Redis          | localhost:6379            | -                          |

### Environment Variables
- See `.env.example` for all required variables (Postgres, MinIO, MailHog, etc).
- Copy `.env.example` to `.env` and fill in your values.

### Useful Commands
- **Apply DB migrations:**
  ```bash
  docker-compose exec alembic_migrator_theater alembic upgrade head
  ```
- **Run tests:**
  ```bash
  pytest
  ```

### Notes
- All services are orchestrated via Docker Compose for easy local development.
- Celery worker and Redis are included for background task processing.
- MailHog and MinIO are included for email and file storage testing.


## Project Directory Structure

```
py-online-cinema
├── poetry.lock
├── pyproject.toml
├── README.md
└── src
    ├── celery_app.py
    ├── config
    │   ├── __init__.py
    │   ├── celeryconfig.py
    │   ├── config.py
    │   ├── dependencies.py
    │   └── settings.py
    ├── database
    │   ├── __init__.py
    │   ├── models
    │   │   ├── __init__.py
    │   │   ├── accounts.py
    │   │   └── base.py
    │   ├── session_postgresql.py
    │   ├── session_sqlite.py
    │   └── validators
    │       ├── __init__.py
    │       └── accounts.py
    ├── exceptions
    │   ├── __init__.py
    │   └── security.py
    ├── main.py
    ├── routes
    │   ├── __init__.py
    │   └── accounts.py
    ├── schemas
    │   ├── __init__.py
    │   ├── accounts.py
    │   └── examples
    │       ├── __init__.py
    │       └── movies.py
    ├── security
    │   ├── __init__.py
    │   ├── interfaces.py
    │   ├── passwords.py
    │   ├── token_manager.py
    │   └── utils.py
    ├── tasks
    │   ├── __init__.py
    │   └── cleanup.py
    ├── tests
    │   └── __init__.py
    └── utils
        ├── __init__.py
        └── email.py
```

