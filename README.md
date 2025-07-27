# Movie Theater API Project

Welcome to the **Movie Theater API** project! This educational assignment is designed to help you develop and refine your skills in creating robust web applications using FastAPI, SQLAlchemy, and Docker. Here's what the project offers:

## Table of Contents

- [Movie Theater API Project](#movie-theater-api-project)
  - [Features](#features)
    - [Database setup](#database-setup)
    - [Data population](#data-population)
    - [Docker integration](#docker-integration)
    - [Project structure](#project-structure)
    - [Updated Project Structure Overview](#updated-project-structure-overview)
  - [Root Directory](#root-directory)
  - [Commands](#commands)
  - [Docker Configuration](#docker-configuration)
  - [Source Directory (src)](#source-directory-src)
  - [Additional Features](#additional-features)
  - [Tip: Using Dependency Injection in FastAPI](#tip-using-dependency-injection-in-fastapi)
  - [Using `get_db` for Database Dependency Injection](#using-get_db-for-database-dependency-injection)
  - [Extended Dependency Injection in FastAPI](#extended-dependency-injection-in-fastapi)
  - [Handling Authentication via Authorization Headers](#handling-authentication-via-authorization-headers)
  - [Summary](#summary)
  - [Primary Services (docker-compose.yml)](#primary-services-docker-composeyml)
    - [1. Database Service (`db`)](#1-database-service-db)
    - [2. pgAdmin Service (`pgadmin`)](#2-pgadmin-service-pgadmin)
    - [3. Backend Service (`web`)](#3-backend-service-web)
    - [4. Database Migrator (`migrator`)](#4-database-migrator-migrator)
    - [5. MailHog Service (`mailhog`)](#5-mailhog-service-mailhog)
    - [6. MinIO Object Storage (`minio`)](#6-minio-object-storage-minio)
    - [7. MinIO Client (`minio_mc`)](#7-minio-client-minio_mc)
  - [Testing Services (docker-compose-tests.yml)](#testing-services-docker-compose-testsyml)
    - [1. Test Backend Service (`web`)](#1-test-backend-service-web)
    - [2. Test MailHog Service (`mailhog`)](#2-test-mailhog-service-mailhog)
    - [3. Test MinIO Storage (`minio`)](#3-test-minio-storage-minio)
    - [4. Test MinIO Client (`minio_mc`)](#4-test-minio-client-minio_mc)
  - [Volumes](#volumes)
  - [Networks](#networks)
  - [Summary (again)](#summary-1)
  - [How to Run the Project](#how-to-run-the-project)
    - [1. Clone the Repository](#1-clone-the-repository)
    - [2. Create and Activate a Virtual Environment](#2-create-and-activate-a-virtual-environment)
    - [3. Install Dependencies with Poetry](#3-install-dependencies-with-poetry)
    - [4. Create a `.env` File](#4-create-a-env-file)
    - [5. Run the Project with Docker Compose](#5-run-the-project-with-docker-compose)
    - [6. Access the Services](#6-access-the-services)
    - [7. Verify Setup](#7-verify-setup)
    - [8. Running the Development Server without Docker](#8-running-the-development-server-without-docker)
    - [9. Running End-to-End (E2E) Tests](#9-running-end-to-end-e2e-tests)
    - [10. Running Tests Locally](#10-running-tests-locally)
      - [Project Setup Summary](#project-setup-summary)
    - [Run project with PyCharm](#run-project-with-pycharm)
  - [Models and Entities Overview](#models-and-entities-overview)
    - [Accounts Models](#accounts-models)
      - [1. UserGroupModel](#1-usergroupmodel)
      - [2. UserModel](#2-usermodel)
      - [3. UserProfileModel](#3-userprofilemodel)
      - [4. TokenBaseModel](#4-tokenbasemodel)
      - [5. ActivationTokenModel](#5-activationtokenmodel)
      - [6. PasswordResetTokenModel](#6-passwordresettokenmodel)
      - [7. RefreshTokenModel](#7-refreshtokenmodel)
    - [Movie Models](#movie-models)
      - [1. MovieModel](#1-moviemodel)
      - [2. GenreModel](#2-genremodel)
      - [3. ActorModel](#3-actormodel)
      - [4. CountryModel](#4-countrymodel)
      - [5. LanguageModel](#5-languagemodel)
      - [6. Association Tables](#6-association-tables)
  - [Task Description: Extending the Cinema Application](#task-description-extending-the-cinema-application)
  - [Tasks: Implementing Email Notifications for User Registration and Password Reset](#tasks-implementing-email-notifications-for-user-registration-and-password-reset)
  - [Task: Implement User Profile Creation and Validation Schema](#task-implement-user-profile-creation-and-validation-schema)
    - [1. Profile Schema (`schemas/profiles.py`)](#1-profile-schema-schemasprofilespy)
    - [2. Profile Creation Endpoint (`routes/profiles.py`)](#2-profile-creation-endpoint-routesprofilespy)
    - [3. Endpoint Behavior and Error Handling](#3-endpoint-behavior-and-error-handling)
      - [1️⃣ Token Validation](#1-token-validation)
      - [2️⃣ Authorization Rules](#2-authorization-rules)
      - [3️⃣ User Existence and Status](#3-user-existence-and-status)
      - [4️⃣ Check for Existing Profile](#4-check-for-existing-profile)
      - [5️⃣ Avatar Upload to S3 Storage](#5-avatar-upload-to-s3-storage)
      - [6️⃣ Profile Creation and Storage](#6-profile-creation-and-storage)
    - [4. Full List of Possible Errors](#4-full-list-of-possible-errors)
    - [5. Next Steps](#5-next-steps)
      - [Tips and Guidance](#tips-and-guidance)
      - [Running Tests](#running-tests)
        - [1️⃣ Running Unit and Integration Tests (Without Docker)](#1-running-unit-and-integration-tests-without-docker)
        - [2️⃣ Running End-to-End (E2E) Tests](#2-running-end-to-end-e2e-tests)
      - [Test Results](#test-results)

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
1. **Build and start all containers (development):**
   ```bash
   docker-compose -f docker-compose-dev.yml up --build
   ```
2. **View logs:**
   ```bash
   docker-compose -f docker-compose-dev.yml logs -f
   ```
3. **Stop all containers:**
   ```bash
   docker-compose -f docker-compose-dev.yml down
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
  docker-compose -f docker-compose-dev.yml exec alembic_migrator_theater alembic upgrade head
  ```
- **Run tests:**
  ```bash
  pytest
  ```

### Notes
- All services are orchestrated via Docker Compose for easy local development.
- **docker-compose-dev.yml**: Development environment with PostgreSQL, FastAPI, MailHog, and MinIO.
- **docker-compose-prod.yml**: Production environment configuration.
- **docker-compose-tests.yml**: Testing environment with SQLite database.
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

