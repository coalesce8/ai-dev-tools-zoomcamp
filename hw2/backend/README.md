# waitlist backend

FastAPI service for the restaurant waitlist manager. See `../_docs/spec.md` for the
full spec. Persistence is SQLAlchemy 2.0 (`src/waitlist/models.py`, `src/waitlist/db.py`)
with Alembic migrations. Defaults to a local SQLite file; set `DATABASE_URL` to point at
Postgres instead — no code changes needed.

## Setup

```sh
uv run alembic upgrade head
```

Set `DATABASE_URL` (e.g. in a `.env` file) to switch databases, for example:

```
DATABASE_URL=postgresql+psycopg://user:pass@localhost/waitlist
```

## Run

```sh
uv run uvicorn waitlist.main:app --reload
```

## Test

```sh
uv run pytest
```

Tests create tables on the configured `DATABASE_URL` (SQLite by default) and reset data
between tests — they don't require migrations to have been run first.

## Lint

```sh
uv run ruff check .
```

## Migrations

```sh
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```
