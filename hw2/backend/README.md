# waitlist backend

FastAPI service for the restaurant waitlist manager. See `../_docs/spec.md` for the
full spec. Uses an in-memory mock database (`src/waitlist/store.py`) — swap for a real
one later without touching `routes.py` or `service.py`.

## Run

```sh
uv run uvicorn waitlist.main:app --reload
```

## Test

```sh
uv run pytest
```

## Lint

```sh
uv run ruff check .
```
