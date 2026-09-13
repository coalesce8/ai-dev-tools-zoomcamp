# Restaurant Waitlist Manager — MVP Spec

## 1. Scope

A single-screen tool for a host stand. The host adds walk-in parties to a queue, tells
them a wait time, and marks what happened to them. The app remembers **who is waiting**;
the host still owns floor state.

**Users:** restaurant staff only. One device.

### Design decisions worth preserving

These are cheap now and expensive to retrofit:

- **Nothing is deleted.** Parties transition through statuses. Reporting and undo both
  depend on this.
- **`quoted_minutes` is stored, not computed.** The host types it from judgment. Storing
  it alongside real elapsed time is what makes auto-quoting possible later.
- **Phone is optional.** Some walk-ins won't give one; they must still be addable.

---

## 2. Data model

One table. SQLAlchemy 2.0 declarative models, Alembic for migrations.

### `parties`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID (or int PK) | no | |
| `name` | str(80) | no | Guest name as given. Non-empty after strip. |
| `party_size` | int | no | `>= 1`. Enforce with a CHECK constraint. |
| `phone` | str(32) | **yes** | Free text. No validation beyond length in v1. |
| `quoted_minutes` | int | yes | `>= 0`. What the host promised. |
| `status` | enum | no | `waiting` \| `seated` \| `no_show` \| `cancelled`. Default `waiting`. |
| `created_at` | timestamptz | no | Server-set. This is the queue order. |
| `ended_at` | timestamptz | yes | Set on any transition out of `waiting`. Null while waiting. |

**Derived, not stored:**

- Queue position — `row_number()` over `created_at` among `status = 'waiting'`.
- Elapsed wait — `now() - created_at` for waiting parties, `ended_at - created_at` for
  closed ones.
- Overdue — `elapsed > quoted_minutes` and `status = 'waiting'`.

**Invariants:**

- `status = 'waiting'` ⟺ `ended_at IS NULL`. Enforce in a CHECK constraint, not just in
  application code.
- Timestamps are stored UTC, rendered in the browser's local zone.

**Index:** `(status, created_at)` — covers the only hot query.

### Database agnosticism

No JSONB, arrays, or vendor-specific types. Connection comes from a `DATABASE_URL` env
var. SQLite for local dev, Postgres for anything real. Use `timezone=True` on DateTime
columns and be aware SQLite does not enforce it — always write timezone-aware UTC
datetimes from Python rather than relying on the DB.

---

## 3. API

FastAPI. JSON over HTTP. All paths under `/api`. Pydantic models for request and
response bodies.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/parties` | List parties. Query param `status` (default `waiting`). |
| `POST` | `/api/parties` | Add a party. |
| `PATCH` | `/api/parties/{id}` | Edit `name`, `party_size`, `phone`, `quoted_minutes`. |
| `POST` | `/api/parties/{id}/seat` | `waiting` → `seated`. |
| `POST` | `/api/parties/{id}/no-show` | `waiting` → `no_show`. |
| `POST` | `/api/parties/{id}/cancel` | `waiting` → `cancelled`. |
| `POST` | `/api/parties/{id}/restore` | Any terminal status → `waiting`. Undo for mis-taps. |
| `GET` | `/api/health` | Liveness. |

### Response shape

`GET /api/parties?status=waiting` returns the list ordered by `created_at ASC`, each
party enriched server-side so the frontend does no date arithmetic:

```json
{
  "id": "...",
  "name": "Marsh",
  "party_size": 4,
  "phone": "555-0143",
  "quoted_minutes": 25,
  "status": "waiting",
  "created_at": "2026-09-13T18:04:00Z",
  "ended_at": null,
  "position": 3,
  "waiting_minutes": 31,
  "is_overdue": true
}
```

### Transition rules

- The three closing actions accept **only** parties currently in `waiting`. Anything else
  is `409 Conflict` — not a silent no-op. A double-tap on Seat must not be mistaken for
  success.
- `restore` accepts only terminal statuses; restoring a `waiting` party is `409`.
- `restore` clears `ended_at` and leaves `created_at` untouched, so the party returns to
  its original place in line.
- `PATCH` is allowed on any status (fixing a typo after seating is legitimate) but must
  not accept `status` — status changes go through the action endpoints only.

### Errors

`400` for validation (FastAPI/Pydantic default), `404` unknown id, `409` illegal
transition. Error bodies: `{"detail": "..."}`.

---

## 4. Frontend

Vite + React + TypeScript. A single screen. No router, no state-management library —
component state and a fetch wrapper are enough for this surface.

### Layout

- **Add form**, always visible at the top: name, party size, phone (optional), quote
  (optional). Submitting clears the form and returns focus to the name field. The host
  adds parties in bursts; every extra click costs.
- **Waiting list** below it, oldest first. Each row shows position, name, size, elapsed
  minutes, quote, and phone. Overdue rows get a visual treatment (colour plus a
  non-colour cue — host stands are bright and screens get glanced at sideways).
- **Row actions:** Seat, No-show, Cancel, Edit.
- **Recently closed**, collapsed by default: the last ~10 non-waiting parties, each with
  a Restore button.

### Behaviour

- Refetch after every mutation.
- Poll `GET /api/parties` every 30s so elapsed times stay honest without a clock
  subscription. (If you'd rather not poll, a local `setInterval` re-render over
  `created_at` works too — but polling also catches edits made in another tab.)
- Destructive-ish actions (No-show, Cancel) need a confirm step or an undo toast. Given
  `restore` exists, an undo toast is the better trade — it doesn't add a tap to the happy
  path.
- Mobile-first sizing. This will be used on a tablet, one-handed, standing up. Tap
  targets ≥ 44px.

---

## 5. Project layout

```
waitlist/
  backend/
    pyproject.toml          # uv-managed
    alembic.ini
    migrations/
    src/waitlist/
      main.py               # FastAPI app, CORS for the Vite dev origin
      config.py             # DATABASE_URL, env parsing
      db.py                 # engine, session dependency
      models.py             # SQLAlchemy
      schemas.py            # Pydantic
      routes.py
      service.py            # transition logic, kept out of route handlers
    tests/
  frontend/
    package.json
    src/
      App.tsx
      api.ts                # typed fetch wrapper
      components/
```

**Backend deps:** `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2`, `alembic`,
`pydantic-settings`, `pydantic`. Dev: `pytest`, `httpx`, `ruff`.

Run with `uv run uvicorn waitlist.main:app --reload`.

---

## 6. Acceptance criteria

The MVP is done when all of these pass:

- [ ] Host adds a party with name + size only; it appears at the bottom of the list.
- [ ] Host adds a party with phone and quote; both display on the row.
- [ ] Party size below 1 is rejected with a readable message.
- [ ] Elapsed minutes increase without a manual refresh.
- [ ] A party past its quote is visually distinguishable from one that isn't.
- [ ] Seating a party removes it from the waiting list; remaining positions renumber.
- [ ] Seating an already-seated party returns 409 and does not change `ended_at`.
- [ ] Editing a waiting party's size does **not** change its queue position.
- [ ] No-show and cancel are distinguishable in the database afterwards.
- [ ] Restore returns a party to its original position, not the back of the line.
- [ ] With `DATABASE_URL` pointed at Postgres instead of SQLite, migrations run and the
      full test suite passes unchanged.

---
