# PROJECT SPEC - Game Theory

**App slug:** `game-theory`
**Generated:** 2026-03-28 10:06
**Framework modules:** django, postgresql, redis, celery, social_auth, jwt, rest_api, graphql, file_encryption, docker, cicd, monitoring, testing, linting

---

## How to use this file

Open this file and `.cursorrules` together in Cursor at the start of every session.
Paste the contents of `.cursorrules` into the Cursor system prompt or
include this file via `@PROJECT_SPEC.md` in your first message to Claude.

---
# GSD Framework — Django Module

## Purpose
Core Django 5.x web framework with Materialize CSS templates, environment-based settings, and GSD entity conventions. This module is always included.

---

## 1. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Django | 5.x (latest stable) |
| Language | Python | 3.12+ |
| Templates | Django Templates + Materialize CSS | |
| Static files | WhiteNoise (local) / S3 + CloudFront (AWS) |
| Env management | django-environ | |
| Package management | pip + requirements.txt (base, dev, prod splits) |

---

## 2. Packages

```
django>=5.0
django-environ>=0.11
whitenoise>=6.6
pillow>=10.0
python-dateutil>=2.9
```

---

## 3. Project Layout

```
game-theory/
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── dev.py / uat.py / prod.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/        # BaseModel, shared utilities
│   ├── lookup/      # LookupValue reference data
│   ├── users/       # User model + social auth
│   └── api/         # API views and serializers
├── templates/
├── static/
├── requirements/
├── manage.py
└── pyproject.toml
```

---

## 4. Entity Conventions — MANDATORY

### 4.1 Primary Keys — All entities use UUID

Every Django model MUST use UUID as the primary key. No integer or auto-increment PKs.

```python
import uuid
from django.db import models

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
```

### 4.2 Lookup / Reference Values — Single Unified Table

All lookup/reference fields are managed through a single `LookupValue` entity with parent-child hierarchy. Never create a new table for a reference list.

```python
class LookupValue(BaseModel):
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    code = models.CharField(max_length=100, db_index=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [('parent', 'code')]
        ordering = ['sort_order', 'label']
```

### 4.3 Soft Delete

All entities use soft delete via `is_active = False`. Never use hard deletes in application code.

### 4.4 API Envelope Pattern

All API responses follow the envelope:
```json
{"success": true, "data": {...}, "meta": {"page": 1, "total": 42}, "errors": []}
```

---

## 5. Settings Structure

Settings split across `base.py` (shared), `local.py` (dev overrides), `dev.py`, `uat.py`, `prod.py`.

`base.py` reads `.env` via `django-environ` with `overwrite=False` so Docker env_file values take precedence.

---

## 6. Cursor Prompting

When starting a session in Cursor, `.cursorrules` is auto-loaded. Attach `@PROJECT_SPEC.md` for full spec context.


---

# GSD Framework — PostgreSQL Module

## Purpose
PostgreSQL 16 as the primary relational database with UUID primary keys and django-environ for connection management.

**Conflicts with:** mysql

---

## 1. Packages

```
psycopg2-binary>=2.9
```

---

## 2. Docker Service

```yaml
db:
  image: postgres:16-alpine
  volumes:
    - postgres_data:/var/lib/postgresql/data
  environment:
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
  ports:
    - "5432:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 5s
    retries: 5
```

---

## 3. Settings

```python
DATABASES = {
    'default': env.db('DATABASE_URL')
}
```

---

## 4. Environment Variables

```env
DATABASE_URL=postgres://postgres:postgres@localhost:5432/game-theory
POSTGRES_DB=game-theory
```

---

## 5. Conventions

- Database name uses underscores (e.g. `gsd_flow`), not hyphens
- All primary keys are UUID — no integer or auto-increment PKs
- All foreign keys reference UUIDs
- Never use raw SQL — use ORM or repository pattern


---

# GSD Framework — Redis Module

## Purpose
Redis 7 for Django caching, session storage, and Celery result backend.

---

## 1. Packages

```
redis>=5.0
```

---

## 2. Docker Service

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

---

## 3. Settings

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/0'),
    }
}
```

---

## 4. Environment Variables

```env
REDIS_URL=redis://localhost:6379/0
```


---

# GSD Framework — Celery Module

## Purpose
Celery 5 async task workers with beat scheduler for background job processing. Uses Redis as default broker (overridden to RabbitMQ if the rabbitmq module is selected).

**Requires:** redis

---

## 1. Packages

```
celery>=5.3
django-celery-results>=2.5
```

---

## 2. Docker Service

```yaml
worker:
  build: .
  entrypoint: []
  command: celery -A config worker -l info
  volumes:
    - .:/app
  env_file: .env.docker
  depends_on:
    web:
      condition: service_started
    redis:
      condition: service_started
```

---

## 3. Settings (default — Redis broker)

```python
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
```

> If the `rabbitmq` module is selected, the broker URL switches to RabbitMQ with additional queue routing configuration.

---

## 4. Celery App Configuration

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
app = Celery('game-theory')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

---

## 5. Task Conventions

- All tasks in `apps/{module}/tasks.py`
- Use `@shared_task(bind=True)` with explicit `name=` and `queue=`
- Every task MUST be idempotent — safe to run multiple times with same arguments
- Use `update_or_create` and guard conditions, not blind inserts


---

# GSD Framework — Social Auth Module

## Purpose
Google and Microsoft OAuth2 social login/registration. No user passwords are stored. Authentication is exclusively via social OAuth providers.

---

## 1. Packages

```
social-auth-app-django>=5.4
social-auth-core>=4.5
```

---

## 2. Django Apps

Added to `INSTALLED_APPS`:
- `social_django`

---

## 3. URL Patterns

```python
path('auth/', include('social_django.urls', namespace='social')),
```

---

## 4. User Model

The User model never stores a password. `set_unusable_password()` is always called on creation.

```python
class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    avatar_url = models.URLField(blank=True)
    is_staff = models.BooleanField(default=False)
    last_login_provider = models.CharField(max_length=50, blank=True)
    USERNAME_FIELD = 'email'
```

---

## 5. Settings

```python
AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.microsoft.MicrosoftOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_USER_MODEL = 'users.User'
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/'
```

---

## 6. Pipeline

Key pipeline steps:
- `social_core.pipeline.social_auth.associate_by_email` — links social login to existing user by email (e.g. seeded superusers)
- `apps.users.pipeline.save_social_account` — persists SocialAccount record
- `apps.users.pipeline.issue_jwt` — returns JWT token pair

---

## 7. OAuth Callback URLs

| Provider | Redirect URI |
|----------|-------------|
| Google | `https://{domain}/auth/complete/google-oauth2/` |
| Microsoft | `https://{domain}/auth/complete/microsoft-graph/` |

---

## 8. Login Flow

```
User clicks "Sign in with Google"
  → GET /auth/login/google-oauth2/
  → Redirect to Google consent screen
  → Pipeline: find/create User, save SocialAccount, issue JWT
  → Redirect to / with JWT
```

---

## 9. Security

- Access/refresh tokens encrypted at rest via django-encrypted-model-fields
- JWT transmitted via `Authorization: Bearer` header only
- All OAuth redirect URIs pinned to exact domain — no wildcards


---

# GSD Framework — JWT Module

## Purpose
djangorestframework-simplejwt for stateless API token authentication with refresh token rotation.

---

## 1. Packages

```
djangorestframework-simplejwt>=5.3
```

---

## 2. Settings

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

---

## 3. URL Patterns

```python
path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
```

---

## 4. Usage

JWT tokens are issued by the social auth pipeline (`apps.users.pipeline.issue_jwt`). API clients include the token in the `Authorization: Bearer {token}` header. Refresh tokens should be stored in httpOnly cookies for web clients.


---

# GSD Framework — REST API Module

## Purpose
Django REST Framework with envelope responses, filtering, pagination, and OpenAPI schema generation via drf-spectacular.

---

## 1. Packages

```
djangorestframework>=3.15
django-cors-headers>=4.3
django-filter>=23.5
drf-spectacular>=0.27
```

---

## 2. Django Apps

Added to `INSTALLED_APPS`:
- `rest_framework`
- `corsheaders`
- `django_filters`
- `drf_spectacular`

---

## 3. Middleware

Added to `MIDDLEWARE`:
- `corsheaders.middleware.CorsMiddleware`

---

## 4. Settings

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

---

## 5. Health Check Endpoint

```python
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    checks = {'status': 'ok', 'db': 'ok'}
    try:
        connection.ensure_connection()
    except Exception:
        checks['db'] = 'error'
        checks['status'] = 'degraded'
    return Response(checks, status=200 if checks['status'] == 'ok' else 503)
```


---

# GSD Framework — GraphQL Module

## Purpose
Strawberry GraphQL with schema-first design, Django integration, and GraphQL Playground.

---

## 1. Packages

```
strawberry-graphql[django]>=0.235
```

---

## 2. Generated Files

`apps/api/schema.py` — Strawberry schema scaffold:

```python
import strawberry
from strawberry.django.views import GraphQLView

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello from the GraphQL API!"

schema = strawberry.Schema(query=Query)
```

---

## 3. URL Patterns

```python
# Uncomment after schema is ready:
# path('graphql/', GraphQLView.as_view(schema=schema)),
```

---

## 4. Conventions

- All resolvers live in `apps/api/schema.py`
- Use `@strawberry.type` for output types, `@strawberry.input` for input types
- Mutations should delegate to the service layer, not contain business logic
- When used with Neo4j, resolvers call graph repository methods


---



> [WARNING] Module file not found: /app/modules/file-encryption.md


---

# GSD Framework — Docker Module

## Purpose
Dockerfile and docker-compose configuration for local development with health checks, volumes, and multi-service stack.

---

## 1. Dockerfile

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/dev.txt ./requirements/
RUN pip install -r requirements/dev.txt

COPY . .

ENTRYPOINT ["docker/entrypoint.sh"]
```

---

## 2. Entrypoint Script

`docker/entrypoint.sh` waits for the database to be ready, runs migrations, collects static files, then exec's the container command.

---

## 3. Docker Compose

All containers named `{app-slug}-{service}` and grouped under the app name. Services are assembled from selected modules — each module contributes its own docker service definitions.

---

## 4. Makefile Targets

| Target | Command |
|--------|---------|
| `make up` | `docker compose up -d` |
| `make down` | `docker compose down` |
| `make build` | `docker compose build` |
| `make migrate` | Run migrations inside web container |
| `make seed` | Run `seed_lookups` + `seed_superusers` |
| `make shell` | Django shell inside web container |
| `make test` | Run pytest inside web container |
| `make lint` | Run ruff + mypy inside web container |

---

## 5. Conventions

- Docker Compose is for local development only — production uses ECS Fargate
- All services read from `.env.docker` (service hostnames like `db`, `redis`)
- Worker containers use `entrypoint: []` to skip the DB-wait entrypoint
- Shell scripts are written with Unix LF line endings for Linux containers


---

# GSD Framework — CI/CD Module

## Purpose
GitHub Actions pipelines for CI and per-environment deployment to AWS ECS Fargate via OIDC authentication. Covers DEV, UAT, and PROD environments with manual approval gates for production.

---

## 1. Environment Overview

| Environment | Trigger | Approval |
|-------------|---------|----------|
| DEV | Push to `develop` | Automatic |
| UAT | Push to `release/*` | Automatic |
| PROD | Tag `v*.*.*` on `main` | Manual gate |

---

## 2. AWS Infrastructure

Each environment is an isolated AWS account or VPC with ECS Fargate, RDS PostgreSQL, ElastiCache Redis, API Gateway, and ECR.

---

## 3. AWS SSO

Authentication uses AWS SSO (IAM Identity Center). No long-lived IAM credentials.

```bash
aws sso login --sso-session gsd
aws sts get-caller-identity --profile game-theory-dev
```

---

## 4. Deploy Script

`scripts/deploy.sh` handles ECR login, Docker build, push, and ECS rolling deploy.

```bash
make deploy ENV=dev   # deploys to DEV
make deploy ENV=prod  # requires manual confirmation
```

---

## 5. GitHub Actions

- `ci.yml` — runs on every push (lint, type check, test)
- `deploy-dev.yml` — deploys on push to `develop`
- `deploy-prod.yml` — deploys on tagged releases with manual approval

All workflows use OIDC for AWS authentication — no stored credentials.

---

## 6. Secrets Management

All secrets in AWS Secrets Manager:
```
/game-theory/{env}/database-url
/game-theory/{env}/secret-key
/game-theory/{env}/redis-url
```

---

## 7. Makefile Targets

| Target | Description |
|--------|-------------|
| `make deploy` | Deploy to AWS (prompts for PROD) |
| `make logs` | Tail ECS CloudWatch logs |
| `make sso-login` | AWS SSO login |


---

# GSD Framework — Monitoring Module

## Purpose
Sentry error tracking with Django integration, plus structured JSON logging.

---

## 1. Packages

```
sentry-sdk[django]>=1.40
```

---

## 2. Settings

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if env('SENTRY_DSN', default=''):
    sentry_sdk.init(
        dsn=env('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

---

## 3. Environment Variables

```env
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
```

Leave `SENTRY_DSN` blank to disable Sentry (e.g. in local development).


---

# GSD Framework — Testing Module

## Purpose
pytest with Django integration, factory-boy for fixtures, and code coverage reporting.

---

## 1. Dev Packages

```
pytest>=8.0
pytest-django>=4.8
pytest-cov>=4.1
factory-boy>=3.3
```

---

## 2. Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.local"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
```

---

## 3. Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/test_models.py      # Model conventions (UUID PK, soft delete)
├── feature/test_health.py   # Health endpoint + landing page
├── integration/             # External service tests
└── factories/factories.py   # UserFactory, LookupValueFactory
```

---

## 4. Running Tests

```bash
pytest -v                    # Local
docker compose exec web pytest -v   # Docker
make test                    # Makefile
```


---

# GSD Framework — Linting Module

## Purpose
Ruff for fast Python linting, MyPy for static type checking, and django-stubs for Django type annotations.

---

## 1. Dev Packages

```
ruff>=0.3
mypy>=1.9
django-stubs>=4.2
```

---

## 2. Configuration (pyproject.toml)

```toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.12"
plugins = ["mypy_django_plugin.main"]
ignore_missing_imports = true

[tool.django-stubs]
django_settings_module = "config.settings.local"
```

---

## 3. Running

```bash
ruff check .                 # Lint
mypy . --config-file pyproject.toml  # Type check
make lint                    # Both via Docker
```


---
