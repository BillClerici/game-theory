# CLAUDE.md — Game Theory Prediction Engine

## Project overview

AI-powered prediction and outcome engineering platform built on Django/PostgreSQL using Bruce Bueno de Mesquita's expected utility model. Conversational LLM layer gathers scenario data, game theory engine computes predictions, platform recommends strategic interventions.

## Required reference documents

Always read and follow these documents when implementing features:

- `docs/requirements/game-theory-app-capabilities.md` — Capability map with vision, feature descriptions, and priority matrix (P0–P3)
- `docs/requirements/feature_map.md` — Detailed feature specifications with models, endpoints, algorithms, and implementation phases

These documents are the source of truth for all feature work. Reference them before designing models, APIs, or UI for any game theory feature.

## Key conventions

- Every Django model inherits from `apps.core.models.BaseModel` (UUID PK, timestamps, soft delete)
- All lookup/reference values use `LookupValue` model with parent-child hierarchy — never create separate enum tables
- Authentication: Google/Microsoft OAuth2 only — no passwords
- GraphQL API via Strawberry at `/graphql/`
- Service layer in `apps/{module}/services.py` — views are thin
- All Celery tasks must be idempotent
- Docker Compose for local development
- Settings split: `base.py / local.py / dev.py / uat.py / prod.py`
- Python 3.12+, type hints on all function signatures
- `.env` files contain real API keys — NEVER overwrite or blank them, only append

## Data grids

Every list/table must include: client-side filtering, column sorting, pagination (10/25/50/100), scrollable body with sticky headers. Use `templates/admin/list.html` as reference.
